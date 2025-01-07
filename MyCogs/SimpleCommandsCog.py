import discord
from discord.ext import commands
from discord import app_commands

class SimpleCommandsCog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    # 슬래시 명령어 정의
    @app_commands.command(name="hello", description="간단한 인사 메시지")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message("안녕하세요! 슬래시 명령어를 사용하고 있습니다.")

    @app_commands.command(name="ping", description="봇의 응답 시간을 확인합니다.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"퐁! {self.client.latency * 1000:.2f}ms")
