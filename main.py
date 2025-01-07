"""
required versions

python 3.10.12

dotenv 1.0.1
pip install python-dotenv

discord 2.4.0
pip install -U discord.py
"""

import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

from MyCogs import *
load_dotenv()
del load_dotenv

class MyClient(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)

        # self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        # SlashCommands Cog 등록
        await self.add_cog(CivilWarCog(self)) # 내전 관련 Cog
        await self.add_cog(MessageEventCog(self)) # 메세지 관련 Cog
        await self.add_cog(SimpleCommandsCog(self)) # 간단한 명령어 Cog

        # sync to a specific guild
        test_guild = discord.Object(id=1325768627596820574)
        self.tree.copy_global_to(guild=test_guild)
        
        # sync to all servers if no specification
        await self.tree.sync()

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)



client.run(os.getenv('BOT_KEY'))
