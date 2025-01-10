import os
import discord
from discord.ext import commands

from MyCogs import *

from dotenv import load_dotenv
load_dotenv()
del load_dotenv

# 종료 시 실행될 함수
def on_bot_exit():
    print("Bot is exiting...")


class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)


    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        # SlashCommands Cog 등록
        await self.add_cog(CivilWarCog(self)) # 내전 관련 Cog
        await self.add_cog(MessageEventCog(self)) # 메세지 관련 Cog
        await self.add_cog(SimpleCommandsCog(self)) # 간단한 명령어 Cog
        await self.add_cog(MusicCog(self)) # 음악 관련 Cog

        # sync to all servers if no specification
        await self.tree.sync()
        print('slash command sync success')

    # 오버라이딩
    async def close(self):
        print('봇 종료 중...')
        # 클린업 작업을 비동기적으로 수행한 후 봇을 종료합니다.
        await self.cleanup()  # 비동기적으로 cleanup을 호출
        await super().close()  # 그 후 기본 close 메서드를 호출하여 봇 종료
        print('봇 종료 완료!')

    async def cleanup(self):
        await self.get_cog("CivilWarCog").on_close()


# 프로그램 시작
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    client = MyClient(intents=intents)

    client.run(os.getenv('BOT_KEY'))

