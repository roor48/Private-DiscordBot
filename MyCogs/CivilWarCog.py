import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import asyncio

class CivilWarCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.createdWarUserId = {}
        self.createdWarMessageId = {}
        self.check_expired_wars.start()  # 주기적으로 만료된 내전 체크 시작
    

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user): # 반응이 추가됐을때 호출
        if user == self.client.user:
            return
        if reaction.emoji != "✅":
            return
        if reaction.message.id not in self.createdWarMessageId: # 메시지가 /내전생성 명령어로 생성한 메시지가 아닐 때
            return
        
        created_user_id = self.createdWarMessageId[reaction.message.id]["user_id"]
        if self.createdWarUserId[created_user_id]["max_player"] <= 0: # 최대 플레이어를 지정 안했으면 넘어감
            return

        if reaction.count-1 > self.createdWarUserId[created_user_id]["max_player"]:
            await reaction.remove(user)
            await user.send(f"{user.display_name}님의 반응 삭제됨\n`이유: 님 낄 자리 없음ㅋㅋ`")



    @app_commands.command(name="내전생성", description="내전 인원을 모읍니다.")
    async def createCivilWar(self, interaction: discord.Interaction, message:str, max_player:int = 0, team_count:int = 2):
        if team_count <= 0:
            await interaction.response.send_message("team_count는 1 이상이여야 합니다.")

        await interaction.response.send_message(f"{message}\n`최대인원: {'no_limits' if max_player==0 else max_player}` `팀 수: {team_count}`\n-# ✅반응을 눌러 내전에 참가하세요!")
        msg = await interaction.original_response()
        await msg.add_reaction("✅")

        create_time = asyncio.get_event_loop().time()
        self.createdWarUserId[interaction.user.id] = {
            "channel_id": msg.channel.id,
            "message_id": msg.id,
            "max_player": max_player,
            "team_count": team_count,
            "create_time": create_time
        }
        self.createdWarMessageId[msg.id] = {
            "user_id": interaction.user.id,
        }


    
    @app_commands.command(name="내전종료", description="이전에 생성한 내전을 종료합니다.")
    async def removeCivilWar(self, interaction: discord.Interaction):
        if interaction.user.id not in self.createdWarUserId:
            await interaction.response.send_message("생성된 내전이 없습니다.")
            return

        try:
            message = await interaction.channel.fetch_message(self.createdWarUserId[interaction.user.id]["message_id"])

            await interaction.response.send_message("생성된 내전이 종료되었습니다.", ephemeral=True)
            await message.reply("생성된 내전이 종료되었습니다.")
        except discord.NotFound:
            await interaction.response.send_message("이 채널에서 메시지를 찾을 수 없습니다.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("메시지를 조회할 권한이 없습니다.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("서버 오류가 발생했습니다.", ephemeral=True)

        del self.createdWarMessageId[self.createdWarUserId[interaction.user.id]["message_id"]]
        del self.createdWarUserId[interaction.user.id]

    @app_commands.command(name="팀뽑기", description="반응한 사람 중 팀 랜덤 배치")
    async def getTeam(self, interaction: discord.Interaction): # /팀뽑기 명령어
        try:
            if interaction.user.id not in self.createdWarUserId:
                await interaction.response.send_message("생성된 내전이 없습니다.")
                return

            message = await interaction.channel.fetch_message(self.createdWarUserId[interaction.user.id]["message_id"])
            
            # 반응한 사용자들을 저장할 리스트
            reacted_users = []
            
            # 각 반응에 대해 반응한 사용자 목록을 비동기적으로 가져옵니다.
            for reaction in message.reactions:
                if reaction.emoji == "✅":
                    async for user in reaction.users():  # 해당 반응에 대해 반응한 사용자 목록
                        if user.bot:
                            continue
                        reacted_users.append(user.mention)
                    break

            reacted_users = list(set(reacted_users))

            if not reacted_users:
                await interaction.response.send_message("✅ 이모지에 반응한 사람이 없습니다.")
                return
            
            random.shuffle(reacted_users)

            team_count = self.createdWarUserId[interaction.user.id]["team_count"]

            teams = [[] for _ in range(team_count)]
            # 사용자들을 각 팀에 나누기
            index = 0
            for user in reacted_users:
                teams[index].append(user)
                index = (index + 1) % team_count

            random.shuffle(teams)

            
            # 각 팀을 멘션하여 출력
            team_mentions = []
            for i, team in enumerate(teams, 1):
                team_mentions.append(f"# 팀 {i}\n{', '.join(team)}")
            
            await interaction.response.send_message("\n".join(team_mentions))


        except discord.NotFound:
            await interaction.response.send_message("이 채널에서 메시지를 찾을 수 없습니다.", ephemeral=True)
            del self.createdWarMessageId[self.createdWarUserId[interaction.user.id]["message_id"]]
            del self.createdWarUserId[interaction.user.id]

        except discord.Forbidden:
            await interaction.response.send_message("메시지를 조회할 권한이 없습니다.", ephemeral=True)
            del self.createdWarMessageId[self.createdWarUserId[interaction.user.id]["message_id"]]
            del self.createdWarUserId[interaction.user.id]

        except discord.HTTPException:
            await interaction.response.send_message("서버 오류가 발생했습니다.", ephemeral=True)
            del self.createdWarMessageId[self.createdWarUserId[interaction.user.id]["message_id"]]
            del self.createdWarUserId[interaction.user.id]


    # 주기적으로 만료된 내전 데이터 확인
    @tasks.loop(minutes=30)  # 1분마다 체크 (효율성을 위해 1분 간격으로 체크)
    async def check_expired_wars(self):
        current_time = asyncio.get_event_loop().time()  # 현재 시간 (초 단위)
        expired_wars = []  # 만료된 내전 목록
        
        # 만료된 내전 데이터 찾기
        for user_id, data in self.createdWarUserId.items():
            message_id = data["message_id"]
            create_time = data.get("create_time")
            if not create_time or (current_time - create_time >= 86400):  # 24시간 이상 경과하면
                expired_wars.append(user_id)

        # 만료된 내전 삭제
        for user_id in expired_wars:
            try:
                channel_id = self.createdWarUserId[user_id]["channel_id"]
                message_id = self.createdWarUserId[user_id]["message_id"]

                del self.createdWarUserId[user_id]
                del self.createdWarMessageId[message_id]
            
                # 관련된 메시지에 24시간 후에 내전이 삭제됐다는 알림을 보내기
                channel = self.client.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                await message.reply("이 내전은 24시간이 지나 자동으로 종료되었습니다.")
            except Exception as e:
                print(f'Error While Auto-Deleting: {e}')

    @app_commands.command(name="print-civilwarcog", description="딕셔너리 출력")
    async def test(self, interaction: discord.Interaction):
        if interaction.user.id != 468316922052608000:
            await interaction.response.send_message("이 기능은 관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        print(self.createdWarUserId)
        print(self.createdWarMessageId)

        await interaction.response.send_message("딕셔너리 출력 완료", ephemeral=True)
