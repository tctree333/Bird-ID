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
from discord.ext import commands

from bot.data import GenericError, database, logger
from bot.functions import CustomCooldown


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_leaderboard(self, ctx, title, page, database_key=None, data=None):
        logger.info("building/sending leaderboard")
        
        if database_key is None and data is None:
            raise GenericError("database_key and data are both NoneType", 990)
        elif database_key is not None and data is not None:
            raise GenericError("database_key and data are both set", 990)

        entry_count = (int(database.zcard(database_key)) if database_key is not None else data.count())
        page = (page * 10) - 10

        if entry_count == 0:
            logger.info(f"no items in {database_key}")
            await ctx.send("There are no items in the database.")
            return

        if page > entry_count:
            page = entry_count - (entry_count % 10)

        items_per_page = 10
        leaderboard_list = (
            map(
                lambda x: (x[0].decode("utf-8"), x[1]), 
                database.zrevrangebyscore(database_key, "+inf", "-inf", page, items_per_page, True)
            )
            if database_key is not None
            else data.iloc[page:page+items_per_page-1].items()
        )
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        leaderboard = ""

        for i, stats in enumerate(leaderboard_list):
            leaderboard += f"{i+1+page}. **{stats[0]}** - {int(stats[1])}\n"
        embed.add_field(name=title, value=leaderboard, inline=False)

        await ctx.send(embed=embed)

    # give hint
    @commands.command(help="- Gives info on command/bird frequencies", aliases=["freq"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
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

        await self.send_leaderboard(ctx, title, page, database_key)


def setup(bot):
    bot.add_cog(Stats(bot))
