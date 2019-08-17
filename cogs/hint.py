from functions import *


class Hint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # give hint
    @commands.command(help="- Gives first letter of current bird", aliases=["h"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def hint(self, ctx):
        print("hint")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
        if currentBird != "":  # check if there is bird
            await ctx.send(f"The first letter is {currentBird[0]}")
        else:
            await ctx.send("You need to ask for a bird first!")

    # give hint for goat
    @commands.command(help="- Gives first letter of current goatsucker", aliases=["goathint", "hg", "gh"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def hintgoat(self, ctx):
        print("hintgoat")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
        if currentBird != "":  # check if there is bird
            await ctx.send(f"The first letter is {currentBird[0]}")
        else:
            await ctx.send("You need to ask for a bird first!")

    # give hint for song
    @commands.command(help="- Gives first letter of current bird call", aliases=["songhint", "hs", "sh"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def hintsong(self, ctx):
        print("hintsong")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
        if currentSongBird != "":  # check if there is bird
            await ctx.send(f"The first letter is {currentSongBird[0]}")
        else:
            await ctx.send("You need to ask for a bird first!")


def setup(bot):
    bot.add_cog(Hint(bot))
