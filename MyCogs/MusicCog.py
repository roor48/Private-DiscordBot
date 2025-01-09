import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp

class MusicCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.voice_client = None

    async def join_voice_channel(self, channel):
        self.voice_client = await channel.connect(self_deaf=True)

    @app_commands.command(name="join", description="봇 채널 참가.")
    async def music_join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("먼저 음성 채널에 접속해주세요.", ephemeral=True)
            return
        self.voice_client = await interaction.user.voice.channel.connect(self_deaf=True)
        await interaction.response.send_message("채널 참가 완료!")

    @app_commands.command(name="play", description="노래를 재생합니다.")
    @app_commands.describe(url="링크를 입력해주세요!")
    async def music_play(self, interaction: discord.Interaction, url:str = 'https://youtu.be/KHQ2MaDbx5I'):
        if self.voice_client:
            await interaction.response.send_message("")
            return
        if not interaction.user.voice:
            await interaction.response.send_message("먼저 음성 채널에 접속해주세요.", ephemeral=True)
            return
        self.voice_client = await interaction.user.voice.channel.connect(self_deaf=True)


        embed = discord.Embed(title="영상 불러오는 중...", colour=discord.Colour.brand_red())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        # yt-dlp를 사용하여 유튜브 URL에서 음성 데이터를 추출
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'extractaudio': True,
            'audioquality': 1,
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'restrictfilenames': True,
            'forcejson': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)  # 다운로드하지 않고 정보만 추출
            duration = info_dict.get('duration', None)  # 길이는 초 단위로 반환됩니다

            embed = discord.Embed(title=info_dict.get('title', None), colour=discord.Colour.brand_red(), url=url)
            embed.set_thumbnail(url=info_dict.get('thumbnail', None))
            embed.add_field(name="영상 길이", value=f"{duration//60:02}:{duration%60:02}")

            await message.edit(embed=embed)

            
        #     info = ydl.extract_info(url, download=False)  # 다운로드하지 않고 정보만 추출
        #     url2 = info['formats'][0]['url']  # 오디오 스트리밍 URL
        
        # # 음성을 재생합니다.
        # voice_client = self.voice_client
        # voice_client.play(discord.FFmpegPCMAudio(url2), after=lambda e: print('done', e))
        

    # 음성 채널에서 나가는 명령어
    @app_commands.command(name="leave", description="음성 채널에서 봇을 나가게 합니다.")
    async def leave(self, interaction: discord.Interaction):
        if self.voice_client:
            await self.voice_client.disconnect()  # 봇을 음성 채널에서 분리
            await interaction.response.send_message("음성 채널에서 나갔습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("봇이 음성 채널에 연결되어 있지 않습니다.", ephemeral=True)

