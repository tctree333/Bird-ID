# sessions.py | commands for sessions
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

import datetime
import textwrap
import time

import discord
from discord.ext import commands

from bot.data import database, logger, states, taxons
from bot.filters import Filter
from bot.functions import CustomCooldown, check_state_role


class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_options(self, ctx):
        filter_int, state, taxon, wiki, strict = database.hmget(
            f"session.data:{ctx.author.id}",
            ["filter", "state", "taxon", "wiki", "strict"],
        )
        filters = Filter().from_int(int(filter_int))
        options = textwrap.dedent(
            f"""\
            **Active Filters:** `{'`, `'.join(filters.display())}`
            **State bird list:** {state.decode('utf-8') if state else 'None'}
            **Bird taxon:** {taxon.decode('utf-8') if taxon else 'None'}
            **Wiki Embeds**: {wiki==b'wiki'}
            **Strict Spelling**: {strict==b'strict'}
            """
        )
        return options

    async def _get_stats(self, ctx):
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

    async def _send_stats(self, ctx, preamble):
        database_key = f"session.incorrect:{ctx.author.id}"

        embed = discord.Embed(
            type="rich", colour=discord.Color.blurple(), title=preamble
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")

        if database.zcard(database_key) != 0:
            leaderboard_list = database.zrevrangebyscore(
                database_key, "+inf", "-inf", 0, 5, True
            )
            leaderboard = ""

            for i, stats in enumerate(leaderboard_list):
                leaderboard += (
                    f"{i+1}. **{stats[0].decode('utf-8')}** - {int(stats[1])}\n"
                )
        else:
            logger.info(f"no birds in {database_key}")
            leaderboard = "**There are no missed birds.**"

        embed.add_field(
            name="Options", value=await self._get_options(ctx), inline=False
        )
        embed.add_field(name="Stats", value=await self._get_stats(ctx), inline=False)
        embed.add_field(name=f"Top Missed Birds", value=leaderboard, inline=False)

        await ctx.send(embed=embed)

    @commands.group(
        brief="- Base session command",
        help="- Base session command\n"
        + "Sessions will record your activity for an amount of time and "
        + "will give you stats on how your performance and "
        + "also set global variables such as black and white, "
        + "state specific bird lists, specific bird taxons, or bird age/sex. ",
        aliases=["ses", "sesh"],
    )
    async def session(self, ctx):
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
    async def start(self, ctx, *, args_str: str = ""):
        logger.info("command: start session")

        if database.exists(f"session.data:{ctx.author.id}"):
            logger.info("already session")
            await ctx.send(
                "**There is already a session running.** *Change settings/view stats with `b!session edit`*"
            )
            return
        else:
            filters = Filter().parse(args_str)

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
    async def edit(self, ctx, *, args_str: str = ""):
        logger.info("command: view session")

        if database.exists(f"session.data:{ctx.author.id}"):
            new_filter = Filter().parse(args_str, defaults=False)

            args = args_str.lower().split(" ")
            logger.info(f"args: {args}")

            new_filter.xor(
                int(database.hget(f"session.data:{ctx.author.id}", "filter"))
            )
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
                toggle_states = list(states_args)
                current_states = (
                    database.hget(f"session.data:{ctx.author.id}", "state")
                    .decode("utf-8")
                    .split(" ")
                )
                add_states = []
                logger.info(f"toggle states: {toggle_states}")
                logger.info(f"current states: {current_states}")
                for state in set(toggle_states).symmetric_difference(
                    set(current_states)
                ):
                    add_states.append(state)
                logger.info(f"adding states: {add_states}")
                database.hset(
                    f"session.data:{ctx.author.id}",
                    "state",
                    " ".join(add_states).strip(),
                )

            taxon_args = set(taxons.keys()).intersection({arg.lower() for arg in args})
            if taxon_args:
                toggle_taxon = list(taxon_args)
                current_taxons = (
                    database.hget(f"session.data:{ctx.author.id}", "taxon")
                    .decode("utf-8")
                    .split(" ")
                )
                add_taxons = []
                logger.info(f"toggle taxons: {toggle_taxon}")
                logger.info(f"current taxons: {current_taxons}")
                for o in set(toggle_taxon).symmetric_difference(set(current_taxons)):
                    add_taxons.append(o)
                logger.info(f"adding taxons: {add_taxons}")
                database.hset(
                    f"session.data:{ctx.author.id}",
                    "taxon",
                    " ".join(add_taxons).strip(),
                )

            await self._send_stats(ctx, f"**Session started previously.**\n")
        else:
            await ctx.send(
                "**There is no session running.** *You can start one with `b!session start`*"
            )

    # stops session
    @session.command(help="- Stops session", aliases=["stp", "end"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.user))
    async def stop(self, ctx):
        logger.info("command: stop session")

        if database.exists(f"session.data:{ctx.author.id}"):
            database.hset(f"session.data:{ctx.author.id}", "stop", round(time.time()))

            await self._send_stats(ctx, "**Session stopped.**\n")
            database.delete(f"session.data:{ctx.author.id}")
            database.delete(f"session.incorrect:{ctx.author.id}")
        else:
            await ctx.send(
                "**There is no session running.** *You can start one with `b!session start`*"
            )


def setup(bot):
    bot.add_cog(Sessions(bot))
