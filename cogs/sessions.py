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

from functions import channel_setup, user_setup
from discord.ext import commands
from data.data import database, logger, states
import typing
import time
import datetime

class Sessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # starts session
    @commands.command(brief="- Starts session", help="- Starts session.\n" +
                      "Arguments passed will become the default arguments to b!bird, " +
                      "but can be manually overwritten during use. " +
                      "These settings can be changed at any time with b!session, " +
                      "and arguments can be passed in any order. " +
                      "However, having both females and juveniles are not supported.",
                      aliases=["st"], usage="[bw] [state] [female|juvenile]")
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def start(self, ctx, *, args: typing.Optional[str] = ""):
        logger.info("start session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            logger.info("already session")
            await ctx.send("**There is already a session running.** *Change settings/view stats with `b!session`*")
            return
        else:
            args = args.split(" ")
            logger.info(f"args: {args}")
            bw = ""
            state = ""
            addon = ""
            if "bw" in args:
                bw = "bw"
            if len(set(states.keys()).intersection(set([arg.upper() for arg in args]))) is not 0:
                state = " ".join(set(states.keys()).intersection(set([arg.upper() for arg in args]))).strip()
            if "female" in args and "juvenile" in args:
                await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
                return
            elif "female" in args:
                addon = "female"
            elif "juvenile" in args:
                addon = "juvenile"

            logger.info(f"adding bw: {bw}; addon: {addon}; state: {state}")

            database.hmset(f"session.data:{str(ctx.author.id)}",
                           {"start": round(time.time()), "stop": 0,
                            "correct": 0, "incorrect": 0, "total": 0,
                            "bw": bw, "state": state.strip(), "addon": addon})

            await ctx.send(f"**Session started with options:**\n" +
                           f"*Age/Sex:* {addon if len(addon) is not 0 else 'default'}\n" +
                           f"*Black & White:* {'True' if len(bw) is not 0 else 'False'}\n" +
                           f"*Special bird list:* {state if len(state) is not 0 else 'None'}")


    # views session
    @commands.command(brief="- Views session", help="- Views session\n" +
                      "Sessions will record your activity for an amount of time and " +
                      "will give you stats on how your performance " +
                      "and also set global variables such as black and white, " +
                      "state specific bird lists, or bird age/sex. ",
                      aliases=["ses", "sesh"], usage="[bw] [state] [female|juvenile]")
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def session(self, ctx, *, args: typing.Optional[str] = ""):
        logger.info("view session")
        logger.info(f"args: {args}")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            args = args.split(" ")
            bw = ""
            state = ""
            addon = ""
            if "bw" in args:
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "bw")) is 0:
                    logger.info("adding bw")
                    database.hset(f"session.data:{str(ctx.author.id)}", "bw", "bw")
                else:
                    logger.info("removing bw")
                    database.hset(f"session.data:{str(ctx.author.id)}", "bw", "")

            if len(set(states.keys()).intersection(set([arg.upper() for arg in args]))) is not 0:
                toggle_states = list(set(states.keys()).intersection(set([arg.upper() for arg in args])))
                current_states = str(database.hget(f"session.data:{str(ctx.author.id)}", "state"))[2:-1].split(" ")
                add_states = []
                logger.info(f"toggle states: {toggle_states}")
                logger.info(f"current states: {current_states}")
                for state in set(toggle_states).symmetric_difference(set(current_states)):
                    add_states.append(state)
                logger.info(f"adding states: {add_states}")
                database.hset(f"session.data:{str(ctx.author.id)}", "state", " ".join(add_states).strip())

            if "female" in args and "juvenile" in args:
                await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
                return
            elif "female" in args:
                addon = "female"
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "addon")) is 0:
                    logger.info("adding female")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", addon)
                else:
                    logger.info("removing female")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", "")
            elif "juvenile" in args:
                addon = "juvenile"
                if len(database.hget(f"session.data:{str(ctx.author.id)}", "addon")) is 0:
                    logger.info("adding juvenile")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", addon)
                else:
                    logger.info("removing juvenile")
                    database.hset(f"session.data:{str(ctx.author.id)}", "addon", "")

            start, correct, incorrect, total = database.hmget(
                f"session.data:{str(ctx.author.id)}",
                ["start", "correct", "incorrect", "total"])

            bw, addon, state = database.hmget(
                f"session.data:{str(ctx.author.id)}",
                ["bw", "addon", "state"])

            elapsed = str(datetime.timedelta(seconds=int(round(time.time()))-int(start)))

            await ctx.send(f"**Session started {elapsed} ago with options:**\n" +
                           f"*Age/Sex:* {str(addon)[2:-1] if len(addon) is not 0 else 'default'}\n" +
                           f"*Black & White:* {'True' if len(bw) is not 0 else 'False'}\n" +
                           f"*Special bird list:* {str(state)[2:-1] if len(state) is not 0 else 'None'}")

            await ctx.send(f"**Session Stats:**\n" +
                           f"*# Correct:* {int(correct)}\n" +
                           f"*# Incorrect* {int(incorrect)}\n" +
                           f"*Accuracy* {0 if int(total) is 0 else 100*(int(correct)/int(total))}%")
        else:
            await ctx.send("**There is no session running.** *You can start one with `b!start`*")


    # stops session
    @commands.command(help="- Stops session",
                      aliases=["sp", "stp"])
    @commands.cooldown(1, 3.0, type=commands.BucketType.channel)
    async def stop(self, ctx):
        logger.info("stop session")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"session.data:{str(ctx.author.id)}"):
            database.hset(f"session.data:{str(ctx.author.id)}", "stop", round(time.time()))

            start, stop, correct, incorrect, total = database.hmget(
                f"session.data:{str(ctx.author.id)}",
                ["start", "stop", "correct", "incorrect", "total"])

            bw, addon, state = database.hmget(
                f"session.data:{str(ctx.author.id)}",
                ["bw", "addon", "state"])

            elapsed = str(datetime.timedelta(seconds=int(stop)-int(start)))

            database.delete(f"session.data:{str(ctx.author.id)}")

            await ctx.send(f"**Session stopped.**\n**Session Options:**\n" +
                           f"*Age/Sex:* {str(addon)[2:-1] if len(addon) is not 0 else 'default'}\n" +
                           f"*Black & White:* {'True' if len(bw) is not 0 else 'False'}\n" +
                           f"*Special bird list:* {str(state)[2:-1] if len(state) is not 0 else 'None'}")

            await ctx.send(f"**Session Stats:**\n" +
                           f"*Duration:* {elapsed}\n" +
                           f"*# Correct:* {int(correct)}\n" +
                           f"*# Incorrect* {int(incorrect)}\n" +
                           f"*Total Birds:* {int(total)}\n" +
                           f"*Accuracy* {0 if int(total) is 0 else 100*(int(correct)/int(total))}%")
        else:
            await ctx.send("**There is no session running.** *You can start one with `b!start`*")


def setup(bot):
    bot.add_cog(Sessions(bot))
