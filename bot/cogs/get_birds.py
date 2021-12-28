# get_birds.py | commands for getting bird images or songs
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

import random
import string
from typing import Optional

from discord.ext import commands

import bot.voice as voice_functions
from bot.core import send_bird
from bot.data import GenericError, database, goatsuckers, logger, states, taxons
from bot.data_functions import bird_setup, session_increment
from bot.filters import Filter
from bot.functions import CustomCooldown, build_id_list, check_state_role

BASE_MESSAGE = (
    "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, "
    + "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. "
    + "Use `b!{hint_cmd}` for a hint.**"
)

BIRD_MESSAGE = BASE_MESSAGE.format(
    media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint"
)
GS_MESSAGE = BASE_MESSAGE.format(
    media="image",
    new_cmd="gs",
    skip_cmd="skip",
    check_cmd="check",
    hint_cmd="hint",
)
SONG_MESSAGE = BASE_MESSAGE.format(
    media="song",
    new_cmd="song",
    skip_cmd="skip",
    check_cmd="check",
    hint_cmd="hint",
)


class Birds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_next_race_media(self, ctx):
        if database.exists(f"race.data:{ctx.channel.id}"):
            if Filter.from_int(
                int(database.hget(f"race.data:{ctx.channel.id}", "filter"))
            ).vc:
                await voice_functions.stop(ctx, silent=True)

            media = database.hget(f"race.data:{ctx.channel.id}", "media").decode(
                "utf-8"
            )

            logger.info(f"auto sending next bird {media}")
            filter_int, taxon, state = database.hmget(
                f"race.data:{ctx.channel.id}", ["filter", "taxon", "state"]
            )

            await self.send_bird_(
                ctx,
                media,
                Filter.from_int(int(filter_int)),
                taxon.decode("utf-8"),
                state.decode("utf-8"),
            )

    def error_handle(
        self,
        ctx,
        media_type: str,
        filters: Filter,
        taxon_str,
        role_str,
        retries,
    ):
        """Return a function to pass to send_bird() as on_error."""
        # pylint: disable=unused-argument

        async def inner(error):
            nonlocal retries

            # skip current bird
            database.hset(f"channel:{ctx.channel.id}", "bird", "")
            database.hset(f"channel:{ctx.channel.id}", "answered", "1")

            if retries >= 2:  # only retry twice
                await ctx.send("**Too many retries.**\n*Please try again.*")
                await self._send_next_race_media(ctx)
                return

            if isinstance(error, GenericError) and error.code == 100:
                retries += 1
                await ctx.send("**Retrying...**")
                await self.send_bird_(
                    ctx, media_type, filters, taxon_str, role_str, retries
                )
            else:
                await ctx.send("*Please try again.*")
                await self._send_next_race_media(ctx)

        return inner

    @staticmethod
    def error_skip(ctx):
        async def inner(error):
            # pylint: disable=unused-argument

            # skip current bird
            database.hset(f"channel:{ctx.channel.id}", "bird", "")
            database.hset(f"channel:{ctx.channel.id}", "answered", "1")
            await ctx.send("*Please try again.*")

        return inner

    @staticmethod
    def increment_bird_frequency(ctx, bird):
        bird_setup(ctx, bird)
        database.zincrby("frequency.bird:global", 1, string.capwords(bird))

    async def send_bird_(
        self,
        ctx,
        media_type: Optional[str],
        filters: Filter,
        taxon_str: str = "",
        role_str: str = "",
        retries=0,
    ):
        media_type = (
            "images"
            if media_type in ("images", "image", "i", "p")
            else ("songs" if media_type in ("songs", "song", "s", "a") else None)
        )
        if not media_type:
            raise GenericError("Invalid media type", code=990)

        if media_type == "songs" and filters.vc:
            current_voice = database.get(f"voice.server:{ctx.guild.id}")
            if current_voice is not None and current_voice.decode("utf-8") != str(
                ctx.channel.id
            ):
                logger.info("already vc race")
                await ctx.send("**The voice channel is currently in use!**")
                return

        if taxon_str:
            taxon = taxon_str.split(" ")
        else:
            taxon = []

        if role_str:
            roles = role_str.split(" ")
        else:
            roles = []

        logger.info(
            "bird: "
            + database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8")
        )

        currently_in_race = bool(database.exists(f"race.data:{ctx.channel.id}"))

        answered = int(database.hget(f"channel:{ctx.channel.id}", "answered"))
        logger.info(f"answered: {answered}")
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            session_increment(ctx, "total", 1)

            logger.info(f"filters: {filters}; taxon: {taxon}; roles: {roles}")

            if not currently_in_race and retries == 0:
                await ctx.send(
                    "**Recognized arguments:** "
                    + f"*Active Filters*: `{'`, `'.join(filters.display())}`, "
                    + f"*Taxons*: `{'None' if taxon_str == '' else taxon_str}`, "
                    + f"*Detected State*: `{'None' if role_str == '' else role_str}`"
                )

            find_custom_role = {i if i.startswith("CUSTOM:") else "" for i in roles}
            find_custom_role.discard("")
            if (
                database.exists(f"race.data:{ctx.channel.id}")
                and len(find_custom_role) == 1
            ):
                custom_role = find_custom_role.pop()
                roles.remove(custom_role)
                roles.append("CUSTOM")
                user_id = custom_role.split(":")[1]
                birds = build_id_list(
                    user_id=user_id, taxon=taxon, state=roles, media=media_type
                )
            else:
                birds = build_id_list(
                    user_id=ctx.author.id, taxon=taxon, state=roles, media=media_type
                )

            if not birds:
                logger.info("no birds for taxon/state")
                await ctx.send(
                    "**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*"
                )
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
            await send_bird(
                ctx,
                currentBird,
                media_type,
                filters,
                on_error=self.error_handle(
                    ctx, media_type, filters, taxon_str, role_str, retries
                ),
                message=(SONG_MESSAGE if media_type == "songs" else BIRD_MESSAGE)
                if not currently_in_race
                else "*Here you go!*",
            )
        else:  # if no, give the same bird
            await ctx.send(f"**Active Filters**: `{'`, `'.join(filters.display())}`")
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"),
                media_type,
                filters,
                on_error=self.error_handle(
                    ctx, media_type, filters, taxon_str, role_str, retries
                ),
                message=(SONG_MESSAGE if media_type == "songs" else BIRD_MESSAGE)
                if not currently_in_race
                else "*Here you go!*",
            )

    @staticmethod
    async def parse(ctx, args_str: str):
        """Parse arguments for options."""

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
                    current_taxons = set(
                        database.hget(f"session.data:{ctx.author.id}", "taxon")
                        .decode("utf-8")
                        .split(" ")
                    )
                    logger.info(f"toggle taxons: {taxon_args}")
                    logger.info(f"current taxons: {current_taxons}")
                    taxon_args.symmetric_difference_update(current_taxons)
                    taxon_args.discard("")
                    logger.info(f"new taxons: {taxon_args}")
                    taxon = " ".join(taxon_args).strip()
                else:
                    taxon = database.hget(
                        f"session.data:{ctx.author.id}", "taxon"
                    ).decode("utf-8")

                roles = (
                    database.hget(f"session.data:{ctx.author.id}", "state")
                    .decode("utf-8")
                    .split(" ")
                )
                if roles[0] == "":
                    roles = []
                if not roles:
                    logger.info("no session lists")
                    roles = check_state_role(ctx)

                session_filter = int(
                    database.hget(f"session.data:{ctx.author.id}", "filter")
                )
                filters = Filter.parse(args_str, defaults=False)
                if filters.vc:
                    filters.vc = False
                    await ctx.send("**The VC filter is not allowed inline!**")

                default_quality = Filter().quality
                if (
                    Filter.from_int(session_filter).quality == default_quality
                    and filters.quality
                    and filters.quality != default_quality
                ):
                    filters ^= Filter()  # clear defaults
                filters ^= session_filter
            else:
                filters = Filter.parse(args_str)
                if filters.vc:
                    filters.vc = False
                    await ctx.send("**The VC filter is not allowed inline!**")

            if state_args:
                logger.info(f"toggle states: {state_args}")
                logger.info(f"current states: {roles}")
                state_args.symmetric_difference_update(set(roles))
                state_args.discard("")
                logger.info(f"new states: {state_args}")
                state = " ".join(state_args).strip()
            else:
                state = " ".join(roles).strip()

            if "CUSTOM" in state.upper().split(" "):
                if not database.exists(f"custom.list:{ctx.author.id}"):
                    await ctx.send("**You don't have a custom list set!**")
                    state_list = state.split(" ")
                    state_list.remove("CUSTOM")
                    state = " ".join(state_list)
                elif database.exists(f"custom.confirm:{ctx.author.id}"):
                    await ctx.send(
                        "**Please verify or confirm your custom list before using!**"
                    )
                    state_list = state.split(" ")
                    state_list.remove("CUSTOM")
                    state = " ".join(state_list)

        else:
            logger.info("race parameters")

            race_filter = int(database.hget(f"race.data:{ctx.channel.id}", "filter"))
            filters = Filter.parse(args_str, defaults=False)
            if filters.vc:
                filters.vc = False
                await ctx.send("**The VC filter is not allowed inline!**")

            default_quality = Filter().quality
            if (
                Filter.from_int(race_filter).quality == default_quality
                and filters.quality
                and filters.quality != default_quality
            ):
                filters ^= Filter()  # clear defaults
            filters ^= race_filter

            taxon = database.hget(f"race.data:{ctx.channel.id}", "taxon").decode(
                "utf-8"
            )
            state = database.hget(f"race.data:{ctx.channel.id}", "state").decode(
                "utf-8"
            )

        logger.info(f"args: filters: {filters}; taxon: {taxon}; state: {state}")

        return (filters, taxon, state)

    # Bird command - no args
    # help text
    @commands.command(
        help="- Sends a random bird image for you to ID",
        aliases=["b"],
        usage="[filters] [order/family] [state]",
    )
    # 5 second cooldown
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def bird(self, ctx, *, args_str: str = ""):
        logger.info("command: bird")

        filters, taxon, state = await self.parse(ctx, args_str)
        media = "images"
        if database.exists(f"race.data:{ctx.channel.id}"):
            media = database.hget(f"race.data:{ctx.channel.id}", "media").decode(
                "utf-8"
            )
        await self.send_bird_(ctx, media, filters, taxon, state)

    # picks a random bird call to send
    @commands.command(
        help="- Sends a random bird song for you to ID",
        aliases=["s"],
        usage="[filters] [order/family] [state]",
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def song(self, ctx, *, args_str: str = ""):
        logger.info("command: song")

        filters, taxon, state = await self.parse(ctx, args_str)
        media = "songs"
        if database.exists(f"race.data:{ctx.channel.id}"):
            media = database.hget(f"race.data:{ctx.channel.id}", "media").decode(
                "utf-8"
            )
        await self.send_bird_(ctx, media, filters, taxon, state)

    # goatsucker command - no args
    # just for fun, no real purpose
    @commands.command(help="- Sends a random goatsucker to ID", aliases=["gs"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def goatsucker(self, ctx):
        logger.info("command: goatsucker")

        if database.exists(f"race.data:{ctx.channel.id}"):
            await ctx.send("This command is disabled during races.")
            return

        answered = int(database.hget(f"channel:{ctx.channel.id}", "answered"))
        # check to see if previous bird was answered
        if answered:  # if yes, give a new bird
            session_increment(ctx, "total", 1)

            database.hset(f"channel:{ctx.channel.id}", "answered", "0")
            currentBird = random.choice(goatsuckers)
            self.increment_bird_frequency(ctx, currentBird)

            database.hset(f"channel:{ctx.channel.id}", "bird", str(currentBird))
            logger.info("currentBird: " + str(currentBird))
            await send_bird(
                ctx,
                currentBird,
                "images",
                Filter(),
                on_error=self.error_skip(ctx),
                message=GS_MESSAGE,
            )
        else:  # if no, give the same bird
            await send_bird(
                ctx,
                database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8"),
                "images",
                Filter(),
                on_error=self.error_skip(ctx),
                message=GS_MESSAGE,
            )


def setup(bot):
    bot.add_cog(Birds(bot))
