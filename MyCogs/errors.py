import discord
from asyncio.exceptions import TimeoutError

async def handle_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(error)
    if isinstance(error, discord.app_commands.CommandInvokeError):
        print('CommandInvokeError', type(error.original))
        if isinstance(error.original, discord.Forbidden):
            await handle_forbidden_error(interaction, command=error.command.name)
            return
        if isinstance(error.original, TimeoutError):
            await handle_forbidden_error(interaction, command=error.command.name)
            return
        
        await default_error(interaction, error)
        return



async def handle_forbidden_error(interaction: discord.Interaction, command: str, error_message: str = '봇에 관리자 권한이 없습니다.\n관리자 권한을 부여해주세요.'):
    embed = discord.Embed(title=error_message, colour=discord.Colour.red())
    embed.add_field(name='', value=command)
    if interaction.response.is_done():
        msg = await interaction.original_response()
        await msg.edit(content=None, embed=embed, view=None)
        if msg.pinned:
            await msg.unpin('권한 부족 오류')
        return
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def default_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f'{type(error)} Has Been Occurred: {error}')
    embed = discord.Embed(title=f"{type(error)} 오류발생", colour=discord.Colour.brand_red())

    if interaction.response.is_done():
        msg = await interaction.original_response()
        await msg.edit(content=None, embed=embed, view=None)
        if msg.pinned:
            await msg.unpin('오류')
        return

    await interaction.response.send_message(embed=embed, ephemeral=True)
