import discord
from discord.ext import commands
from discord import app_commands
import random

from .errors import handle_error
from .AdminManager import is_admin

class CustomInt(int):
    def __str__(self):
        return super().__str__() if self > 0 else "inf"

class CivilView(discord.ui.View):
    def __init__(self, *, timeout: float, author: discord.Member, message: discord.InteractionMessage, max_player: CustomInt, team_count: int):
        super().__init__(timeout=timeout)
        self.__author: discord.Member = author
        self.__message: discord.InteractionMessage = message
        self.__max_player: CustomInt = max_player
        self.__team_count: int = team_count

        self.__game_count: int = 1

        self.__joined: list[discord.Member] = []


    @discord.ui.button(label="참가", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        message = interaction.message
        if interaction.user in self.__joined:
            return
        if self.__max_player > 0 and len(self.__joined) >= self.__max_player:
            return

        self.__joined.append(interaction.user)

        try:
            embed = message.embeds[0]
            embed.set_field_at(0, name='인원 수', value=f'`{len(self.__joined)} / {self.__max_player}`')
            embed.set_field_at(2, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
        except:
            embed = discord.Embed(title=message.content, colour=discord.Colour.random())
            embed.add_field(name='인원 수', value=f'`{len(self.__joined)} / {self.__max_player}`')
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
            embed.set_footer(text='24시간 이후에 만료됩니다.')


        await message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.all())


    @discord.ui.button(label="퇴장", style=discord.ButtonStyle.gray)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user not in self.__joined:
            return
        
        self.__joined.remove(interaction.user)

        message = interaction.message
        try:
            embed = message.embeds[0]
            embed.set_field_at(0, name='인원 수', value=f'`{len(self.__joined)} / {self.__max_player}`')
            embed.set_field_at(2, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
        except:
            embed = discord.Embed(title=message.content, colour=discord.Colour.random())
            embed.add_field(name='인원 수', value=f'`{len(self.__joined)} / {self.__max_player}`')
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
            embed.set_footer(text='24시간 이후에 만료됩니다.')


        await message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.all())


    @discord.ui.button(label="팀 뽑기", style=discord.ButtonStyle.blurple)
    async def team_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not self.__joined:
            return

        joined_user = self.__joined.copy()
        teams = [[] for _ in range(self.__team_count)]
        
        random.shuffle(joined_user)
        # 사용자들을 각 팀에 나누기
        index = 0
        for user in joined_user:
            teams[index].append(user.mention)
            index = (index + 1) % self.__team_count
        random.shuffle(teams)

        # 각 팀을 멘션하여 출력
        embed = discord.Embed(title=f'{self.__game_count}번째 게임')
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        self.__game_count += 1
        content = ''
        for i, team in enumerate(teams, 1):
            content += ' '.join(team)
            embed.add_field(name=f'팀 {i}', value=' '.join(team), inline=False)

        try:
            msg = await self.__message.thread.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions.all())
        except discord.errors.NotFound:
            self.__message.thread = await interaction.message.create_thread(name='팀 결과', auto_archive_duration=1440, reason='내전 생성')
            msg = await self.__message.thread.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions.all())

        await msg.edit(content=None)


    @discord.ui.button(label="내전 종료", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id) and self.__author != interaction.user:
            await interaction.response.send_message(content='이 내전을 생성한 사람만 종료가 가능합니다.', ephemeral=True)
            return

        await interaction.response.defer()

        self.stop()
        await self.expiration_message(interaction.message)


    async def on_timeout(self):
        print('TIMEOUT VIEW')
        await self.expiration_message()


    async def expiration_message(self, message: discord.InteractionMessage = None):
        try:
            await self.__message.thread.delete(reason='만료')
        except: ...

        CivilWarCog.civil_count -= 1
        if not message:
            message: discord.Message = await self.__message.channel.fetch_message(self.__message.id)

        try:
            embed = message.embeds[0]
        except:
            embed = discord.Embed(title=message.content, colour=discord.Colour.random())
            embed.add_field(name='인원 수', value=f'`{len(self.__joined)} / {self.__max_player}`')
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)

        embed.set_footer(text='만료되었습니다.')
        self.clear_items()
        await message.edit(embed=embed, view=self)



class CivilWarCog(commands.Cog):
    civil_count: int = 0
    def __init__(self, client):
        self.client: commands.Bot = client

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await handle_error(interaction, error)


    @app_commands.command(name="내전생성", description="내전 인원을 모읍니다.")
    @app_commands.describe(message="내용을 입력해주세요!", max_player="최대 인원입니다  (미지정 시 무한)", team_count="팀 수 입니다  (미지정 시 2팀)")
    async def createCivilWar(self, interaction: discord.Interaction, message:str, max_player:app_commands.Range[int, 1] = 0, team_count:app_commands.Range[int, 1, 25] = 2):
        if isinstance(interaction.user, discord.User):
            await interaction.response.send_message('개인 메세지에선 지원하지 않습니다.')
            return
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message('스레드 밖에서 사용해 주세요.', ephemeral=True)
            return

        max_player = CustomInt(max_player)
        embed = discord.Embed(title='내전', colour=discord.Colour.random())
        embed.add_field(name='인원 수', value=f'`0 / {max_player}`')
        embed.add_field(name='설정', value=f'`최대 인원: {max_player}` `최대 팀 수: {team_count}`')
        embed.add_field(name='인원 리스트', value='', inline=False)
        embed.set_footer(text='24시간 이후에 만료됩니다.')

        await interaction.response.send_message(content=message, embed=embed, allowed_mentions=discord.AllowedMentions.all())
        msg = await interaction.original_response()

        await msg.create_thread(name='팀 결과', auto_archive_duration=1440, reason='내전 생성')

        view = CivilView(timeout=86400, author=interaction.user, message=msg, max_player=max_player, team_count=team_count)

        await msg.edit(view=view)
        print('Created a CivilWar!')
        CivilWarCog.civil_count += 1

    @app_commands.command(name="print-civil")
    async def print_civil(self, interaction: discord.Interaction):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("이 기능은 관리자만 사용할 수 있습니다.", ephemeral=True)

        await interaction.response.send_message(content=CivilWarCog.civil_count)
        print(CivilWarCog.civil_count)
