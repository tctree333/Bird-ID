# check.py | commands to check answers
# Copyright (C) 2019-2020  EraserBird, person_v1.32, hmmm

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
from discord.ext import commands

from bot.core import get_sciname, spellcheck
from bot.data import database, get_wiki_url, logger
from bot.filters import Filter
from bot.functions import (CustomCooldown, bird_setup, incorrect_increment,
                           score_increment, session_increment,
                           streak_increment)

# achievement values
achievement = [1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690, 1000]


class Check(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Check command - argument is the guess
    @commands.command(
        help="- Checks your answer.", usage="guess", aliases=["guess", "c"]
    )
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    async def check(self, ctx, *, arg):
        logger.info("command: check")

        currentBird = database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8")
        if currentBird == "":  # no bird
            await ctx.send("You must ask for a bird first!")
            return
        # if there is a bird, it checks answer
        sciBird = (await get_sciname(currentBird)).lower().replace("-", " ")
        arg = arg.lower().replace("-", " ")
        currentBird = currentBird.lower().replace("-", " ")
        logger.info("currentBird: " + currentBird)
        logger.info("arg: " + arg)

        bird_setup(ctx, currentBird)

        race_in_session = bool(database.exists(f"race.data:{ctx.channel.id}"))
        if race_in_session:
            logger.info("race in session")
            if database.hget(f"race.data:{ctx.channel.id}", "strict"):
                logger.info("strict spelling")
                correct = arg in (currentBird, sciBird)
            else:
                logger.info("spelling leniency")
                correct = spellcheck(arg, currentBird) or spellcheck(arg, sciBird)
        else:
            logger.info("no race")
            if database.hget(f"session.data:{ctx.author.id}", "strict"):
                logger.info("strict spelling")
                correct = arg in (currentBird, sciBird)
            else:
                logger.info("spelling leniency")
                correct = spellcheck(arg, currentBird) or spellcheck(arg, sciBird)

        if correct:
            logger.info("correct")

            database.hset(f"channel:{ctx.channel.id}", "bird", "")
            database.hset(f"channel:{ctx.channel.id}", "answered", "1")

            session_increment(ctx, "correct", 1)
            streak_increment(ctx, 1)

            await ctx.send(
                "Correct! Good job!"
                if not race_in_session
                else f"**{ctx.author.mention}**, you are correct!"
            )
            url = get_wiki_url(ctx, currentBird)
            await ctx.send(url)
            score_increment(ctx, 1)
            if int(database.zscore("users:global", str(ctx.author.id))) in achievement:
                number = str(int(database.zscore("users:global", str(ctx.author.id))))
                await ctx.send(f"Wow! You have answered {number} birds correctly!")
                filename = f"bot/media/achievements/{number}.PNG"
                with open(filename, "rb") as img:
                    await ctx.send(file=discord.File(img, filename="award.png"))

            if race_in_session:
                media = database.hget(f"race.data:{ctx.channel.id}", "media").decode(
                    "utf-8"
                )

                limit = int(database.hget(f"race.data:{ctx.channel.id}", "limit"))
                first = database.zrevrange(f"race.scores:{ctx.channel.id}", 0, 0, True)[
                    0
                ]
                if int(first[1]) >= limit:
                    logger.info("race ending")
                    race = self.bot.get_cog("Race")
                    await race.stop_race_(ctx)
                else:
                    logger.info(f"auto sending next bird {media}")
                    filter_int, taxon, state = database.hmget(
                        f"race.data:{ctx.channel.id}", ["filter", "taxon", "state"]
                    )
                    birds = self.bot.get_cog("Birds")
                    await birds.send_bird_(
                        ctx,
                        media,
                        Filter.from_int(int(filter_int)),
                        taxon.decode("utf-8"),
                        state.decode("utf-8"),
                    )

        else:
            logger.info("incorrect")

            streak_increment(ctx, None)  # reset streak
            session_increment(ctx, "incorrect", 1)
            incorrect_increment(ctx, str(currentBird), 1)

            if race_in_session:
                await ctx.send("Sorry, that wasn't the right answer.")
            else:
                database.hset(f"channel:{ctx.channel.id}", "bird", "")
                database.hset(f"channel:{ctx.channel.id}", "answered", "1")
                await ctx.send("Sorry, the bird was actually " + currentBird + ".")
                url = get_wiki_url(ctx, currentBird)
                await ctx.send(url)


def setup(bot):
    bot.add_cog(Check(bot))
