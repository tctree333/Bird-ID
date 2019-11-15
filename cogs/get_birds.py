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

import itertools
import random
from discord.ext import commands
from data.data import birdList, database, goatsuckers, songBirds, logger, states, orders
from functions import (
    channel_setup, error_skip, error_skip_goat, error_skip_song, send_bird, send_birdsong, user_setup, check_state_role,
    session_increment
)

BASE_MESSAGE = (
    "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
    "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. " +
    "Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint"
) + "\n*This is a{option}.*"
GS_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="gs", skip_cmd="skipgoat", check_cmd="checkgoat", hint_cmd="hintgoat"
)
SONG_MESSAGE = BASE_MESSAGE.format(
    media="song", new_cmd="song", skip_cmd="skipsong", check_cmd="checksong", hint_cmd="hintsong"
)

class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_bird_(self, ctx, add_on: str = "", bw: bool = False, order: str = ""):
        if add_on == "":
            message = BIRD_MESSAGE.format(option="n image")
        else:
            message = BIRD_MESSAGE.format(option=f" {add_on}")
        
        if order:
            order = order.split(" ")

        logger.info("bird: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[2:-1])

        answered = int(database.hget(f"channel:{str(ctx.channel.id)}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            roles = check_state_role(ctx)
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

                roles = str(database.hget(f"session.data:{ctx.author.id}", "state"))[2:-1].split(" ")
                if roles[0] == "":
                    roles = []
                if not roles:
                    logger.info("no session lists")
                    roles = check_state_role(ctx)
                logger.info(f"addon: {add_on}; bw: {bw}; roles: {roles}")

            if order:
                birds_in_order = set(itertools.chain.from_iterable(orders[o] for o in order))
                if roles:
                    birds_in_state = set(itertools.chain.from_iterable(states[state]["birdList"] for state in roles))
                    birds = list(birds_in_order.intersection(birds_in_state))
                else:
                    birds = list(birds_in_order)
            else:
                if roles:
                    birds = list(set(itertools.chain.from_iterable(states[state]["birdList"] for state in roles)))
                else:
                    birds = birdList
            
            if len(birds) is 0:
                logger.info("no birds for order/state")
                await ctx.send(f"**Sorry, no birds could be found for the order/state combo.**\n*Please try again*")
                return
            logger.info(f"number of birds: {len(birds)}")

            currentBird = random.choice(birds)
            prevB = str(database.hget(f"channel:{str(ctx.channel.id)}", "prevB"))[2:-1]
            while currentBird == prevB:
                currentBird = random.choice(birds)
            database.hset(f"channel:{str(ctx.channel.id)}", "prevB", str(currentBird))
            database.hset(f"channel:{str(ctx.channel.id)}", "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(ctx, currentBird, on_error=error_skip, message=message, addOn=add_on, bw=bw)
            database.hset(f"channel:{str(ctx.channel.id)}", "answered", "0")
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "bird"))[2:-1],
                on_error=error_skip,
                message=message,
                addOn=add_on,
                bw=bw
            )

    async def send_song_(self, ctx):
        songAnswered = int(database.hget(f"channel:{str(ctx.channel.id)}", "sAnswered"))
        # check to see if previous bird was answered
        if songAnswered:  # if yes, give a new bird
            roles = check_state_role(ctx)
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

                roles = str(database.hget(f"session.data:{ctx.author.id}", "state"))[2:-1].split(" ")
                if roles[0] == "":
                    roles = []
                if len(roles) is 0:
                    logger.info("no session lists")
                    roles = check_state_role(ctx)
                logger.info(f"roles: {roles}")

            if roles:
                birds = list(itertools.chain.from_iterable(states[state]["songBirds"] for state in roles))
            else:
                birds = songBirds
            logger.info(f"number of birds: {len(birds)}")

            currentSongBird = random.choice(birds)
            prevS = str(database.hget(f"channel:{str(ctx.channel.id)}", "prevS"))[2:-1]
            while currentSongBird == prevS:
                currentSongBird = random.choice(birds)
            database.hset(f"channel:{str(ctx.channel.id)}", "prevS", str(currentSongBird))
            database.hset(f"channel:{str(ctx.channel.id)}", "sBird", str(currentSongBird))
            logger.info("currentSongBird: " + str(currentSongBird))
            await send_birdsong(ctx, currentSongBird, on_error=error_skip_song, message=SONG_MESSAGE)
            database.hset(f"channel:{str(ctx.channel.id)}", "sAnswered", "0")
        else:
            await send_birdsong(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "sBird"))[2:-1],
                on_error=error_skip_song,
                message=SONG_MESSAGE
            )

    # Bird command - no args
    # help text
    @commands.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile] [bw]")
    # 5 second cooldown
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def bird(self, ctx, *, args_str: str = ""):
        logger.info("command: bird")

        await channel_setup(ctx)
        await user_setup(ctx)

        args = args_str.split(" ")
        logger.info(f"args: {args}")
        if "bw" in args:
            bw = True
        else:
            bw = False
        order_args = set(orders["orders"]).intersection({arg.lower() for arg in args})
        if order_args:
            order = " ".join(order_args).strip()
        else:
            order = ""
        female = "female" in args or "f" in args
        juvenile = "juvenile" in args or "j" in args
        if female and juvenile:
            await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
            return
        elif female:
            add_on = "female"
        elif juvenile:
            add_on = "juvenile"
        else:
            add_on = ""

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("session parameters")

            session_add_on = str(database.hget(f"session.data:{ctx.author.id}", "addon"))[2:-1]
            if add_on == "":
                add_on = session_add_on
            elif add_on == session_add_on:
                add_on = ""
            else:
                await ctx.send("**Juvenile females are not yet supported.**\n*Overriding session options...*")

            if str(database.hget(f"session.data:{ctx.author.id}", "bw"))[2:-1]:
                bw = not bw

        logger.info(f"args: bw: {bw}; addon: {add_on}; order: {order}")
        await ctx.send(f"**Recongnized arguments:** *Black & White*: `{str(bw)}`, " +
                       f"*Female/Juvenile*: `{'None' if add_on == '' else add_on}`, " +
                       f"*Orders*: `{'None' if order == '' else order}`")

        await self.send_bird_(ctx, add_on, bw, order)

    # goatsucker command - no args
    # just for fun, no real purpose
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def goatsucker(self, ctx):
        logger.info("command: goatsucker")

        await channel_setup(ctx)
        await user_setup(ctx)

        answered = int(database.hget(f"channel:{str(ctx.channel.id)}", "gsAnswered"))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

            database.hset(f"channel:{str(ctx.channel.id)}", "gsAnswered", "0")
            currentBird = random.choice(goatsuckers)
            database.hset(f"channel:{str(ctx.channel.id)}", "goatsucker", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(ctx, currentBird, on_error=error_skip_goat, message=GS_MESSAGE)
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                str(database.hget(f"channel:{str(ctx.channel.id)}", "goatsucker"))[2:-1],
                on_error=error_skip_goat,
                message=GS_MESSAGE
            )

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def song(self, ctx):
        logger.info("command: song")

        await channel_setup(ctx)
        await user_setup(ctx)

        logger.info("bird: " + str(database.hget(f"channel:{str(ctx.channel.id)}", "sBird"))[2:-1])
        logger.info("answered: " + str(int(database.hget(f"channel:{str(ctx.channel.id)}", "sAnswered"))))

        await self.send_song_(ctx)

def setup(bot):
    bot.add_cog(Birds(bot))
