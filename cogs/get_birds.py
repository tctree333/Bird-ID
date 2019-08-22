from functions import *


class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Bird command - no args
    # help text
    @commands.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile]")
    # 10 second cooldown
    @commands.cooldown(1, 10.0, type=commands.BucketType.channel)
    async def bird(self, ctx, add_on=""):
        print("bird")

        await channel_setup(ctx)
        await user_setup(ctx)

        if not (add_on == "female" or add_on == "juvenile" or add_on == ""):
            await ctx.send("This command only takes female, juvenile, or nothing!")
            return

        print("bird: "+str(database.lindex(str(ctx.channel.id), 0))[2:-1])
        print("answered: "+str(int(database.lindex(str(ctx.channel.id), 1))))

        answered = int(database.lindex(str(ctx.channel.id), 1))
        # check to see if previous bird was answered
        if answered == True:  # if yes, give a new bird
            database.lset(str(ctx.channel.id), 1, "0")
            currentBird = birdList[randint(0, len(birdList)-1)]
            prevB = str(database.lindex(str(ctx.channel.id), 8))[2:-1]
            while currentBird == prevB:
                currentBird = birdList[randint(0, len(birdList)-1)]
            database.lset(str(ctx.channel.id), 8, str(currentBird))
            database.lset(str(ctx.channel.id), 0, str(currentBird))
            print("currentBird: "+str(currentBird))
            await send_bird(ctx, currentBird, on_error=error_skip, message="*Here you go!* \n**Use `b!bird` again to get a new picture of the same bird, or `b!skip` to get a new bird. Use `b!check guess` to check your answer. Use `b!hint` for a hint.**", addOn=add_on)
        else:  # if no, give the same bird
            await send_bird(ctx, str(database.lindex(str(ctx.channel.id), 0))[2:-1], on_error=error_skip, message="*Here you go!* \n**Use `b!bird` again to get a new picture of the same bird, or `b!skip` to get a new bird. Use `b!check guess` to check your answer.**", addOn=add_on)
            database.lset(str(ctx.channel.id), 1, "0")

    # goatsucker command - no args
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def goatsucker(self, ctx):
        print("goatsucker")

        await channel_setup(ctx)
        await user_setup(ctx)

        goatsuckers = ["Common Pauraque",
                       "Chuck-will's-widow", "Whip-poor-will"]
        answered = int(database.lindex(str(ctx.channel.id), 6))
        # check to see if previous bird was answered
        if answered == True:  # if yes, give a new bird
            database.lset(str(ctx.channel.id), 6, "0")
            currentBird = goatsuckers[randint(0, 2)]
            database.lset(str(ctx.channel.id), 5, str(currentBird))
            print("currentBird: "+str(currentBird))
            await send_bird(ctx, currentBird, message="*Here you go!* \n**Use `b!bird` again to get a new picture of the same goatsucker, or `b!skipgoat` to get a new bird. Use `b!checkgoat guess` to check your answer. Use `b!hint` for a hint.**")
        else:  # if no, give the same bird
            await send_bird(ctx, str(database.lindex(str(ctx.channel.id), 5))[2:-1], message="*Here you go!* \n**Use `b!bird` again to get a new picture of the same bird, or `b!skip` to get a new bird. Use `b!check guess` to check your answer.**")
            database.lset(str(ctx.channel.id), 6, "0")

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.cooldown(1, 10.0, type=commands.BucketType.channel)
    async def song(self, ctx):
        print("song")

        await channel_setup(ctx)
        await user_setup(ctx)

        songAnswered = int(database.lindex(str(ctx.channel.id), 3))
        # check to see if previous bird was answered
        if songAnswered == True:  # if yes, give a new bird
            v = randint(0, len(songBirds)-1)
            currentSongBird = songBirds[v]
            prevS = str(database.lindex(str(ctx.channel.id), 9))[2:-1]
            while currentSongBird == prevS:
                currentSongBird = songBirds[randint(0, len(songBirds)-1)]
            database.lset(str(ctx.channel.id), 9, str(currentSongBird))
            database.lset(str(ctx.channel.id), 2, str(currentSongBird))
            print("currentSongBird: "+str(currentSongBird))
            await send_birdsong(ctx, currentSongBird, message="*Here you go!* \n**Use `b!song` again to get a new sound of the same bird, or `b!skipsong` to get a new bird. Use `b!checksong guess` to check your answer. Use `b!hintsong` for a hint.**")
            database.lset(str(ctx.channel.id), 3, "0")
        else:
            await send_birdsong(ctx, str(database.lindex(str(ctx.channel.id), 2))[2:-1], message="*Here you go!* \n**Use `b!song` again to get a new sound of the same bird, or `b!skipsong` to get a new bird. Use `b!checksong guess` to check your answer. Use `b!hintsong` for a hint.**")
            database.lset(str(ctx.channel.id), 3, "0")


def setup(bot):
    bot.add_cog(Birds(bot))
