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

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import ContextOrInteraction, database, logger


class Hint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # give hint
    @app_commands.command(name="hint", description="Gives first letter of current bird")
    async def hint(self, interaction: discord.Interaction):
        logger.info("command: hint")

        ctx = ContextOrInteraction(interaction)

        currentBird = database.hget(f"channel:{ctx.channel.id}", "bird").decode("utf-8")
        if currentBird != "":  # check if there is bird
            await interaction.response.send_message(
                f"The first letter is {currentBird[0]}"
            )
        else:
            await interaction.response.send_message("You need to ask for a bird first!")


async def setup(bot):
    await bot.add_cog(Hint(bot))
