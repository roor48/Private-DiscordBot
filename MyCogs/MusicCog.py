import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL, utils
import asyncio
import urllib.parse, urllib.request, re

class queue_element:
    def __init__(self, original_url: str, url: str, thumbnail: str, title: str, duration: int):
        self.original_url = original_url
        self.url = url
        self.thumbnail = thumbnail
        self.title = title
        self.duration = duration

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
        
        self.now_playing: queue_element = None
        self.queues: dict[int, list[queue_element]] = {}
        self.voice_clients: dict[int, discord.VoiceClient] = {}

        self.youtube_base_url: tuple = ('https://www.youtube.com/', 'https://youtu.be/')
        self.youtube_results_url: str = self.youtube_base_url[0] + 'results?'
        self.youtube_watch_url: str = self.youtube_base_url[0] + 'watch?v='
        self.ytdl: YoutubeDL = YoutubeDL({
            'format': 'bestaudio/best',
            'cookiefile': './cookies.txt',  # 쿠키 파일 경로 추가
        })

        self.ffmpeg_options: dict = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if after.channel or member != self.client.user:
            return
        
        if member.guild.id in self.voice_clients:
            del self.voice_clients[member.guild.id]
        if member.guild.id in self.queues:
            del self.queues[member.guild.id]

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

    async def play_next(self, message: discord.Message):
        q_elements = self.queues.get(message.guild.id, None)
        if q_elements: # url이 있고 요소가 있으면
            q_ele = q_elements.pop(0)
            await self.play_music(q_ele, message)
        else: # 더 이상 재생할 노래가 없으면 disconnect
            if q_elements is not None:
                del self.queues[message.guild.id]

            voice_client = self.voice_clients.get(message.guild.id, None)
            if voice_client is not None:
                del self.voice_clients[message.guild.id]
                await voice_client.disconnect()
    
    async def play_music(self, q_ele: queue_element, message: discord.Message):
        # try:
        #     data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
        # except utils.DownloadError as e:
        #     embed = discord.Embed(title="올바른 주소가 아닙니다.", colour=discord.Colour.brand_red())
        #     await message.edit(embed=embed)
        #     return


        embed = discord.Embed(title=q_ele.title, colour=discord.Colour.brand_red(), url=q_ele.original_url)
        embed.set_thumbnail(url=q_ele.thumbnail)
        embed.set_author(name="현재 재생 중")
        embed.add_field(name="영상 길이", value=f"{q_ele.duration//60:02}:{q_ele.duration%60:02}")

        await message.edit(embed=embed)

        song = q_ele.url
        player = discord.FFmpegOpusAudio(song, **self.ffmpeg_options)

        self.voice_clients[message.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(message), self.client.loop))



    @app_commands.command(name="play", description="노래를 재생합니다.")
    @app_commands.describe(url="주소 혹은 검색할 텍스트를 입력해주세요.")
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
            if self.youtube_base_url[0] not in url and self.youtube_base_url[1] not in url:
                url = self.search_youtube(url)
                if not url:
                    embed = discord.Embed(title="검색 결과가 없습니다.", colour=discord.Colour.brand_red())
                    await message.edit(embed=embed)
                    return
            
            try:
                q_ele = await self.get_youtube_info(url)
            except utils.DownloadError as e:
                embed = discord.Embed(title="올바른 주소가 아닙니다.", colour=discord.Colour.brand_red())
                await message.edit(embed=embed)
                return
            
            self.queues[interaction.guild_id].append(q_ele)

            embed = discord.Embed(title=q_ele.title, colour=discord.Colour.brand_red(), url=q_ele.original_url)
            embed.set_thumbnail(url=q_ele.thumbnail)
            embed.set_author(name="대기열에 추가 완료!")
            embed.add_field(name="영상 길이", value=f"{q_ele.duration//60:02}:{q_ele.duration%60:02}")

            await message.edit(embed=embed)

            if self.voice_clients[interaction.guild_id].is_paused():
                return
            if not self.voice_clients[interaction.guild_id].is_playing():
                await self.play_next(message)

        except Exception as e:
            print(f'{type(e)} Has Been Occurred: {e}')
            embed = discord.Embed(title=f"{type(e)} 오류발생", colour=discord.Colour.brand_red())
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

