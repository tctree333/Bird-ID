# voice.py | commands for voice
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

from discord.ext import commands, tasks

import bot.voice as voice_functions
from bot.data import logger
from bot.functions import CustomCooldown


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup.start()

    def cog_unload(self):
        self.cleanup.cancel()

    @commands.command(help="- Play a sound")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def play(self, ctx):
        logger.info("command: play")
        await voice_functions.play(ctx, "rick.mp3")

    @commands.command(help="- Pause playing")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def pause(self, ctx):
        logger.info("command: pause")
        await voice_functions.pause(ctx)

    @commands.command(help="- Stop playing")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def stop(self, ctx):
        logger.info("command: stop")
        await voice_functions.stop(ctx)

    @commands.command(help="- Disconnect from voice", aliases=["dc"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def disconnect(self, ctx):
        logger.info("command: disconnect")
        await voice_functions.disconnect(ctx)

    @tasks.loop(minutes=10)
    async def cleanup(self):
        logger.info("running cleanup task")
        await voice_functions.cleanup(self.bot)


def setup(bot):
    bot.add_cog(Voice(bot))
