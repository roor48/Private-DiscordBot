from discord.ext import commands

class MessageEventCog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            return
        
        # await message.channel.send(f'`second function`')