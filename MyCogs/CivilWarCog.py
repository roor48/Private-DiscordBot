import discord
from discord.ext import commands
from discord import app_commands
import random


class CivilView(discord.ui.View):
    def __init__(self, *, timeout: float = 180, author: discord.Member, message: discord.Message, thread: discord.Thread, max_player:int, team_count:int):
        super().__init__(timeout=timeout)
        self.__author: discord.User | discord.Member = author
        self.__message: discord.Message = message
        self.__thread: discord.Thread = thread
        self.__max_player: int = max_player
        self.__team_count: int = team_count

        self.__game_count: int = 1

        self.__joined: list[discord.Member] = []


    @discord.ui.button(label="참가", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if interaction.user in self.__joined:
            return
        if self.__max_player > 0 and len(self.__joined) >= self.__max_player:
            await interaction.user.send(f"{interaction.user.display_name}님의 반응 삭제됨\n`이유: 님 낄 자리 없음ㅋㅋ`")
            return

        self.__joined.append(interaction.user)

        try:
            embed = self.__message.embeds[0]
            embed.set_field_at(1, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
        except:
            embed = discord.Embed(title=self.__message.content, colour=discord.Colour.random())
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player if self.__max_player>0 else "inf"}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
            embed.set_footer(text='24시간 이후에 만료됩니다.')


        await self.__message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.all())


    @discord.ui.button(label="퇴장", style=discord.ButtonStyle.gray)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user not in self.__joined:
            return
        
        self.__joined.remove(interaction.user)

        try:
            embed = self.__message.embeds[0]
            embed.set_field_at(1, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
        except:
            embed = discord.Embed(title=self.__message.content, colour=discord.Colour.random())
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player if self.__max_player>0 else "inf"}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)
            embed.set_footer(text='24시간 이후에 만료됩니다.')


        await self.__message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.all())


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
            msg = await self.__thread.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions.all())
        except discord.errors.NotFound:
            self.__thread = await self.__message.create_thread(name='내-전', auto_archive_duration=1440, reason='내전 생성')
            msg = await self.__thread.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions.all())

        await msg.edit(content=None)


    @discord.ui.button(label="내전 종료", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.__author != interaction.user:
            await interaction.response.send_message(content='이 내전을 생성한 사람만 종료가 가능합니다.', ephemeral=True)
            return

        await interaction.response.defer()

        self.stop()
        await self.expiration_message()


    async def on_timeout(self):
        await self.expiration_message()


    async def expiration_message(self):
        try:
            await self.__thread.delete(reason='만료')
        except: ...

        try:
            embed = self.__message.embeds[0]
        except:
            embed = discord.Embed(title=self.__message.content, colour=discord.Colour.random())
            embed.add_field(name='설정', value=f'`최대 인원: {self.__max_player if self.__max_player>0 else "inf"}` `최대 팀 수: {self.__team_count}`')
            embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.__joined), inline=False)

        embed.set_footer(text='만료되었습니다.')
        for child in self.children:
            self.remove_item(child)
        await self.__message.edit(embed=embed, view=self)
        await self.__message.unpin(reason='내전 만료')


class CivilWarCog(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

    @app_commands.command(name="내전생성", description="내전 인원을 모읍니다.")
    @app_commands.describe(message="내용을 입력해주세요!", max_player="최대 인원입니다.", team_count="팀 수 입니다.")
    async def createCivilWar(self, interaction: discord.Interaction, message:str, max_player:int = 0, team_count:int = 2):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message('스레드 밖에서 사용해 주세요.', ephemeral=True)
            return

        embed = discord.Embed(title='내전', colour=discord.Colour.random())
        embed.add_field(name='설정', value=f'`최대 인원: {max_player if max_player>0 else "inf"}` `최대 팀 수: {team_count}`')
        embed.add_field(name='인원 리스트', value='', inline=False)
        embed.set_footer(text='24시간 이후에 만료됩니다.')

        await interaction.response.send_message(content=message, embed=embed, allowed_mentions=discord.AllowedMentions.all())
        msg = await interaction.original_response()

        thread = await msg.create_thread(name='팀 결과', auto_archive_duration=1440, reason='내전 생성')

        view = CivilView(timeout=86400, author=interaction.user, message=msg, thread=thread, max_player=max_player, team_count=team_count)

        await msg.edit(view=view)
        await msg.pin(reason='내전 생성')
