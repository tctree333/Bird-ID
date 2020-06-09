# get_birds.py | commands for getting bird images or songs
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

import random
import string

from discord.ext import commands

from bot.core import send_bird, send_birdsong
from bot.data import database, goatsuckers, logger, states, taxons
from bot.functions import (CustomCooldown, bird_setup, build_id_list,
                           check_state_role, error_skip, error_skip_goat,
                           error_skip_song, session_increment)
from bot.filters import Filter

BASE_MESSAGE = (
    "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
    "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. " +
    "Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint"
)
GS_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="gs", skip_cmd="skipgoat", check_cmd="checkgoat", hint_cmd="hintgoat"
)
SONG_MESSAGE = BASE_MESSAGE.format(
    media="song", new_cmd="song", skip_cmd="skipsong", check_cmd="checksong", hint_cmd="hintsong"
)

class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def increment_bird_frequency(self, ctx, bird):
        bird_setup(ctx, bird)
        database.zincrby("frequency.bird:global", 1, string.capwords(bird))

    async def send_bird_(self, ctx, filters: Filter, taxon_str: str = "", role_str: str = ""):
        if taxon_str:
            taxon = taxon_str.split(" ")
        else:
            taxon = []

        if role_str:
            roles = role_str.split(" ")
        else:
            roles = []

        logger.info("bird: " + database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"))

        answered = int(database.hget(f"channel:{ctx.channel.id}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            session_increment(ctx, "total", 1)

            logger.info(f"filters: {filters}; taxon: {taxon}; roles: {roles}")

            await ctx.send(
                f"**Recognized arguments:** " +
                f"*Active Filters*: `{'`, `'.join(filters.display())}`, " +
                f"*Taxons*: `{'None' if taxon == [] else ' '.join(taxon)}`, " +
                f"*Detected State*: `{'None' if roles == [] else ' '.join(roles)}`"
            )

            custom_role = {i if i.startswith("CUSTOM:") else "" for i in roles}
            custom_role.discard("")
            if database.exists(f"race.data:{ctx.channel.id}") and len(custom_role) == 1:
                custom_role = custom_role.pop()
                roles.remove(custom_role)
                roles.append("CUSTOM")
                user_id = custom_role.split(":")[1]
                birds = build_id_list(user_id=user_id, taxon=taxon, roles=roles, media="image")
            else:
                birds = build_id_list(user_id=ctx.author.id, taxon=taxon, roles=roles, media="image")

            if not birds:
                logger.info("no birds for taxon/state")
                await ctx.send(f"**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*")
                return

            currentBird = random.choice(birds)
            self.increment_bird_frequency(ctx, currentBird)

            prevB = database.hget(f"channel:{ctx.channel.id}", "prevB").decode("utf-8")
            while currentBird == prevB and len(birds) > 1:
                currentBird = random.choice(birds)
            database.hset(f"channel:{ctx.channel.id}", "prevB", str(currentBird))
            database.hset(f"channel:{ctx.channel.id}", "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            database.hset(f"channel:{ctx.channel.id}", "answered", "0")
            await send_bird(ctx, currentBird, filters, on_error=error_skip, message=BIRD_MESSAGE)
        else:  # if no, give the same bird
            await ctx.send(
                f"**Active Filters**: `{'`, `'.join(filters.display())}`"
            )
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"),
                filters,
                on_error=error_skip,
                message=BIRD_MESSAGE,
            )

    async def send_song_(self, ctx):
        songAnswered = int(database.hget(f"channel:{ctx.channel.id}", "sAnswered"))
        # check to see if previous bird was answered
        if songAnswered:  # if yes, give a new bird
            roles = check_state_role(ctx)
            session_increment(ctx, "total", 1)
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")

                roles = database.hget(f"session.data:{ctx.author.id}", "state").decode("utf-8").split(" ")
                if roles[0] == "":
                    roles = []
                if not roles:
                    logger.info("no session lists")
                    roles = check_state_role(ctx)
                logger.info(f"roles: {roles}")

            birds = build_id_list(user_id=ctx.author.id, roles=roles, media="songs")

            if not birds:
                logger.info("no birds for taxon/state")
                await ctx.send(f"**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*")
                return

            currentSongBird = random.choice(birds)
            self.increment_bird_frequency(ctx, currentSongBird)

            prevS = database.hget(f"channel:{ctx.channel.id}", "prevS").decode("utf-8")
            while currentSongBird == prevS and len(birds) > 1:
                currentSongBird = random.choice(birds)
            database.hset(f"channel:{ctx.channel.id}", "prevS", str(currentSongBird))
            database.hset(f"channel:{ctx.channel.id}", "sBird", str(currentSongBird))
            logger.info("currentSongBird: " + str(currentSongBird))
            database.hset(f"channel:{ctx.channel.id}", "sAnswered", "0")
            await send_birdsong(ctx, currentSongBird, on_error=error_skip_song, message=SONG_MESSAGE)
        else:
            await send_birdsong(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "sBird").decode("utf-8"),
                on_error=error_skip_song,
                message=SONG_MESSAGE
            )

    # Bird command - no args
    # help text
    @commands.command(
        help='- Sends a random bird image for you to ID', aliases=["b"], usage="[filters] [order/family] [state]"
    )
    # 5 second cooldown
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def bird(self, ctx, *, args_str: str = ""):
        logger.info("command: bird")

        filters = Filter().parse(args_str)

        args = args_str.split(" ")
        logger.info(f"args: {args}")

        if not database.exists(f"race.data:{ctx.channel.id}"):
            roles = check_state_role(ctx)

            taxon_args = set(taxons.keys()).intersection({arg.lower() for arg in args})
            if taxon_args:
                taxon = " ".join(taxon_args).strip()
            else:
                taxon = ""

            state_args = set(states.keys()).intersection({arg.upper() for arg in args})
            if state_args:
                state = " ".join(state_args).strip()
            else:
                state = ""

            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session parameters")

                if taxon_args:
                    toggle_taxon = list(taxon_args)
                    current_taxons = database.hget(f"session.data:{ctx.author.id}", "taxon").decode("utf-8").split(" ")
                    add_taxons = []
                    logger.info(f"toggle taxons: {toggle_taxon}")
                    logger.info(f"current taxons: {current_taxons}")
                    for o in set(toggle_taxon).symmetric_difference(set(current_taxons)):
                        add_taxons.append(o)
                    logger.info(f"adding taxons: {add_taxons}")
                    taxon = " ".join(add_taxons).strip()
                else:
                    taxon = database.hget(f"session.data:{ctx.author.id}", "taxon").decode("utf-8")

                roles = database.hget(f"session.data:{ctx.author.id}", "state").decode("utf-8").split(" ")
                if roles[0] == "":
                    roles = []
                if not roles:
                    logger.info("no session lists")
                    roles = check_state_role(ctx)

                session_filter = int(database.hget(f"session.data:{ctx.author.id}", "filter"))
                if Filter().from_int(session_filter).quality and filters.quality == Filter().quality:
                    filters.xor(Filter()) # clear defaults
                filters.xor(session_filter)

            if state_args:
                toggle_states = list(state_args)
                add_states = []
                logger.info(f"toggle states: {toggle_states}")
                logger.info(f"current states: {roles}")
                for s in set(toggle_states).symmetric_difference(set(roles)):
                    add_states.append(s)
                logger.info(f"adding states: {add_states}")
                state = " ".join(add_states).strip()
            else:
                state = " ".join(roles).strip()

        else:
            logger.info("race parameters")

            race_filter = int(database.hget(f"race.data:{ctx.channel.id}", "filter"))
            if Filter().from_int(race_filter).quality and filters.quality == Filter().quality:
                filters.xor(Filter()) # clear defaults
            filters.xor(race_filter)

            taxon = database.hget(f"race.data:{ctx.channel.id}", "taxon").decode("utf-8")
            state = database.hget(f"race.data:{ctx.channel.id}", "state").decode("utf-8")

        logger.info(f"args: filters: {filters}; taxon: {taxon}; state: {state}")

        await self.send_bird_(ctx, filters, taxon, state)

    # goatsucker command - no args
    # just for fun, no real purpose
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def goatsucker(self, ctx):
        logger.info("command: goatsucker")

        answered = int(database.hget(f"channel:{ctx.channel.id}", "gsAnswered"))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            session_increment(ctx, "total", 1)

            database.hset(f"channel:{ctx.channel.id}", "gsAnswered", "0")
            currentBird = random.choice(goatsuckers)
            self.increment_bird_frequency(ctx, currentBird)

            database.hset(f"channel:{ctx.channel.id}", "goatsucker", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(ctx, currentBird, Filter(), on_error=error_skip_goat, message=GS_MESSAGE)
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "goatsucker").decode("utf-8"),
                Filter(),
                on_error=error_skip_goat,
                message=GS_MESSAGE
            )

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def song(self, ctx):
        logger.info("command: song")

        logger.info("bird: " + database.hget(f"channel:{ctx.channel.id}", "sBird").decode("utf-8"))
        logger.info("answered: " + str(int(database.hget(f"channel:{ctx.channel.id}", "sAnswered"))))

        await self.send_song_(ctx)

def setup(bot):
    bot.add_cog(Birds(bot))
