# hint.py | commands for giving hints
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

from discord.ext import commands

from bot.data import database, logger
from bot.functions import CustomCooldown


class Hint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # give hint
    @commands.hybrid_command(help="- Gives first letter of current bird", aliases=["h"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    async def hint(self, ctx: commands.Context):
        logger.info("command: hint")

        currentBird = database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8")
        if currentBird != "":  # check if there is bird
            await ctx.send(f"The first letter is {currentBird[0]}")
        else:
            await ctx.send("You need to ask for a bird first!")


async def setup(bot):
    await bot.add_cog(Hint(bot))
