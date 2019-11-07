# sessions.py | commands for sessions
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

import datetime
import time
import discord

from discord.ext import commands

from data.data import database, logger, states
from functions import channel_setup, user_setup, check_state_role

class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_options(self, ctx):
        bw, addon, state = database.hmget(f"session.data:{str(ctx.author.id)}",
                                                        ["bw", "addon", "state"])
        options = str(
            f"**Age/Sex:** {str(addon)[2:-1] if addon else 'default'}\n" +
            f"**Black & White:** {bw==b'bw'}\n" +
            f"**Special bird list:** {str(state)[2:-1] if state else 'None'}\n"
        )
        return options

    async def _get_stats(self, ctx):
        start, correct, incorrect, total = map(
            int, database.hmget(f"session.data:{str(ctx.author.id)}", ["start", "correct", "incorrect", "total"]))
        elapsed = str(datetime.timedelta(seconds=round(time.time()) - start))
        try:
            accuracy = round(100 * (correct / (correct + incorrect)), 2)
        except ZeroDivisionError:
            accuracy = 0

        stats = str(
            f"**Duration:** `{elapsed}`\n" +
            f"**# Correct:** {correct}\n" +
            f"**# Incorrect:** {incorrect}\n" +
            f"**Total Birds:** {total}\n" +
            f"**Accuracy:** {accuracy}%\n"
        )
        return stats

    async def _send_stats(self, ctx, preamble):
        database_key = f"session.incorrect:{str(ctx.author.id)}"

        embed = discord.Embed(type="rich", colour=discord.Color.blurple(), title=preamble)
        embed.set_author(name="Bird ID - An Ornithology Bot")

        if database.zcard(database_key) is not 0:
            leaderboard_list = database.zrevrangebyscore(
                database_key, "+inf", "-inf", 0, 5, True)
            leaderboard = ""

            for i, stats in enumerate(leaderboard_list):
                leaderboard += f"{str(i+1)}. **{str(stats[0])[2:-1]}** - {str(int(stats[1]))}\n"
        else:
            logger.info(f"no birds in {database_key}")
            leaderboard = "**There are no missed birds.**"

        embed.add_field(name="Options", value=await self._get_options(ctx), inline=False)
        embed.add_field(name="Stats", value=await self._get_stats(ctx), inline=False)
        embed.add_field(name=f"Top Missed Birds", value=leaderboard, inline=False)

        await ctx.send(embed=embed)

    @commands.group(brief="- Base session command",
                    help="- Base session command\n" +
                         "Sessions will record your activity for an amount of time and " +
                         "will give you stats on how your performance and " +
                         "also set global variables such as black and white, " +
                         "state specific bird lists, or bird age/sex. ",
                    aliases=["ses", "sesh"])
    async def session(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid subcommand passed.**\n*Valid Subcommands:* `start, view, stop`')

    # starts session
    @session.command(
        brief="- Starts session",
        help="""- Starts session.
        Arguments passed will become the default arguments to 'b!bird', but can be manually overwritten during use. 
        These settings can be changed at any time with 'b!session edit', and arguments can be passed in any order. 
        However, having both females and juveniles are not supported.""",
        aliases=["st"],
        usage="[bw] [state] [female|juvenile]"
    )
    @commands.cooldown(1, 3.0, type=commands.BucketType.user)
    async def start(self, ctx, *, args_str: str = ""):
        logger.info("command: start session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            logger.info("already session")
            await ctx.send("**There is already a session running.** *Change settings/view stats with `b!session edit`*")
            return
        else:
            args = args_str.split(" ")
            logger.info(f"args: {args}")
            if "bw" in args:
                bw = "bw"
            else:
                bw = ""
            states_args = set(states.keys()).intersection({arg.upper() for arg in args})
            if states_args:
                state = " ".join(states_args).strip()
            else:
                state = " ".join(check_state_role(ctx))
            female = "female" in args or "f" in args
            juvenile = "juvenile" in args or "j" in args
            if female and juvenile:
                await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
                return
            elif female:
                addon = "female"
            elif juvenile:
                addon = "juvenile"
            else:
                addon = ""
            logger.info(f"adding bw: {bw}; addon: {addon}; state: {state}")

            database.hmset(
                f"session.data:{str(ctx.author.id)}", {
                    "start": round(time.time()),
                    "stop": 0,
                    "correct": 0,
                    "incorrect": 0,
                    "total": 0,
                    "bw": bw,
                    "state": state,
                    "addon": addon
                }
            )
            await ctx.send(f"**Session started with options:**\n{await self._get_options(ctx)}")
    # views session
    @session.command(
        brief="- Views session",
        help="- Views session\nSessions will record your activity for an amount of time and " +
        "will give you stats on how your performance and also set global variables such as black and white, " +
        "state specific bird lists, or bird age/sex. ",
        aliases=["view"],
        usage="[bw] [state] [female|juvenile]"
    )
    @commands.cooldown(1, 3.0, type=commands.BucketType.user)
    async def edit(self, ctx, *, args_str: str = ""):
        logger.info("command: view session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            args = args_str.split(" ")
            logger.info(f"args: {args}")
            if "bw" in args:
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "bw")) is 0:
                    logger.info("adding bw")
                    database.hset(f"session.data:{str(ctx.author.id)}", "bw", "bw")
                else:
                    logger.info("removing bw")
                    database.hset(f"session.data:{str(ctx.author.id)}", "bw", "")
            states_args = set(states.keys()).intersection({arg.upper() for arg in args})
            if states_args:
                toggle_states = list(states_args)
                current_states = str(database.hget(f"session.data:{str(ctx.author.id)}", "state"))[2:-1].split(" ")
                add_states = []
                logger.info(f"toggle states: {toggle_states}")
                logger.info(f"current states: {current_states}")
                for state in set(toggle_states).symmetric_difference(set(current_states)):
                    add_states.append(state)
                logger.info(f"adding states: {add_states}")
                database.hset(f"session.data:{str(ctx.author.id)}", "state", " ".join(add_states).strip())
            female = "female" in args or "f" in args
            juvenile = "juvenile" in args or "j" in args
            if female and juvenile:
                await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
                return
            elif female:
                addon = "female"
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "addon")) is 0:
                    logger.info("adding female")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", addon)
                else:
                    logger.info("removing female")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", "")
            elif juvenile:
                addon = "juvenile"
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "addon")) is 0:
                    logger.info("adding juvenile")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", addon)
                else:
                    logger.info("removing juvenile")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", "")
            await self._send_stats(ctx, f"**Session started previously with options:**\n")
        else:
            await ctx.send("**There is no session running.** *You can start one with `b!session start`*")

    # stops session
    @session.command(help="- Stops session", aliases=["stp"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.user)
    async def stop(self, ctx):
        logger.info("command: stop session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            database.hset(f"session.data:{str(ctx.author.id)}", "stop", round(time.time()))

            await self._send_stats(ctx, "**Session stopped.**\n**Session Options:**\n")
            database.delete(f"session.data:{str(ctx.author.id)}")
            database.delete(f"session.incorrect:{str(ctx.author.id)}")
        else:
            await ctx.send("**There is no session running.** *You can start one with `b!session start`*")

def setup(bot):
    bot.add_cog(Sessions(bot))
