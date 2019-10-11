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

from discord.ext import commands

from data.data import database, logger, states
from functions import channel_setup, user_setup, check_state_role

class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _send_options(self, ctx, preamble):
        bw, addon, state = database.hmget(f"session.data:{str(ctx.author.id)}", ["bw", "addon", "state"])
        print(bw)
        await ctx.send(
            preamble + f"""*Age/Sex:* {str(addon)[2:-1] if addon else 'default'}
*Black & White:* {bw==b'bw'}
*Special bird list:* {str(state)[2:-1] if state else 'None'}"""
        )

    async def _send_stats(self, ctx, opts_preamble):
        start, correct, incorrect, total = map(
            int, database.hmget(f"session.data:{str(ctx.author.id)}", ["start", "correct", "incorrect", "total"])
        )
        elapsed = str(datetime.timedelta(seconds=round(time.time()) - start))
        try:
            accuracy = round(100 * (correct / (correct + incorrect)), 2)
        except ZeroDivisionError:
            accuracy = 0

        await self._send_options(ctx, opts_preamble)
        await ctx.send(
            f"""**Session Stats:**
*Duration:* {elapsed}
*# Correct:* {correct}
*# Incorrect:* {incorrect}
*Total Birds:* {total}
*Accuracy:* {accuracy}%"""
        )

    # starts session
    @commands.command(
        brief="- Starts session",
        help="""- Starts session.
        Arguments passed will become the default arguments to b!bird, but can be manually overwritten during use. 
        These settings can be changed at any time with b!session, and arguments can be passed in any order. 
        However, having both females and juveniles are not supported.""",
        aliases=["st"],
        usage="[bw] [state] [female|juvenile]"
    )
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def start(self, ctx, *, args_str: str = ""):
        logger.info("start session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            logger.info("already session")
            await ctx.send("**There is already a session running.** *Change settings/view stats with `b!session`*")
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
            await self._send_options(ctx, "**Session started with options:**\n")

    # views session
    @commands.command(
        brief="- Views session",
        help="- Views session\nSessions will record your activity for an amount of time and " +
        "will give you stats on how your performance and also set global variables such as black and white, " +
        "state specific bird lists, or bird age/sex. ",
        aliases=["ses", "sesh"],
        usage="[bw] [state] [female|juvenile]"
    )
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def session(self, ctx, *, args_str: str = ""):
        logger.info("view session")

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
            await ctx.send("**There is no session running.** *You can start one with `b!start`*")

    # stops session
    @commands.command(help="- Stops session", aliases=["sp", "stp"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def stop(self, ctx):
        logger.info("stop session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            database.hset(f"session.data:{str(ctx.author.id)}", "stop", round(time.time()))

            await self._send_stats(ctx, "**Session stopped.**\n**Session Options:**\n")
            database.delete(f"session.data:{str(ctx.author.id)}")
        else:
            await ctx.send("**There is no session running.** *You can start one with `b!start`*")

def setup(bot):
    bot.add_cog(Sessions(bot))
