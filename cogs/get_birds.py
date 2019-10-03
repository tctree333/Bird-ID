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
from data.data import birdList, database, goatsuckers, songBirds, logger, states
from functions import (channel_setup, error_skip, error_skip_goat,
                       error_skip_song, send_bird, send_birdsong, user_setup,
                       check_state_role, session_increment)

BASE_MESSAGE = (
    "*Here you go!* \n" +
    "**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
    "or `b!{skip_cmd}` to get a new bird. " +
    "Use `b!{check_cmd} guess` to check your answer. " +
    "Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint") + "\n*This is a{option}.*"
GS_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="gs", skip_cmd="skipgoat", check_cmd="checkgoat", hint_cmd="hintgoat")
SONG_MESSAGE = BASE_MESSAGE.format(
    media="song", new_cmd="song", skip_cmd="skipsong", check_cmd="checksong", hint_cmd="hintsong")


class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Bird command - no args
    # help text
    @commands.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile] [bw]")
    # 5 second cooldown
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def bird(self, ctx, add_on="", bw=""):
        logger.info("bird")

        await channel_setup(ctx)
        await user_setup(ctx)

        if not (add_on == "female" or add_on == "juvenile" or add_on == "bw"or add_on == ""):
            await ctx.send("This command only takes female, juvenile, or nothing!")
            return

        if add_on == "bw":
            add_on = ""
            bw = True
        elif bw == "bw":
            bw = True
        else:
            bw = False

        roles = check_state_role(ctx)

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("session parameters")
            session_increment(ctx, "total", 1)

            session_add_on = str(database.hget(f"session.data:{ctx.author.id}", "addon"))[2:-1]
            if add_on == "":
                add_on = session_add_on
            elif add_on == session_add_on:
                add_on = ""
            else:
                await ctx.send("**Juvenile females are not yet supported.**\n*Overriding session options...*")

            if len(str(database.hget(f"session.data:{ctx.author.id}", "bw"))[2:-1]) is not 0:
                bw = not bw

            roles = str(database.hget(f"session.data:{ctx.author.id}", "state"))[2:-1].split(" ")
            if roles[0] == "":
                roles = []
            logger.info(f"addon: {add_on}; bw: {bw}; roles: {roles}")
        
        if add_on == "":
            message = BIRD_MESSAGE.format(option="n image")
        else:
            message = BIRD_MESSAGE.format(option=f" {add_on}")

        logger.info(
            "bird: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[2:-1])
        logger.info("answered: " +
                    str(int(database.hget(f"channel:{str(ctx.channel.id)}", "answered"))))

        answered = int(database.hget(
            f"channel:{str(ctx.channel.id)}", "answered"))

        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "0")

            birds = []
            if roles:
                for state in roles:
                    birds += states[state]["birdList"]
                birds = list(set(birds))
            else:
                birds += birdList
            logger.info(f"number of birds: {len(birds)}")

            currentBird = birds[randint(0, len(birds) - 1)]
            prevB = str(database.hget(
                f"channel:{str(ctx.channel.id)}", "prevB"))[2:-1]
            while currentBird == prevB:
                currentBird = birds[randint(0, len(birds) - 1)]
            database.hset(f"channel:{str(ctx.channel.id)}",
                          "prevB", str(currentBird))
            database.hset(f"channel:{str(ctx.channel.id)}",
                          "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(
                ctx,
                currentBird,
                on_error=error_skip,
                message=message,
                addOn=add_on,
                bw=bw)
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[
                    2:-1],
                on_error=error_skip,
                message=message,
                addOn=add_on,
                bw=bw)

    # goatsucker command - no args
    # just for fun, no real purpose
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def goatsucker(self, ctx):
        logger.info("goatsucker")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("session active")
            session_increment(ctx, "total", 1)

        answered = int(database.hget(
            f"channel:{str(ctx.channel.id)}", "gsAnswered"))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            database.hset(f"channel:{str(ctx.channel.id)}", "gsAnswered", "0")
            currentBird = goatsuckers[randint(0, 2)]
            database.hset(f"channel:{str(ctx.channel.id)}",
                          "goatsucker", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(
                ctx,
                currentBird,
                on_error=error_skip_goat,
                message=GS_MESSAGE
            )
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "goatsucker"))[
                    2:-1],
                on_error=error_skip_goat,
                message=GS_MESSAGE
            )

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def song(self, ctx):
        logger.info("song")

        await channel_setup(ctx)
        await user_setup(ctx)

        roles = check_state_role(ctx)

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("session active")
            session_increment(ctx, "total", 1)

            roles = str(database.hget(f"session.data:{ctx.author.id}", "state"))[2:-1].split(" ")
            if roles[0] == "":
                roles = []
            logger.info(f"roles: {roles}")

        logger.info(
            "bird: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "sBird"))[2:-1])
        logger.info("answered: " +
                    str(int(database.hget(f"channel:{str(ctx.channel.id)}", "sAnswered"))))

        songAnswered = int(database.hget(
            f"channel:{str(ctx.channel.id)}", "sAnswered"))
        # check to see if previous bird was answered
        if songAnswered:  # if yes, give a new bird
            birds = []
            if roles:
                for state in roles:
                    birds += states[state]["songBirds"]
                birds = list(set(birds))
            else:
                birds += songBirds
            logger.info(f"number of birds: {len(birds)}")

            currentSongBird = birds[randint(0, len(birds) - 1)]
            prevS = str(database.hget(
                f"channel:{str(ctx.channel.id)}", "prevS"))[2:-1]
            while currentSongBird == prevS:
                currentSongBird = birds[randint(0, len(birds) - 1)]
            database.hset(f"channel:{str(ctx.channel.id)}",
                          "prevS", str(currentSongBird))
            database.hset(f"channel:{str(ctx.channel.id)}",
                          "sBird", str(currentSongBird))
            logger.info("currentSongBird: " + str(currentSongBird))
            await send_birdsong(
                ctx,
                currentSongBird,
                on_error=error_skip_song,
                message=SONG_MESSAGE
            )
            database.hset(f"channel:{str(ctx.channel.id)}", "sAnswered", "0")
        else:
            await send_birdsong(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "sBird"))[
                    2:-1],
                on_error=error_skip_song,
                message=SONG_MESSAGE
            )


def setup(bot):
    bot.add_cog(Birds(bot))
