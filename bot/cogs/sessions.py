# sessions.py | commands for sessions
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

import datetime
import textwrap
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import database, logger, states, taxons
from bot.filters import Filter, arg_autocomplete
from bot.functions import CustomCooldown, check_state_role


class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_options(self, ctx: commands.Context):
        filter_int, state, taxon, wiki, strict = database.hmget(
            f"session.data:{ctx.author.id}",
            ["filter", "state", "taxon", "wiki", "strict"],
        )
        filters = Filter.from_int(int(filter_int))
        options = textwrap.dedent(
            f"""\
            **Active Filters:** `{'`, `'.join(filters.display())}`
            **Alternate bird list:** {state.decode('utf-8') if state else 'None'}
            **Bird taxon:** {taxon.decode('utf-8') if taxon else 'None'}
            **Wiki Embeds**: {wiki==b'wiki'}
            **Strict Spelling**: {strict==b'strict'}
            """
        )
        return options

    async def _get_stats(self, ctx: commands.Context):
        start, correct, incorrect, total = map(
            int,
            database.hmget(
                f"session.data:{ctx.author.id}",
                ["start", "correct", "incorrect", "total"],
            ),
        )
        elapsed = datetime.timedelta(seconds=round(time.time()) - start)
        try:
            accuracy = round(100 * (correct / (correct + incorrect)), 2)
        except ZeroDivisionError:
            accuracy = 0

        stats = textwrap.dedent(
            f"""\
            **Duration:** `{elapsed}`
            **# Correct:** {correct}
            **# Incorrect:** {incorrect}
            **Total Birds:** {total}
            **Accuracy:** {accuracy}%
            """
        )
        return stats

    async def _send_stats(self, ctx: commands.Context, preamble):
        database_key = f"session.incorrect:{ctx.author.id}"

        embed = discord.Embed(
            type="rich", colour=discord.Color.blurple(), title=preamble
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")

        if database.zcard(database_key) != 0:
            leaderboard_list = database.zrevrangebyscore(
                database_key, "+inf", "-inf", 0, 5, True
            )
            leaderboard = "".join(
                (
                    f"{i+1}. **{stats[0].decode('utf-8')}** - {int(stats[1])}\n"
                    for i, stats in enumerate(leaderboard_list)
                )
            )
        else:
            logger.info(f"no birds in {database_key}")
            leaderboard = "**There are no missed birds.**"

        embed.add_field(
            name="Options", value=await self._get_options(ctx), inline=False
        )
        embed.add_field(name="Stats", value=await self._get_stats(ctx), inline=False)
        embed.add_field(name="Top Missed Birds", value=leaderboard, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_group(
        brief="- Base session command",
        help="- Base session command\n"
        + "Sessions will record your activity for an amount of time and "
        + "will give you stats on how your performance and "
        + "also set global variables such as black and white, "
        + "state specific bird lists, specific bird taxons, or bird age/sex. ",
        aliases=["ses", "sesh"],
    )
    async def session(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "**Invalid subcommand passed.**\n*Valid Subcommands:* `start, view, stop`"
            )

    # starts session
    @session.command(
        brief="- Starts session",
        help="""- Starts session.
        Arguments passed will become the default arguments to 'b!bird', but can be manually overwritten during use. 
        These settings can be changed at any time with 'b!session edit', and arguments can be passed in any order. 
        However, having both females and juveniles are not supported.""",
        aliases=["st"],
        usage="[state] [taxons] [filters]",
    )
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    @app_commands.rename(args_str="options")
    @app_commands.describe(
        args_str="Macaulay Library filters, bird lists, or taxons. Muliple options can be used at once (even if it doesn't autocomplete)"
    )
    @app_commands.autocomplete(args_str=arg_autocomplete)
    async def start(self, ctx: commands.Context, *, args_str: str = ""):
        logger.info("command: start session")

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("already session")
            await ctx.send(
                "**There is already a session running.** *Change settings/view stats with `b!session edit`*"
            )
            return

        filters = Filter.parse(args_str)
        if filters.vc:
            filters.vc = False
            await ctx.send("**The VC filter is not allowed in sessions!**")

        args = args_str.lower().split(" ")
        logger.info(f"args: {args}")

        if "wiki" in args:
            wiki = ""
        else:
            wiki = "wiki"

        if "strict" in args:
            strict = "strict"
        else:
            strict = ""

        states_args = set(states.keys()).intersection({arg.upper() for arg in args})
        if states_args:
            state = " ".join(states_args).strip()
        else:
            state = " ".join(check_state_role(ctx))

        taxon_args = set(taxons.keys()).intersection({arg.lower() for arg in args})
        if taxon_args:
            taxon = " ".join(taxon_args).strip()
        else:
            taxon = ""

        logger.info(
            f"adding filters: {filters}; state: {state}; wiki: {wiki}; strict: {strict}"
        )

        database.hset(
            f"session.data:{ctx.author.id}",
            mapping={
                "start": round(time.time()),
                "stop": 0,
                "correct": 0,
                "incorrect": 0,
                "total": 0,
                "filter": str(filters.to_int()),
                "state": state,
                "taxon": taxon,
                "wiki": wiki,
                "strict": strict,
            },
        )
        await ctx.send(
            f"**Session started with options:**\n{await self._get_options(ctx)}"
        )

        logger.info("session start: skipping bird")
        database.hset(f"channel:{ctx.channel.id}", "bird", "")
        database.hset(f"channel:{ctx.channel.id}", "answered", "1")

    # views session
    @session.command(
        brief="- Views session",
        help="- Views session\nSessions will record your activity for an amount of time and "
        + "will give you stats on how your performance and also set global variables such as black and white, "
        + "state specific bird lists, specific bird taxons, or bird age/sex. ",
        aliases=["view"],
        usage="[state] [taxons] [filters]",
    )
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    @app_commands.rename(args_str="options")
    @app_commands.describe(
        args_str="Macaulay Library filters, bird lists, or taxons. Muliple options can be used at once (even if it doesn't autocomplete)"
    )
    @app_commands.autocomplete(args_str=arg_autocomplete)
    async def edit(self, ctx: commands.Context, *, args_str: str = ""):
        logger.info("command: view session")

        if not database.exists(f"session.data:{ctx.author.id}"):
            await ctx.send(
                "**There is no session running.** *You can start one with `b!session start`*"
            )
            return

        new_filter = Filter.parse(args_str, defaults=False)
        if new_filter.vc:
            new_filter.vc = False
            await ctx.send("**The VC filter is not allowed in sessions!**")

        args = args_str.lower().split(" ")
        logger.info(f"args: {args}")

        new_filter ^= int(database.hget(f"session.data:{ctx.author.id}", "filter"))
        database.hset(
            f"session.data:{ctx.author.id}", "filter", str(new_filter.to_int())
        )

        if "wiki" in args:
            if database.hget(f"session.data:{ctx.author.id}", "wiki"):
                logger.info("enabling wiki embeds")
                database.hset(f"session.data:{ctx.author.id}", "wiki", "")
            else:
                logger.info("disabling wiki embeds")
                database.hset(f"session.data:{ctx.author.id}", "wiki", "wiki")

        if "strict" in args:
            if database.hget(f"session.data:{ctx.author.id}", "strict"):
                logger.info("disabling strict spelling")
                database.hset(f"session.data:{ctx.author.id}", "strict", "")
            else:
                logger.info("enabling strict spelling")
                database.hset(f"session.data:{ctx.author.id}", "strict", "strict")

        states_args = set(states.keys()).intersection({arg.upper() for arg in args})
        if states_args:
            current_states = set(
                database.hget(f"session.data:{ctx.author.id}", "state")
                .decode("utf-8")
                .split(" ")
            )
            logger.info(f"toggle states: {states_args}")
            logger.info(f"current states: {current_states}")
            states_args.symmetric_difference_update(current_states)
            states_args.discard("")
            logger.info(f"new states: {states_args}")
            database.hset(
                f"session.data:{ctx.author.id}",
                "state",
                " ".join(states_args).strip(),
            )

        taxon_args = set(taxons.keys()).intersection({arg.lower() for arg in args})
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
            database.hset(
                f"session.data:{ctx.author.id}",
                "taxon",
                " ".join(taxon_args).strip(),
            )

        await self._send_stats(ctx, "**Session started previously.**\n")

    # stops session
    @session.command(help="- Stops session", aliases=["stp", "end"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    async def stop(self, ctx: commands.Context):
        logger.info("command: stop session")

        if database.exists(f"session.data:{ctx.author.id}"):
            database.hset(f"session.data:{ctx.author.id}", "stop", round(time.time()))

            await self._send_stats(ctx, "**Session stopped.**\n")
            database.delete(f"session.data:{ctx.author.id}")
            database.delete(f"session.incorrect:{ctx.author.id}")

            logger.info("session end: skipping bird")
            database.hset(f"channel:{ctx.channel.id}", "bird", "")
            database.hset(f"channel:{ctx.channel.id}", "answered", "1")
        else:
            await ctx.send(
                "**There is no session running.** *You can start one with `b!session start`*"
            )


async def setup(bot):
    await bot.add_cog(Sessions(bot))
