# check.py | commands to check answers
# Copyright (C) 2019  EraserBird, person_v1.32

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from functions import *


# achievement values
achievement = [1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690]


class Check(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Check command - argument is the guess
    @commands.command(help='- Checks your answer.', usage="guess", aliases=["guess", "c"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def check(self, ctx, *, arg):
        print("check")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentBird)
            index = birdList.index(currentBird)
            sciBird = sciBirdList[index]
            database.lset(str(ctx.channel.id), 0, "")
            database.lset(str(ctx.channel.id), 1, "1")
            if spellcheck(arg, currentBird) is True or spellcheck(arg, sciBird) is True:
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentBird} (bird)")
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
                database.zincrby("incorrect", 1, str(currentBird))
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
            print("currentBird: "+str(currentBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks your goatsucker.', usage="guess", aliases=["cg"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def checkgoat(self, ctx, *, arg):
        print("checkgoat")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentBird)
            index = goatsuckers.index(currentBird)
            sciBird = sciGoat[index]
            database.lset(str(ctx.channel.id), 6, "1")
            database.lset(str(ctx.channel.id), 5, "")
            if spellcheck(arg, currentBird) is True or spellcheck(arg, sciBird) is True:
                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentBird} (bird)")
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
                database.zincrby("incorrect", 1, str(currentBird))
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
            print("currentBird: "+str(currentBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks the song', aliases=["songcheck", "cs", "sc"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def checksong(self, ctx, *, arg):
        print("checksong")

        await channel_setup(ctx)
        await user_setup(ctx)

        global achievement

        currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
        if currentSongBird == "":  # no bird
            await ctx.send("You must ask for a bird call first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentSongBird)
            index = songBirds.index(currentSongBird)
            sciBird = sciSongBirds[index]
            database.lset(str(ctx.channel.id), 2, "")
            database.lset(str(ctx.channel.id), 3, "1")
            if spellcheck(arg, currentSongBird) is True or spellcheck(arg, sciBird) is True:

                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentSongBird} (bird)")
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
                database.zincrby("incorrect", 1, str(currentSongBird))
                await ctx.send("Sorry, the bird was actually " + currentSongBird.lower() + ".")
                page = wikipedia.page(f"{currentSongBird} (bird)")
                await ctx.send(page.url)
            print("currentBird: "+str(currentSongBird.lower().replace("-", " ")))
            print("args: "+str(arg.lower().replace("-", " ")))


def setup(bot):
    bot.add_cog(Check(bot))
