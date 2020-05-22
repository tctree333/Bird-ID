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

from discord.ext import commands

from bot.data import (birdList, database, goatsuckers, logger, songBirds,
                      states, taxons)
from bot.functions import (CustomCooldown, build_id_list, channel_setup,
                           check_state_role, error_skip, error_skip_goat,
                           error_skip_song, send_bird, send_birdsong,
                           session_increment, user_setup)

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

    async def send_bird_(self, ctx, add_on: str = "", bw: bool = False, taxon_str: str = "", role_str: str = ""):
        if add_on == "":
            message = BIRD_MESSAGE.format(option="n image")
        else:
            message = BIRD_MESSAGE.format(option=f" {add_on}")

        if taxon_str:
            taxon = taxon_str.split(" ")
        else:
            taxon = []

        if role_str:
            roles = role_str.split(" ")
        else:
            roles = []

        if not isinstance(bw, bool):
            bw = bw == "bw"

        logger.info("bird: " + database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"))

        answered = int(database.hget(f"channel:{ctx.channel.id}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

            logger.info(f"addon: {add_on}; bw: {bw}; taxon: {taxon}; roles: {roles}")

            await ctx.send(
                f"**Recognized arguments:** *Black & White*: `{bw}`, " +
                f"*Female/Juvenile*: `{'None' if add_on == '' else add_on}`, " +
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
            prevB = database.hget(f"channel:{ctx.channel.id}", "prevB").decode("utf-8")
            while currentBird == prevB and len(birds) > 1:
                currentBird = random.choice(birds)
            database.hset(f"channel:{ctx.channel.id}", "prevB", str(currentBird))
            database.hset(f"channel:{ctx.channel.id}", "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            database.hset(f"channel:{ctx.channel.id}", "answered", "0")
            await send_bird(ctx, currentBird, on_error=error_skip, message=message, addOn=add_on, bw=bw)
        else:  # if no, give the same bird
            await ctx.send(
                f"**Recognized arguments:** *Black & White*: `{bw}`, " +
                f"*Female/Juvenile*: `{'None' if add_on == '' else add_on}`"
            )
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"),
                on_error=error_skip,
                message=message,
                addOn=add_on,
                bw=bw
            )

    async def send_song_(self, ctx):
        songAnswered = int(database.hget(f"channel:{ctx.channel.id}", "sAnswered"))
        # check to see if previous bird was answered
        if songAnswered:  # if yes, give a new bird
            roles = check_state_role(ctx)
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

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
        help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile] [bw] [order/family]"
    )
    # 5 second cooldown
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def bird(self, ctx, *, args_str: str = ""):
        logger.info("command: bird")

        await channel_setup(ctx)
        await user_setup(ctx)

        args = args_str.split(" ")
        logger.info(f"args: {args}")

        bw = "bw" in args

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

                session_add_on = database.hget(f"session.data:{ctx.author.id}", "addon").decode("utf-8")
                if add_on == "":
                    add_on = session_add_on
                elif add_on == session_add_on:
                    add_on = ""
                elif session_add_on == "":
                    add_on = add_on
                else:
                    await ctx.send("**Juvenile females are not yet supported.**\n*Overriding session options...*")

                if database.hget(f"session.data:{ctx.author.id}", "bw").decode("utf-8"):
                    bw = not bw

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

            race_add_on = database.hget(f"race.data:{ctx.channel.id}", "addon").decode("utf-8")
            if add_on == "":
                add_on = race_add_on
            elif add_on == race_add_on:
                add_on = ""
            elif race_add_on == "":
                add_on = add_on
            else:
                await ctx.send("**Juvenile females are not yet supported.**\n*Overriding race options...*")

            if database.hget(f"race.data:{ctx.channel.id}", "bw").decode("utf-8"):
                bw = not bw

            taxon = database.hget(f"race.data:{ctx.channel.id}", "taxon").decode("utf-8")
            state = database.hget(f"race.data:{ctx.channel.id}", "state").decode("utf-8")

        logger.info(f"args: bw: {bw}; addon: {add_on}; taxon: {taxon}; state: {state}")

        await self.send_bird_(ctx, add_on, bw, taxon, state)

    # goatsucker command - no args
    # just for fun, no real purpose
    @commands.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def goatsucker(self, ctx):
        logger.info("command: goatsucker")

        await channel_setup(ctx)
        await user_setup(ctx)

        answered = int(database.hget(f"channel:{ctx.channel.id}", "gsAnswered"))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            if database.exists(f"session.data:{ctx.author.id}"):
                logger.info("session active")
                session_increment(ctx, "total", 1)

            database.hset(f"channel:{ctx.channel.id}", "gsAnswered", "0")
            currentBird = random.choice(goatsuckers)
            database.hset(f"channel:{ctx.channel.id}", "goatsucker", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(ctx, currentBird, on_error=error_skip_goat, message=GS_MESSAGE)
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "goatsucker").decode("utf-8"),
                on_error=error_skip_goat,
                message=GS_MESSAGE
            )

    # picks a random bird call to send
    @commands.command(help="- Sends a bird call to ID", aliases=["s"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def song(self, ctx):
        logger.info("command: song")

        await channel_setup(ctx)
        await user_setup(ctx)

        logger.info("bird: " + database.hget(f"channel:{ctx.channel.id}", "sBird").decode("utf-8"))
        logger.info("answered: " + str(int(database.hget(f"channel:{ctx.channel.id}", "sAnswered"))))

        await self.send_song_(ctx)

def setup(bot):
    bot.add_cog(Birds(bot))
