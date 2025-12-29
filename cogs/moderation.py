from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong 🏓")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
