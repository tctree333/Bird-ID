# check.py | commands to check answers
# Copyright (C) 2019  EraserBird, person_v1.32, hmmm

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

import discord
import wikipedia
from discord.ext import commands
from data.data import goatsuckers, sciGoat, database, logger
from functions import (bird_setup, channel_setup, spellcheck,
                       user_setup, get_sciname, session_increment)

# achievement values
achievement = [1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690]


class Check(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Check command - argument is the guess
    @commands.command(help='- Checks your answer.', usage="guess", aliases=["guess", "c"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def check(self, ctx, *, arg):
        logger.info("check")

        await channel_setup(ctx)
        await user_setup(ctx)
        currentBird = str(database.hget(
            f"channel:{str(ctx.channel.id)}", "bird"))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentBird)
            sciBird = await get_sciname(currentBird)
            database.hset(f"channel:{str(ctx.channel.id)}", "bird", "")
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")
            if spellcheck(arg, currentBird) is True or spellcheck(
                    arg, sciBird) is True:
                logger.info("correct")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "correct", 1)

                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
                database.zincrby("score", 1, str(ctx.channel.id))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(
                        ctx.message.author.id))) in achievement:
                    number = str(
                        int(
                            database.zscore("users",
                                            str(ctx.message.author.id))))
                    await ctx.send(
                        f"Wow! You have answered {number} birds correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(
                            file=discord.File(img, filename="award.png"))

            else:
                logger.info("incorrect")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "incorrect", 1)

                database.zincrby("incorrect", 1, str(currentBird))
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
            logger.info("currentBird: " +
                        str(currentBird.lower().replace("-", " ")))
            logger.info("args: " + str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks your goatsucker.', usage="guess", aliases=["cg"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def checkgoat(self, ctx, *, arg):
        logger.info("checkgoat")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentBird = str(database.hget(
            f"channel:{str(ctx.channel.id)}", "goatsucker"))[2:-1]
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentBird)
            index = goatsuckers.index(currentBird)
            sciBird = sciGoat[index]
            database.hset(f"channel:{str(ctx.channel.id)}", "gsAnswered", "1")
            database.hset(f"channel:{str(ctx.channel.id)}", "goatsucker", "")
            if spellcheck(arg, currentBird) is True or spellcheck(
                    arg, sciBird) is True:
                logger.info("correct")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "correct", 1)

                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
                database.zincrby("score", 1, str(ctx.channel.id))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(
                        ctx.message.author.id))) in achievement:
                    number = str(
                        int(
                            database.zscore("users",
                                            str(ctx.message.author.id))))
                    await ctx.send(
                        f"Wow! You have answered {number} birds correctly!")
                    filename = 'achievements/' + number + ".PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(
                            file=discord.File(img, filename="award.png"))

            else:
                logger.info("incorrect")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "incorrect", 1)

                database.zincrby("incorrect", 1, str(currentBird))
                await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
                page = wikipedia.page(f"{currentBird} (bird)")
                await ctx.send(page.url)
            logger.info("currentBird: " +
                        str(currentBird.lower().replace("-", " ")))
            logger.info("args: " + str(arg.lower().replace("-", " ")))

    # Check command - argument is the guess
    @commands.command(help='- Checks the song', aliases=["songcheck", "cs", "sc"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def checksong(self, ctx, *, arg):
        logger.info("checksong")

        await channel_setup(ctx)
        await user_setup(ctx)

        currentSongBird = str(database.hget(
            f"channel:{str(ctx.channel.id)}", "sBird"))[2:-1]
        if currentSongBird == "":  # no bird
            await ctx.send("You must ask for a bird call first!")
        else:  # if there is a bird, it checks answer
            await bird_setup(currentSongBird)
            sciBird = await get_sciname(currentSongBird)
            database.hset(f"channel:{str(ctx.channel.id)}", "sBird", "")
            database.hset(f"channel:{str(ctx.channel.id)}", "sAnswered", "1")
            if spellcheck(arg, currentSongBird) is True or spellcheck(
                    arg, sciBird) is True:
                logger.info("correct")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "correct", 1)

                await ctx.send("Correct! Good job!")
                page = wikipedia.page(f"{currentSongBird} (bird)")
                await ctx.send(page.url)
                database.zincrby("score", 1, str(ctx.channel.id))
                database.zincrby("users", 1, str(ctx.message.author.id))
                if int(database.zscore("users", str(
                        ctx.message.author.id))) in achievement:
                    number = str(
                        int(
                            database.zscore("users",
                                            str(ctx.message.author.id))))
                    await ctx.send(
                        f"Wow! You have answered {number} birds correctly!")
                    filename = f"achievements/{number}.PNG"
                    with open(filename, 'rb') as img:
                        await ctx.send(
                            file=discord.File(img, filename="award.png"))

            else:
                logger.info("incorrect")

                if database.exists(f"session.data:{ctx.author.id}"):
                    logger.info("session active")
                    session_increment(ctx, "incorrect", 1)

                database.zincrby("incorrect", 1, str(currentSongBird))
                await ctx.send("Sorry, the bird was actually " + currentSongBird.lower() + ".")
                page = wikipedia.page(f"{currentSongBird} (bird)")
                await ctx.send(page.url)
            logger.info("currentBird: " +
                        str(currentSongBird.lower().replace("-", " ")))
            logger.info("args: " + str(arg.lower().replace("-", " ")))


def setup(bot):
    bot.add_cog(Check(bot))
