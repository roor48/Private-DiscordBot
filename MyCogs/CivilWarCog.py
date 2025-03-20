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
    def __init__(self, *, timeout: float, author: discord.Member, content: str, max_player: int, team_count: int):
        super().__init__(timeout=timeout)
        self.content: str = content
        self.max_player: CustomInt = CustomInt(max_player)
        self.team_count: int = team_count
        self.joined: list[discord.Member] = []

        self.__author: discord.Member = author
        self.__colour = discord.Colour.random()

        self.__game_count: int = 1


    def new_embed(self)->discord.Embed:
        embed = discord.Embed(title='내전', colour=self.__colour)
        embed.add_field(name='인원 수', value=f'`{len(self.joined)} / {self.max_player}`')
        embed.add_field(name='설정', value=f'`최대 인원: {self.max_player}` `최대 팀 수: {self.team_count}`')
        embed.add_field(name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.joined), inline=False)
        embed.set_footer(text='24시간 이후에 만료됩니다.')
        
        return embed

    @discord.ui.button(label="참가", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        message = interaction.message
        if interaction.user in self.joined:
            return
        if self.max_player > 0 and len(self.joined) >= self.max_player:
            return

        self.joined.append(interaction.user)

        try:
            embed = message.embeds[0]
            embed.set_field_at(0, name='인원 수', value=f'`{len(self.joined)} / {self.max_player}`')
            embed.set_field_at(2, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.joined), inline=False)
        except:
            embed = self.new_embed()


        await message.edit(content=self.content, embed=embed)


    @discord.ui.button(label="퇴장", style=discord.ButtonStyle.gray)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user not in self.joined:
            return
        
        self.joined.remove(interaction.user)

        message = interaction.message
        try:
            embed = message.embeds[0]
            embed.set_field_at(0, name='인원 수', value=f'`{len(self.joined)} / {self.max_player}`')
            embed.set_field_at(2, name='인원 리스트', value=' '.join(f'`{member.display_name}`' for member in self.joined), inline=False)
        except:
            embed = self.new_embed()


        await message.edit(content=self.content, embed=embed)


    @discord.ui.button(label="팀 뽑기", style=discord.ButtonStyle.blurple)
    async def team_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not self.joined:
            return

        joined_user = self.joined.copy()
        teams = [[] for _ in range(self.team_count)]
        
        random.shuffle(joined_user)
        # 사용자들을 각 팀에 나누기
        index = 0
        for user in joined_user:
            teams[index].append(user.mention)
            index = (index + 1) % self.team_count
        random.shuffle(teams)

        # 각 팀을 멘션하여 출력
        embed = discord.Embed(title=f'{self.__game_count}번째 게임')
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        self.__game_count += 1
        content = ''
        for i, team in enumerate(teams, 1):
            content += ' '.join(team)
            embed.add_field(name=f'팀 {i}', value=' '.join(team), inline=False)

        message = interaction.message
        try:
            msg = await message.thread.send(content=content, embed=embed)
        except discord.errors.NotFound:
            message.thread = await interaction.message.create_thread(name='팀 결과', auto_archive_duration=1440, reason='내전 생성')
            msg = await message.thread.send(content=content, embed=embed)

        await msg.edit(content=None)


    @discord.ui.button(label="수정")
    async def edit_civil(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id) and self.__author != interaction.user:
            await interaction.response.send_message(content='이 내전을 생성한 사람만 수정이 가능합니다.', ephemeral=True)
            return

        await interaction.response.send_modal(EditModal(message=interaction.message, view=self))




    @discord.ui.button(label="내전 종료", style=discord.ButtonStyle.danger, row=1)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id) and self.__author != interaction.user:
            await interaction.response.send_message(content='이 내전을 생성한 사람만 종료가 가능합니다.', ephemeral=True)
            return

        # await interaction.response.defer()
        await interaction.response.send_modal(DeleteModal(view=self))

        # await self.expiration_message(interaction.message)


    async def on_timeout(self):
        print('TIMEOUT VIEW')
        await self.expiration_message()


    async def expiration_message(self, message: discord.InteractionMessage = None):
        CivilWarCog.civil_count -= 1
        if not message:
            return
            # message: discord.Message = await self.__message.channel.fetch_message(self.__message.id)

        await message.thread.delete(reason='만료')
        try:
            embed = message.embeds[0]
        except:
            embed = self.new_embed()
        embed.set_footer(text='만료되었습니다.')

        self.clear_items()
        self.stop()
        await message.edit(content=self.content, embed=embed, view=self)
        


class EditModal(discord.ui.Modal):
    def __init__(self, *, message: discord.InteractionMessage, view: CivilView):
        super().__init__(title='수정')
        self.message = message
        self.view = view

        self.add_item(discord.ui.TextInput(label='메시지', default=view.content))
        self.add_item(discord.ui.TextInput(label='최대인원', placeholder="숫자 (no limit)", default=str(int(view.max_player))))
        self.add_item(discord.ui.TextInput(label='팀 수', placeholder="숫자 (1~25)", default=view.team_count))


    async def on_submit(self, interaction: discord.Interaction):
        max_player = str(self.children[1])
        team_count = str(self.children[2])
        if not max_player.isdigit() or not team_count.isdigit():
            await interaction.response.send_message("숫자가 아닌 문자가 들어갔습니다.", ephemeral=True)
            return
        await interaction.response.defer()

        max_player = int(max_player)
        team_count = int(team_count)

        if max_player < 0:
            max_player = 0
        
        if team_count < 1:
            team_count = 1
        elif team_count > 25:
            team_count = 25

        if max_player > 0:
            self.view.joined = self.view.joined[:max_player]
        self.view.max_player = CustomInt(max_player)
        self.view.team_count = team_count

        embed = self.view.new_embed()

        await self.message.edit(content=self.children[0], embed=embed, view=self.view, allowed_mentions=discord.AllowedMentions.all())


class DeleteModal(discord.ui.Modal):
    def __init__(self, *, view: CivilView):
        super().__init__(title='내전종료')
        self.view = view
        self.add_item(discord.ui.TextInput(label='확인메시지', default='종료하겠습니다.', required=False))
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        await self.view.expiration_message(interaction.message)



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
        
        view = CivilView(timeout=86400, author=interaction.user, content=message, max_player=max_player, team_count=team_count)

        embed = view.new_embed()

        await interaction.response.send_message(content=message, embed=embed, allowed_mentions=discord.AllowedMentions.all())
        msg = await interaction.original_response()

        await msg.create_thread(name='팀 결과', auto_archive_duration=1440, reason='내전 생성')


        await msg.edit(view=view)
        print('Created a CivilWar!')
        CivilWarCog.civil_count += 1

    @app_commands.command(name="print-civil")
    async def print_civil(self, interaction: discord.Interaction):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("이 기능은 관리자만 사용할 수 있습니다.", ephemeral=True)

        await interaction.response.send_message(content=CivilWarCog.civil_count)
        print(CivilWarCog.civil_count)
