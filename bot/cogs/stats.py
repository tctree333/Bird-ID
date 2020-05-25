# stats.py | commands for bot statistics
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

import discord
import pandas as pd
from discord.ext import commands

from bot.data import GenericError, database, logger
from bot.functions import CustomCooldown, send_leaderboard


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # give frequency stats
    @commands.command(help="- Gives info on command/bird frequencies", aliases=["freq"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def frequency(self, ctx, scope="", page=1):
        logger.info("command: frequency")

        if scope in ("command", "commands", "c"):
            database_key = "frequency.command:global"
            title = "Most Frequently Used Commands"
        elif scope in ("bird", "birds", "b"):
            database_key = "frequency.bird:global"
            title = "Most Frequent Birds"
        else:
            await ctx.send("**Invalid Scope!**\n*Valid Scopes:* `commands, birds`")
            return

        await send_leaderboard(ctx, title, page, database_key)

    # export data as csv
    @commands.command(help="- Exports bot data as a csv")
    @commands.check(CustomCooldown(10.0, bucket=commands.BucketType.channel))
    async def export(self, ctx):
        logger.info("command: export")

        



def setup(bot):
    bot.add_cog(Stats(bot))
