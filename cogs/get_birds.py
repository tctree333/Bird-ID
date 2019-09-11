# get_birds.py | commands for getting bird images or songs
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

from random import randint

from discord.ext import commands

from data.data import birdList, database, goatsuckers, songBirds, logger
from functions import (channel_setup, error_skip, error_skip_goat,
                       error_skip_song, send_bird, send_birdsong, user_setup)

BASE_MESSAGE = (
"*Here you go!* \n" +
"**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
"or `b!{skip_cmd}` to get a new bird. " +
"Use `b!{check_cmd} guess` to check your answer. " +
"Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(media="image",new_cmd="bird",skip_cmd="skip",check_cmd="check",hint_cmd="hint")
GS_MESSAGE = BASE_MESSAGE.format(media="image",new_cmd="gs",skip_cmd="skipgoat",check_cmd="checkgoat",hint_cmd="hintgoat")
SONG_MESSAGE = BASE_MESSAGE.format(media="song",new_cmd="song",skip_cmd="skipsong",check_cmd="checksong",hint_cmd="hintsong")
class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Bird command - no args
    # help text
    @commands.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile]")
    # 5 second cooldown
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def bird(self, ctx, add_on=""):
        logger.info("bird")

        await channel_setup(ctx)
        await user_setup(ctx)

        if not (add_on == "female" or add_on == "juvenile" or add_on == ""):
            await ctx.send("This command only takes female, juvenile, or nothing!")
            return

        logger.info("bird: " + str(database.lindex(str(ctx.channel.id), 0))[2:-1])
        logger.info("answered: " + str(int(database.lindex(str(ctx.channel.id), 1))))

        answered = int(database.lindex(str(ctx.channel.id), 1))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            database.lset(str(ctx.channel.id), 1, "0")
            currentBird = birdList[randint(0, len(birdList) - 1)]
            prevB = str(database.lindex(str(ctx.channel.id), 8))[2:-1]
            while currentBird == prevB:
                currentBird = birdList[randint(0, len(birdList) - 1)]
            database.lset(str(ctx.channel.id), 8, str(currentBird))
            database.lset(str(ctx.channel.id), 0, str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(
                ctx,
                currentBird,
                on_error=error_skip,
                message=
                BIRD_MESSAGE,
                addOn=add_on)
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.lindex(str(ctx.channel.id), 0))[2:-1],
                on_error=error_skip,
                message=
                BIRD_MESSAGE,
                addOn=add_on)

    # goatsucker command - no args
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def goatsucker(self, ctx):
        logger.info("goatsucker")

        await channel_setup(ctx)
        await user_setup(ctx)

        answered = int(database.lindex(str(ctx.channel.id), 6))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            database.lset(str(ctx.channel.id), 6, "0")
            currentBird = goatsuckers[randint(0, 2)]
            database.lset(str(ctx.channel.id), 5, str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(
                ctx,
                currentBird,
                on_error=error_skip_goat,
                message=
                GS_MESSAGE
            )
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.lindex(str(ctx.channel.id), 5))[2:-1],
                on_error=error_skip_goat,
                message=
                GS_MESSAGE
            )
            database.lset(str(ctx.channel.id), 6, "0")

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def song(self, ctx):
        logger.info("song")

        await channel_setup(ctx)
        await user_setup(ctx)

        songAnswered = int(database.lindex(str(ctx.channel.id), 3))
        # check to see if previous bird was answered
        if songAnswered:  # if yes, give a new bird
            v = randint(0, len(songBirds) - 1)
            currentSongBird = songBirds[v]
            prevS = str(database.lindex(str(ctx.channel.id), 9))[2:-1]
            while currentSongBird == prevS:
                currentSongBird = songBirds[randint(0, len(songBirds) - 1)]
            database.lset(str(ctx.channel.id), 9, str(currentSongBird))
            database.lset(str(ctx.channel.id), 2, str(currentSongBird))
            logger.info("currentSongBird: " + str(currentSongBird))
            await send_birdsong(
                ctx,
                currentSongBird,
                on_error=error_skip_song,
                message=
                SONG_MESSAGE
            )
            database.lset(str(ctx.channel.id), 3, "0")
        else:
            await send_birdsong(
                ctx,
                str(database.lindex(str(ctx.channel.id), 2))[2:-1],
                on_error=error_skip_song,
                message=
                SONG_MESSAGE
            )
            database.lset(str(ctx.channel.id), 3, "0")


def setup(bot):
    bot.add_cog(Birds(bot))
