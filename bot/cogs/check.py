# check.py | commands to check answers
# Copyright (C) 2019-2021  EraserBird, person_v1.32, hmmm

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

import string
from difflib import get_close_matches

import discord
from discord.ext import commands

import bot.voice as voice_functions
from bot.core import better_spellcheck, get_sciname
from bot.data import (
    alpha_codes,
    birdListMaster,
    database,
    format_wiki_url,
    logger,
    sci_screech_owls,
    sciListMaster,
    screech_owls,
)
from bot.data_functions import (
    bird_setup,
    incorrect_increment,
    score_increment,
    session_increment,
    streak_increment,
)
from bot.filters import Filter
from bot.functions import CustomCooldown

# achievement values
achievement = [1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690, 1000]


class Check(commands.Cog):
    def __init__(self, bot: commands.Bot):
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
        alpha_code = alpha_codes.get(string.capwords(currentBird), "")
        logger.info("currentBird: " + currentBird)
        logger.info("arg: " + arg)

        bird_setup(ctx, currentBird)

        accepted_answers = [currentBird, sciBird]
        if currentBird == "screech owl":
            accepted_answers += screech_owls
            accepted_answers += sci_screech_owls

        race_in_session = bool(database.exists(f"race.data:{ctx.channel.id}"))
        if race_in_session:
            logger.info("race in session")
            if database.hget(f"race.data:{ctx.channel.id}", "strict"):
                logger.info("strict spelling")
                correct = arg in accepted_answers
            else:
                logger.info("spelling leniency")
                correct = better_spellcheck(
                    arg, accepted_answers, birdListMaster + sciListMaster
                )

            if not correct and database.hget(f"race.data:{ctx.channel.id}", "alpha"):
                logger.info("checking alpha codes")
                correct = arg.upper() == alpha_code
        else:
            logger.info("no race")
            if database.hget(f"session.data:{ctx.author.id}", "strict"):
                logger.info("strict spelling")
                correct = arg in accepted_answers
            else:
                logger.info("spelling leniency")
                correct = (
                    better_spellcheck(
                        arg, accepted_answers, birdListMaster + sciListMaster
                    )
                    or arg.upper() == alpha_code
                )

        if correct:
            logger.info("correct")

            database.hset(f"channel:{ctx.channel.id}", "bird", "")
            database.hset(f"channel:{ctx.channel.id}", "answered", "1")

            session_increment(ctx, "correct", 1)
            streak_increment(ctx, 1)
            database.zincrby(
                f"correct.user:{ctx.author.id}", 1, string.capwords(str(currentBird))
            )

            if (
                race_in_session
                and Filter.from_int(
                    int(database.hget(f"race.data:{ctx.channel.id}", "filter"))
                ).vc
            ):
                await voice_functions.stop(ctx, silent=True)

            await ctx.send(
                f"Correct! Good job! The bird was **{currentBird}**."
                if not race_in_session
                else f"**{ctx.author.mention}**, you are correct! The bird was **{currentBird}**."
            )
            url = format_wiki_url(ctx, currentBird)
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
                await ctx.send("Sorry, the bird was actually **" + currentBird + "**.")
                url = format_wiki_url(ctx, currentBird)
                await ctx.send(url)

    async def race_autocheck(self, message: discord.Message):
        if not database.exists(f"race.data:{message.channel.id}"):
            return
        if (
            len(message.content.strip()) == 4
            and message.content.strip().upper() in alpha_codes.values()
            and database.hget(f"race.data:{message.channel.id}", "alpha")
        ) or len(
            get_close_matches(
                string.capwords(message.content.strip().replace("-", " ")),
                birdListMaster + sciListMaster,
            )
        ) != 0:
            logger.info("race autocheck found: checking")
            ctx = commands.Context(
                message=message,
                bot=self.bot,
                prefix="race-autocheck",
            )
            await self.check(ctx, arg=message.content)


def setup(bot):
    cog = Check(bot)
    bot.add_message_handler(cog.race_autocheck)
    bot.add_cog(cog)
