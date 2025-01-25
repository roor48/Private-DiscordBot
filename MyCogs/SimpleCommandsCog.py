import discord
from discord.ext import commands
from discord import app_commands

class SimpleCommandsCog(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

    @app_commands.command(name="종료", description="봇을 종료합니다.")
    async def stop_bot(self, interaction: discord.Interaction):
        if interaction.user.id != 468316922052608000:
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        await interaction.response.send_message("종료 중입니다.")
        await self.client.close()

    @app_commands.command(name="ping", description="봇의 응답 시간을 확인합니다.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"pong! {self.client.latency * 1000:.2f}ms", ephemeral=True)

