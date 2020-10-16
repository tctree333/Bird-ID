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

import asyncio

import discord
from discord.ext import commands

from bot.data import logger
from bot.functions import CustomCooldown


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_voice_client(self, ctx, connect=False):
        voice = ctx.author.voice
        if voice is None or voice.channel is None:
            await ctx.send("**Please join a voice channel to connect the bot!**")
            return None
        client = next(
            filter(lambda x: x.guild == voice.channel.guild, self.bot.voice_clients), None
        )
        if client is None:
            if connect:
                try:
                    client = await voice.channel.connect()
                    await ctx.send(f"Connected to {voice.channel.mention}")
                    return client
                except asyncio.TimeoutError:
                    await ctx.send(
                        "**Could not connect to voice channel in time.**\n*Please try again.*"
                    )
                except discord.ClientException:
                    await ctx.send("**I'm already connected to another voice channel!**")
                return None
            await ctx.send("**The bot isn't in a voice channel!**")
            return None
        if client.channel != voice.channel:
            await ctx.send("**You need to be in the same voice channel as the bot!**")
            return None
        return client

    # @commands.command(help="- Connects to a voice channel")
    # @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    # @commands.guild_only()
    # async def connect(self, ctx):
    #     logger.info("command: connect")

    #     voice = ctx.author.voice
    #     if voice is None or voice.channel is None:
    #         await ctx.send("Please join a voice channel to connect the bot!")
    #         return
    #     try:
    #         await voice.channel.connect()
    #         await ctx.send(f"Connected to {voice.channel.mention}")
    #     except asyncio.TimeoutError:
    #         await ctx.send(
    #             "**Could not connect to voice channel in time.**\n*Please try again.*"
    #         )
    #         return
    #     except discord.ClientException:
    #         await ctx.send("**I'm already connected to another voice channel!**")
    #         return

    @commands.command(help="- Play a sound")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def play(self, ctx):
        logger.info("command: play")

        client = await self.get_voice_client(ctx, connect=True)
        if client is None:
            return
        if client.is_paused():
            client.resume()
            await ctx.send("Resumed playing.")
            return
        await ctx.send("Playing...")
        source = await discord.FFmpegOpusAudio.from_probe("rick.mp3")
        client.play(source)

    @commands.command(help="- Pause playing")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def pause(self, ctx):
        logger.info("command: pause")

        client = await self.get_voice_client(ctx)
        if client is None:
            return
        if client.is_playing():
            client.pause()
            await ctx.send("Paused.")
        elif client.is_paused():
            await ctx.send("Already paused.")
        else:
            await ctx.send("There's nothing playing!")

    @commands.command(help="- Stop playing")
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def stop(self, ctx):
        logger.info("command: stop")

        client = await self.get_voice_client(ctx)
        if client is None:
            return
        if client.is_playing() or client.is_paused():
            client.stop()
            await ctx.send("Stopped playing.")
        else:
            await ctx.send("There's nothing playing!")

    @commands.command(help="- Disconnect from voice", aliases=["dc"])
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    async def disconnect(self, ctx):
        logger.info("command: disconnect")

        client = await self.get_voice_client(ctx)
        if client is None:
            return
        client.stop()
        await client.disconnect()
        await ctx.send("Bye!")


def setup(bot):
    bot.add_cog(Voice(bot))
