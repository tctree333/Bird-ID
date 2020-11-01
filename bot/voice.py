# voice.py | functions for voice
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
from typing import Optional

import discord
import discord.utils
import pydub

from bot.data import logger, database


async def _send(ctx, silent, message: str):
    if not silent:
        await ctx.send(message)


async def get_voice_client(
    ctx, connect: bool = False, silent: bool = False
) -> Optional[discord.VoiceClient]:
    logger.info("fetching voice client")

    voice = None
    if ctx.author:
        voice = ctx.author.voice
        if voice is None or voice.channel is None or voice.channel.guild != ctx.guild:
            await _send(ctx, silent, "**Please join a voice channel to connect the bot!**")
            return None

    current_voice = database.get(f"voice.server:{ctx.guild.id}")
    if current_voice is not None and current_voice.decode("utf-8") != str(
        ctx.channel.id
    ):
        logger.info("already vc race")
        bound_channel = ctx.guild.get_channel(int(current_voice))
        await ctx.send(
            "**The voice channel is currently in use!**"
            + (
                f"\n*Use {bound_channel.mention} for vc settings!*"
                if bound_channel
                else ""
            )
        )
        return None

    client: discord.VoiceClient = discord.utils.find(
        lambda x: x.guild == ctx.guild, ctx.bot.voice_clients
    )
    if client is None:
        if connect and voice:
            try:
                client = await voice.channel.connect()
                await _send(ctx, silent, f"Connected to {voice.channel.mention}")
                return client
            except asyncio.TimeoutError:
                await _send(
                    ctx,
                    silent,
                    "**Could not connect to voice channel in time.**\n*Please try again.*",
                )
            except discord.ClientException:
                await _send(
                    ctx, silent, "**I'm already connected to another voice channel!**"
                )
        else:
            await _send(ctx, silent, "**The bot isn't in a voice channel!**")
        return None

    if voice and client.channel != voice.channel:
        await _send(
            ctx, silent, "**You need to be in the same voice channel as the bot!**"
        )
        return None
    return client


async def play(ctx, filename: str, silent: bool = False):
    logger.info("voice: playing")

    client: discord.VoiceClient = await get_voice_client(ctx, connect=True)
    if client is None:
        return False
    if client.is_paused():
        client.resume()
        await _send(ctx, silent, "Resumed playing.")
        return
    # source = await discord.FFmpegOpusAudio.from_probe(filename)
    source = CustomAudio(filename)
    if client.is_playing():
        client.stop()
    client.play(source)
    await _send(ctx, silent, "Playing...")
    return True


async def pause(ctx, silent: bool = False):
    logger.info("voice: pausing")

    client: discord.VoiceClient = await get_voice_client(ctx)
    if client is None:
        return False
    if client.is_playing():
        client.pause()
        await _send(ctx, silent, "Paused.")
    elif client.is_paused():
        await _send(ctx, silent, "Already paused.")
    else:
        await _send(ctx, silent, "There's nothing playing!")
    return True


async def stop(ctx, silent: bool = False):
    logger.info("voice: stopping")

    client: discord.VoiceClient = await get_voice_client(ctx)
    if client is None:
        return False
    if client.is_playing() or client.is_paused():
        client.stop()
        await _send(ctx, silent, "Stopped playing.")
    else:
        await _send(ctx, silent, "There's nothing playing!")
    return True


async def disconnect(ctx, silent: bool = False):
    logger.info("voice: disconnecting")

    client: discord.VoiceClient = await get_voice_client(ctx)
    if client is None:
        return False
    client.stop()
    await client.disconnect()
    client.cleanup()
    await _send(ctx, silent, "Bye!")
    return True


class FauxContext:
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot

    def __getattr__(self, name):
        return getattr(self.channel, name, None)

async def cleanup(bot):
    logger.info("cleaning up empty channels")
    for client in bot.voice_clients:
        if len(client.channel.voice_states) == 1:
            logger.info("found empty")
            current_voice = database.get(f"voice.server:{client.guild.id}")
            if current_voice is not None:
                logger.info("vc race")
                bound_channel = client.guild.get_channel(int(current_voice))
                race = bot.get_cog("Race")
                await race.stop_race_(FauxContext(bound_channel, bot))
            else:
                await client.disconnect()
    logger.info("done cleaning!")


class CustomAudio(discord.AudioSource):
    def __init__(self, filename):
        self.filename = filename
        self.cursor = 0
        self.segment = pydub.AudioSegment.from_file(filename, format=filename.split(".")[-1])
        # .set_frame_rate(48000)

    def read(self):
        self.cursor += 20
        return self.segment[self.cursor-20:self.cursor].raw_data

    def is_opus(self):
        return False

    def cleanup(self):
        pass
