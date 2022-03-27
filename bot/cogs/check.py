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

import discord
from discord import app_commands
from discord.ext import commands

import bot.voice as voice_functions
from bot.core import better_spellcheck, get_sciname
from bot.data import (
    ContextOrInteraction,
    alpha_codes,
    birdListMaster,
    database,
    get_wiki_url,
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

# from bot.functions import CustomCooldown


# achievement values
achievement = [1, 10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 666, 690, 1000]


class Check(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Check command - argument is the guess
    @app_commands.command(name="check", description="Checks your answer.")
    @app_commands.describe(guess="Your answer")
    # @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    async def check(self, interaction: discord.Interaction, guess: str) -> None:
        logger.info("command: check")

        ctx = ContextOrInteraction(interaction)

        currentBird = database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8")
        if currentBird == "":  # no bird
            await interaction.response.send_message("You must ask for a bird first!")
            return
        # if there is a bird, it checks answer
        sciBird = (await get_sciname(currentBird)).lower().replace("-", " ")
        arg = guess.lower().replace("-", " ")
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

            await interaction.response.send_message(
                f"Correct! Good job! The bird was **{currentBird}**."
                if not race_in_session
                else f"**{ctx.author.mention}**, you are correct! The bird was **{currentBird}**."
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
                await interaction.response.send_message("Sorry, that wasn't the right answer.")
            else:
                database.hset(f"channel:{ctx.channel.id}", "bird", "")
                database.hset(f"channel:{ctx.channel.id}", "answered", "1")
                await interaction.response.send_message("Sorry, the bird was actually **" + currentBird + "**.")
                url = get_wiki_url(ctx, currentBird)
                await ctx.send(url)


async def setup(bot):
    await bot.add_cog(Check(bot))
