from functions import *


class Skip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Skip command - no args
    @commands.command(help="- Skip the current bird to get a new one", aliases=["sk"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def skip(self, ctx):
        print("skip")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
        database.lset(str(ctx.channel.id), 0, "")
        database.lset(str(ctx.channel.id), 1, "1")
        if currentBird != "":  # check if there is bird
            birdPage = wikipedia.page(currentBird + "(bird)")
            await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
        else:
            await ctx.send("You need to ask for a bird first!")

    # Skip command - no args
    @commands.command(help="- Skip the current goatsucker to get a new one", aliases=["goatskip", "sg"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def skipgoat(self, ctx):
        print("skipgoat")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
        database.lset(str(ctx.channel.id), 5, "")
        database.lset(str(ctx.channel.id), 6, "1")
        if currentBird != "":  # check if there is bird
            birdPage = wikipedia.page(currentBird + "(bird)")
            await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
        else:
            await ctx.send("You need to ask for a bird first!")

    # Skip song command - no args
    @commands.command(help="- Skip the current bird call to get a new one", aliases=["songskip", "ss"])
    @commands.cooldown(1, 10.0, type=commands.BucketType.channel)
    async def skipsong(self, ctx):
        print("skipsong")

        await channel_setup(ctx)
        await user_setup(ctx)

        database.lset(str(ctx.channel.id), 3, "1")
        currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
        if currentSongBird != "":  # check if there is bird
            birdPage = wikipedia.page(currentSongBird + "(bird)")
            await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
        else:
            await ctx.send("You need to ask for a bird first!")


def setup(bot):
    bot.add_cog(Skip(bot))
