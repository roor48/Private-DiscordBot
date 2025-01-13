from traceback import print_exc
import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL, utils
import asyncio
import urllib.parse, urllib.request
import re

class queue_element:
    def __init__(self, original_url: str, url: str, thumbnail: str, title: str, duration: int):
        self.original_url = original_url
        self.url = url
        self.thumbnail = thumbnail
        self.title = title
        self.duration = duration

def is_youtube_link(url: str) -> bool:
    """
    정규식 설명:
        https?:// : http 또는 https로 시작하는 URL
        (www\.)? : www.이 있을 수도 있고 없을 수도 있음
        (youtube|youtu)\.(com|be) : youtube.com, youtu.be 도메인
        (watch\?v=|(?:[a-zA-Z0-9_-]+/)+) : watch?v= 패턴 또는 youtu.be/ 패턴
        ([a-zA-Z0-9_-]{11}) : 영상 ID는 11자의 알파벳, 숫자, 하이픈(-), 언더스코어(_)로 이루어져 있음
    """

    youtube_regex = (
        r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/'
        r'(watch\?v=|(?:[a-zA-Z0-9_-]+/)+)([a-zA-Z0-9_-]{11})')
    return bool(re.match(youtube_regex, url))

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
        
        self.repeat_mode: dict[int, int] = {} # 0 반복 없음, 1 단일 반복, 2 전체 반복

        self.now_playing: dict[int, queue_element] = {}
        self.queues: dict[int, list[queue_element]] = {}
        self.voice_clients: dict[int, discord.VoiceClient] = {}

        self.youtube_results_url: str = 'https://www.youtube.com/results?'
        self.youtube_watch_url: str = 'https://www.youtube.com/watch?v='

        self.ytdl: YoutubeDL = YoutubeDL({
            'format': 'bestaudio/best',
            'cookiefile': './cookies.txt',  # 쿠키 파일 경로

            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            }
        })

        self.ffmpeg_options: dict = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        try:
            voice_client = self.voice_clients.get(member.guild.id, None)
            if not voice_client:
                return
            if not before.channel or voice_client.channel.id != before.channel.id:
                return

            if member.id != self.client.user.id:
                if all(m.bot for m in before.channel.members):
                    await voice_client.disconnect()
                return

            if member.guild.id in self.voice_clients:
                del self.voice_clients[member.guild.id]

            if member.guild.id in self.queues:
                del self.queues[member.guild.id]

            if member.guild.id in self.now_playing:
                del self.now_playing[member.guild.id]

            if member.guild.id in self.repeat_mode:
                del self.repeat_mode[member.guild.id]
        
        except Exception as e:
            print_exc()
            print(f'{type(e)} Has Been Occurred: {e}')


    def search_youtube(self, url: str):
        query_string = urllib.parse.urlencode({
            'search_query': url
        })

        content = urllib.request.urlopen(
            self.youtube_results_url + query_string
        )

        search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())

        if search_results:
            return self.youtube_watch_url + search_results[0]
        return False
    
    async def get_youtube_info(self, url: str):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))

        return queue_element(url,
                             data.get('url', None), 
                             data.get('thumbnail', None), 
                             data.get('title', None), 
                             data.get('duration', None))


    async def play_next(self, channel: discord.TextChannel):

        q_elements = self.queues.get(channel.guild.id, None)
    
        now_playing = self.now_playing.get(channel.guild.id, None)
        if now_playing and channel.guild.id in self.repeat_mode:
            if self.repeat_mode[channel.guild.id] == 1:
                self.play_music(now_playing)
                return
            elif self.repeat_mode[channel.guild.id] == 2:
                q_elements.append(now_playing)


        if q_elements: # url이 있고 요소가 있으면
            q_ele = q_elements.pop(0)
            await self.play_music(q_ele, channel)
        else: # 더 이상 재생할 노래가 없으면 disconnect
            if q_elements:
                del self.queues[channel.guild.id]

            voice_client = self.voice_clients.get(channel.guild.id, None)
            if voice_client:
                del self.voice_clients[channel.guild.id]
                await voice_client.disconnect()
    
    async def play_music(self, q_ele: queue_element, channel: discord.TextChannel):
        embed = discord.Embed(title=q_ele.title, colour=discord.Colour.brand_red(), url=q_ele.original_url)
        embed.set_thumbnail(url=q_ele.thumbnail)
        embed.set_author(name="현재 재생 중")
        embed.add_field(name="영상 길이", value=f"{q_ele.duration//60:02}:{q_ele.duration%60:02}")

        await channel.send(embed=embed)

        song = q_ele.url
        player = discord.FFmpegOpusAudio(song, **self.ffmpeg_options)

        self.now_playing[channel.guild.id] = q_ele
        self.voice_clients[channel.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(channel), self.client.loop))



    @app_commands.command(name="play", description="노래를 재생합니다.")
    @app_commands.describe(url="유튜브 주소 혹은 검색할 텍스트를 입력해주세요.")
    async def add_music(self, interaction: discord.Interaction, url: str):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        if not interaction.user.voice:
            await interaction.response.send_message('먼저 음성 채팅방에 들어가주세요.', ephemeral=True)
            return
        

        if interaction.guild_id not in self.voice_clients:
            self.voice_clients[interaction.guild_id] = None
            self.voice_clients[interaction.guild_id] = await interaction.user.voice.channel.connect(reconnect=False, self_deaf=True)
            self.queues[interaction.guild_id] = []
            self.repeat_mode[interaction.guild_id] = 0
            self.now_playing[interaction.guild_id] = None
        
        if self.voice_clients[interaction.guild_id] == None:
            await interaction.response.send_message('봇이 음성 채팅방에 들어갈 때까지 조금만 기다려 주세요.', ephemeral=True)
            return

        if self.voice_clients[interaction.guild_id].channel != interaction.user.voice.channel:
            await interaction.response.send_message('봇과 다른 통화방에 있습니다.')
            return


        embed = discord.Embed(title="영상 불러오는 중...", colour=discord.Colour.brand_red())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        try:
            url = url.replace(' ', '')
            if not is_youtube_link(url):
                url = self.search_youtube(url)
                if not url:
                    embed = discord.Embed(title="검색 결과가 없습니다.", colour=discord.Colour.brand_red())
                    await message.edit(embed=embed)
                    return
            

            q_ele = await self.get_youtube_info(url)
            
            self.queues[interaction.guild_id].append(q_ele)

            embed = discord.Embed(title=q_ele.title, colour=discord.Colour.brand_red(), url=q_ele.original_url)
            embed.set_thumbnail(url=q_ele.thumbnail)
            embed.set_author(name="대기열에 추가 완료!")
            embed.add_field(name="영상 길이", value=f"{q_ele.duration//60:02}:{q_ele.duration%60:02}")

            await message.edit(embed=embed)

            if self.voice_clients[interaction.guild_id].is_paused():
                return
            if not self.voice_clients[interaction.guild_id].is_playing():
                await self.play_next(message.channel)

        except Exception as e:
            print_exc()
            print(f'{type(e)} Has Been Occurred: {e}')
            embed = discord.Embed(title=f"{type(e)} 오류발생", colour=discord.Colour.brand_red())
            await message.edit(embed=embed)



    @app_commands.command(name="skip", description="현재 노래를 건너뜁니다.")
    async def skip(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        embed = discord.Embed(title="대기 중입니다...", colour=discord.Colour.brand_red())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        voice_client: discord.VoiceClient = self.voice_clients.get(interaction.guild_id, None)
        if not voice_client or not (voice_client.is_playing() or voice_client.is_paused()):
            embed.title = "재생 중이 아닙니다."
            await message.edit(embed=embed)
            return
        
        voice_client.stop()

        embed.title = "곡 하나를 건너뛰었습니다!"
        await message.edit(embed=embed)

    @app_commands.command(name="repeat", description="반복 모드를 설정합니다.")
    async def repeat(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        embed = discord.Embed(title="설정 중입니다...", colour=discord.Colour.brand_red())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        val = self.repeat_mode.get(interaction.guild_id, 0) + 1
        if val > 2:
            val = 0
        self.repeat_mode[interaction.guild_id] = val

        arr = ["반복 없음", "단일 반복", "전체 반복"]
        embed.title = "설정 완료"
        embed.add_field(name="반복 모드", value=arr[self.repeat_mode[interaction.guild_id]])
        await message.edit(embed=embed)

    @app_commands.command(name="queue", description="대기열을 확인합니다.")
    async def queue(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        queue: list[queue_element] = self.queues.get(interaction.guild_id, False)
        if not queue:
            await interaction.response.send_message('대기열에 노래가 없습니다.')
            return
        
        embed = discord.Embed(title="대기열을 불러오고 있습니다.", colour=discord.Colour.brand_red())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        try:
            embed.title = "대기열"
            titles = []
            durations = []

            for i in range(min(10, len(queue))):
                titles.append(f'{i+1}. {queue[i].title}')
                durations.append(queue[i].duration)

            for i in range(len(titles)):
                embed.add_field(name=titles[i], value=f'[{durations[i]//60:02}:{durations[i]%60:02}]({queue[i].original_url})', inline=False)

            await message.edit(embed=embed)
        
        except Exception as e:
            print_exc()
            print(f'{type(e)} Has Been Occurred: {e}')
            embed = discord.Embed(title=f"{type(e)} 오류발생", colour=discord.Colour.brand_red())
            await message.edit(embed=embed)



    @app_commands.command(name="pause", description="멈춤")
    async def pause(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        if not interaction.guild_id in self.voice_clients:
            await interaction.response.send_message('봇이 채널에 없습니다.')
            return
        # if not self.voice_clients[interaction.guild_id].is_playing():
        #     await interaction.response.send_message('멈출 노래가 없습니다.')
        #     return
        if self.voice_clients[interaction.guild_id].is_paused():
            await interaction.response.send_message('이미 멈춘 상태입니다.')
            return
        
        self.voice_clients[interaction.guild_id].pause()
        await interaction.response.send_message('노래를 멈췄습니다.')



    @app_commands.command(name="resume", description="재생")
    async def resume(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        if not interaction.guild_id in self.voice_clients:
            await interaction.response.send_message('봇이 채널에 없습니다.')
            return
        # if not self.voice_clients[interaction.guild_id].is_playing():
        #     await interaction.response.send_message('재생할 노래가 없습니다.')
        #     return
        if not self.voice_clients[interaction.guild_id].is_paused():
            await interaction.response.send_message('이미 재생 중입니다.')
            return
        self.voice_clients[interaction.guild_id].resume()
        await interaction.response.send_message('노래를 다시 재생했습니다.')



    @app_commands.command(name="clear", description="대기열 제거")
    async def clear_queue(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        if interaction.guild_id in self.queues:
            self.queues[interaction.guild_id].clear()

        await interaction.response.send_message('대기열 제거 완료!')




    @app_commands.command(name="leave", description="봇 내보내기")
    async def leave(self, interaction: discord.Interaction):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        
        voice_client = self.voice_clients.get(interaction.guild_id, False)
        if voice_client:
            await interaction.response.send_message('봇을 내보냈습니다.')
            await self.voice_clients[interaction.guild_id].disconnect()
        else:
            await interaction.response.send_message('봇이 채널에 없습니다.')

    @app_commands.command(name="print-music", description="딕셔너리 출력")
    async def test(self, interaction: discord.Interaction):
        if interaction.user.id != 468316922052608000:
            await interaction.response.send_message("이 기능은 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.send_message(f'{self.voice_clients}\n{self.queues}')
        print(len(self.voice_clients))
        print(len(self.queues))

        voice_client: discord.VoiceClient = self.voice_clients.get(interaction.guild_id, None)
        if voice_client:
            print('is_paused:', voice_client.is_paused())
            print('is_playing:', voice_client.is_playing())
