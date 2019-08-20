from functions import *


# achievement values
achievement = [10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690]


class Check(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Check command - argument is the guess
    @commands.command(help='- Checks your answer.', usage="guess", aliases=["guess", "c"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def check(self, ctx, *, arg):
        print("check")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            index = birdList.index(currentBird)
            sciBird = sciBirdList[index]
            database.lset(str(ctx.channel.id), 0, "")
            database.lset(str(ctx.channel.id), 1, "1")
            if spellcheck(arg.lower().replace("-", " "), currentBird.lower().replace("-", " ")) is True:
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
                database.lset(str(ctx.channel.id), 4, str(
                    int(database.lindex(str(ctx.channel.id), 4))+1))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                    number = str(
                        int(database.zscore("users", str(ctx.message.author.id))))
                    await ctx.send(f"Wow! You have answered {number} birds correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(file=discord.File(img, filename="award.png"))

            else:
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
            print("currentBird: "+str(currentBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks your goatsucker.', usage="guess", aliases=["cg"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def checkgoat(self, ctx, *, arg):
        print("checkgoat")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            index = birdList.index(currentBird)
            sciBird = sciBirdList[index]
            database.lset(str(ctx.channel.id), 6, "1")
            database.lset(str(ctx.channel.id), 5, "")
            if spellcheck(arg.lower().replace("-", " "), currentBird.lower().replace("-", " ")) is True:
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
                database.lset(str(ctx.channel.id), 4, str(
                    int(database.lindex(str(ctx.channel.id), 4))+1))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                    number = str(
                        int(database.zscore("users", str(ctx.message.author.id))))
                    await ctx.send(f"Wow! You have answered {number} birds correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(file=discord.File(img, filename="award.png"))

            else:
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
            print("currentBird: "+str(currentBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks the song', aliases=["songcheck", "cs", "sc"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def checksong(self, ctx, *, arg):
        print("checksong")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
        if currentSongBird == "":  # no bird
            await ctx.send("You must ask for a bird call first!")
        else:  # if there is a bird, it checks answer
            index = songBirds.index(currentSongBird)
            sciBird = sciSongBirds[index]
            database.lset(str(ctx.channel.id), 2, "")
            database.lset(str(ctx.channel.id), 3, "1")
            if spellcheck(arg.lower().replace("-", " "), currentSongBird.lower().replace("-", " ")) is True:
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
                database.lset(str(ctx.channel.id), 4, str(
                    int(database.lindex(str(ctx.channel.id), 4))+1))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                    number = str(
                        int(database.zscore("users", str(ctx.message.author.id))))
                    await ctx.send(f"Wow! You have answered {number} birds correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(file=discord.File(img, filename="award.png"))

            else:
                await ctx.send("Sorry, the bird was actually " + currentSongBird.lower() + ".")
                page = wikipedia.page(sciBird)
                await ctx.send(page.url)
            print("currentBird: "+str(currentSongBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))


def setup(bot):
    bot.add_cog(Check(bot))
