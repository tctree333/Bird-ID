# voice.py | commands for voice
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

from discord.ext import commands, tasks

import bot.voice as voice_functions
from bot.data import logger, database
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
        await voice_functions.play(ctx, None)

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

    @commands.command(help="- Skip forward 5 seconds", aliases=["fw", "forwards"])
    @commands.check(CustomCooldown(2.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def forward(self, ctx, seconds: int = 5):
        logger.info("command: forward")
        if seconds < 1:
            await ctx.send("Invalid number of seconds!")
            return
        await voice_functions.rel_seek(ctx, seconds)

    @commands.command(
        help="- Skip back 5 seconds", aliases=["bk", "backward", "backwards"]
    )
    @commands.check(CustomCooldown(2.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def back(self, ctx, seconds: int = 5):
        logger.info("command: back")
        if seconds < 1:
            await ctx.send("Invalid number of seconds!")
            return
        await voice_functions.rel_seek(ctx, seconds * -1)

    @commands.command(help="- Replay", aliases=["rp", "re"])
    @commands.check(CustomCooldown(2.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def replay(self, ctx):
        logger.info("command: replay")
        await voice_functions.rel_seek(ctx, None)

    @commands.command(help="- Disconnect from voice", aliases=["dc"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def disconnect(self, ctx):
        logger.info("command: disconnect")
        current_voice = database.get(f"voice.server:{ctx.guild.id}")
        if current_voice is not None:
            race = ctx.bot.get_cog("Race")
            await race.stop_race_(ctx)
        else:
            await voice_functions.disconnect(ctx)

    @tasks.loop(minutes=10)
    async def cleanup(self):
        logger.info("running cleanup task")
        await voice_functions.cleanup(self.bot)


async def setup(bot):
    await bot.add_cog(Voice(bot))
