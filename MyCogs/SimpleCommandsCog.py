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


    @app_commands.command(name="고정된메시지삭제", description="봇이 보낸 메시지를 고정 해제합니다.")
    async def removeBotPinned(self, interaction: discord.Interaction):
        await interaction.response.send_message("고정 해제 중입니다...", ephemeral=True)
        msg = await interaction.original_response()

        pinned_messages = await interaction.channel.pins()

        if not pinned_messages:
            await msg.edit(content="고정된 메시지가 없습니다.")
            return
        
        
        for msg in pinned_messages:
            if msg.author == self.client.user:
                await msg.unpin(reason="봇이 메시지를 고정 해제했습니다.")

        await msg.edit(content="봇이 보낸 메시지 중 고정된 메시지를 전부 고정 해제했습니다.")
