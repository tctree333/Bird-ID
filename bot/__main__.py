# __main__.py | main program
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

import asyncio
import concurrent.futures
import os
import sys
from datetime import date, datetime, timedelta, timezone

import discord
import holidays
from discord.ext import commands, tasks
from sentry_sdk import capture_exception

from bot.core import rotate_cache, send_bird
from bot.data import GenericError, database, logger
from bot.data_functions import channel_setup, user_setup
from bot.filters import Filter
from bot.functions import (
    backup_all,
    drone_attack,
    get_all_users,
    handle_error,
    prune_user_cache,
)

# The channel id that the backups send to
BACKUPS_CHANNEL = os.getenv("SCIOLY_ID_BOT_BACKUPS_CHANNEL", "")

if __name__ == "__main__":
    # Initialize bot
    intent: discord.Intents = discord.Intents.none()
    intent.guilds = True
    # intent.members = True
    intent.messages = True
    intent.voice_states = True

    cache_flags: discord.MemberCacheFlags = discord.MemberCacheFlags.none()
    cache_flags.voice = True

    bot = commands.Bot(
        command_prefix=["b!", "b.", "b#", "B!", "B.", "B#", "o>", "O>"],
        case_insensitive=True,
        description="BirdID - Your Very Own Ornithologist",
        help_command=commands.DefaultHelpCommand(verify_checks=False),
        intents=intent,
        member_cache_flags=cache_flags,
    )

    @bot.event
    async def on_ready():
        print("Ready!")
        logger.info("Logged in as:")
        logger.info(bot.user.name)
        logger.info(bot.user.id)
        # Change discord activity
        await bot.change_presence(activity=discord.Activity(type=3, name="birds"))
        refresh_cache.start()
        refresh_user_cache.start()
        evict_user_cache.start()
        if os.getenv("SCIOLY_ID_BOT_ENABLE_BACKUPS") != "false":
            refresh_backup.start()

    # Here we load our extensions(cogs) that are located in the cogs directory, each cog is a collection of commands
    core_extensions = [
        "bot.cogs.get_birds",
        "bot.cogs.check",
        "bot.cogs.skip",
        "bot.cogs.hint",
        "bot.cogs.score",
        "bot.cogs.stats",
        "bot.cogs.state",
        "bot.cogs.sessions",
        "bot.cogs.race",
        "bot.cogs.voice",
        "bot.cogs.meta",
        "bot.cogs.other",
    ]
    extra_extensions = os.getenv("SCIOLY_ID_BOT_EXTRA_COGS", "").strip().split(",")

    for extension in core_extensions + extra_extensions:
        if extension.strip() == "":
            continue
        try:
            bot.load_extension(extension)
        except (
            discord.errors.ClientException,
            commands.errors.ExtensionNotFound,
            commands.errors.ExtensionFailed,
        ) as e:
            if extension in core_extensions:
                logger.exception(f"Failed to load extension {extension}.", e)
                capture_exception(e)
                raise e
            logger.error(f"Failed to load extension {extension}.", e)

    if sys.platform == "win32":
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    ######
    # Global Command Checks
    ######

    @bot.check
    async def prechecks(ctx):
        await ctx.trigger_typing()

        logger.info("global check: checking permissions")
        await commands.bot_has_permissions(
            send_messages=True, embed_links=True, attach_files=True
        ).predicate(ctx)

        logger.info("global check: checking banned")
        if database.zscore("ignore:global", str(ctx.channel.id)) is not None:
            raise GenericError(code=192)
        if database.zscore("banned:global", str(ctx.author.id)) is not None:
            raise GenericError(code=842)

        logger.info("global check: logging command frequency")
        database.zincrby("frequency.command:global", 1, str(ctx.command))

        logger.info("global check: database setup")
        await channel_setup(ctx)
        await user_setup(ctx)

        return True

    @bot.check
    async def is_holiday(ctx):
        """Sends a picture of a turkey on Thanksgiving.

        Can be extended to other holidays as well.
        """
        logger.info("global check: checking holiday")
        now = datetime.now(tz=timezone(-timedelta(hours=4))).date()
        us = holidays.US()
        if now in us:
            if us.get(now) == "Thanksgiving":
                await send_bird(
                    ctx,
                    "Wild Turkey",
                    "images",
                    Filter(),
                    message="**It's Thanksgiving!**\nEnjoy this birb responsibly!.",
                )
                raise GenericError(code=666)
            if us.get(now) == "Independence Day":
                await send_bird(
                    ctx,
                    "Bald Eagle",
                    "images",
                    Filter(),
                    message="**It's Independence Day!**\nEnjoy this birb responsibly!",
                )
                raise GenericError(code=666)
        elif now == date(now.year, 4, 1):
            return await drone_attack(ctx)
        return True

    ######
    # GLOBAL ERROR CHECKING
    ######
    @bot.event
    async def on_command_error(ctx, error):
        """Handles errors for all commands without local error handlers."""
        logger.info("Error: " + str(error))

        # don't handle errors with local handlers
        if hasattr(ctx.command, "on_error"):
            return

        await handle_error(ctx, error)

    @tasks.loop(hours=0.5)
    async def refresh_cache():
        """Task to delete a random selection of cached birds every hour."""
        logger.info("TASK: Refreshing some cache items")
        event_loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            await event_loop.run_in_executor(executor, rotate_cache)

    @tasks.loop(hours=3.0)
    async def refresh_user_cache():
        """Task to update User cache to increase performance of commands."""
        logger.info("TASK: Updating User cache")
        await get_all_users(bot)

    @tasks.loop(minutes=8.0)
    async def evict_user_cache():
        """Task to remove keys from the User cache to ensure freshness."""
        logger.info("TASK: Removing user keys")
        prune_user_cache(10)

    @tasks.loop(hours=1.0)
    async def refresh_backup():
        """Sends a copy of the database to a discord channel (BACKUPS_CHANNEL)."""
        logger.info("TASK: Refreshing backup")
        try:
            os.remove("bot_files/backups/dump.dump")
            logger.info("Cleared backup dump")
        except FileNotFoundError:
            logger.info("Already cleared backup dump")
        try:
            os.remove("bot_files/backups/keys.txt")
            logger.info("Cleared backup keys")
        except FileNotFoundError:
            logger.info("Already cleared backup keys")

        event_loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            await event_loop.run_in_executor(executor, backup_all)

        if BACKUPS_CHANNEL.isdecimal():
            logger.info("Sending backup files")
            channel = bot.get_channel(int(BACKUPS_CHANNEL))
            with open("bot_files/backups/dump.dump", "rb") as f:
                await channel.send(file=discord.File(f, filename="dump"))
            with open("bot_files/backups/keys.txt", "r") as f:
                await channel.send(file=discord.File(f, filename="keys.txt"))
            logger.info("Backup Files Sent!")

    # Actually run the bot
    token = os.getenv("SCIOLY_ID_BOT_TOKEN")
    bot.run(token)
