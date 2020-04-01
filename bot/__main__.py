# __main__.py | main program
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
import concurrent.futures
import errno
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, date, timezone, timedelta

from dotenv import load_dotenv, find_dotenv
import aiohttp
import discord
import holidays
import redis
import wikipedia
from discord.ext import commands, tasks
from sentry_sdk import capture_exception, configure_scope

load_dotenv(find_dotenv(), verbose=True)

from bot.data import GenericError, database, logger
from bot.functions import backup_all, channel_setup, precache, send_bird, drone_attack

# The channel id that the backups send to
BACKUPS_CHANNEL = os.environ["SCIOLY_ID_BOT_BACKUPS_CHANNEL"]

def start_precache():
    """Downloads all the images/songs before they're needed."""
    asyncio.run(precache())

def start_backup():
    """Backs up the database to a discord channel."""
    asyncio.run(backup_all())

if __name__ == '__main__':
    # Initialize bot
    bot = commands.Bot(
        command_prefix=['b!', 'b.', 'b#', 'B!', 'B.', 'B#', 'o>', 'O>'],
        case_insensitive=True,
        description="BirdID - Your Very Own Ornithologist",
        help_command=commands.DefaultHelpCommand(verify_checks=False)
    )

    @bot.event
    async def on_ready():
        print("Ready!")
        logger.info("Logged in as:")
        logger.info(bot.user.name)
        logger.info(bot.user.id)
        # Change discord activity
        await bot.change_presence(activity=discord.Activity(type=3, name="birds"))

        if os.environ["SCIOLY_ID_BOT_ENABLE_PRECACHE"] == "true":
            refresh_cache.start()
        
        if os.environ["SCIOLY_ID_BOT_ENABLE_BACKUPS"] == "true":
            refresh_backup.start()

    # Here we load our extensions(cogs) that are located in the cogs directory, each cog is a collection of commands
    core_extensions = [
        'bot.cogs.get_birds', 'bot.cogs.check', 'bot.cogs.skip', 'bot.cogs.hint', 'bot.cogs.score', 'bot.cogs.state',
        'bot.cogs.sessions', 'bot.cogs.race', 'bot.cogs.other'
    ]
    
    if "SCIOLY_ID_BOT_EXTRA_COGS" in os.environ:
        extra_extensions = os.environ["SCIOLY_ID_BOT_EXTRA_COGS"].split(',')
    else:
        extra_extensions = []

    for extension in core_extensions + extra_extensions:
        try:
            bot.load_extension(extension)
        except (discord.errors.ClientException, commands.errors.ExtensionNotFound, commands.errors.ExtensionFailed) as e:
            if extension in core_extensions:
                logger.exception(f'Failed to load extension {extension}.', e)
                capture_exception(e)
                raise e
            else:
                logger.error(f'Failed to load extension {extension}.', e)

    if sys.platform == 'win32':
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

    ######
    # Global Command Checks
    ######

    @bot.check
    def set_sentry_tag(ctx):
        """Tags sentry errors with current command."""
        logger.info("global check: checking sentry tag")
        with configure_scope() as scope:
            scope.set_tag("command", ctx.command.name)
        return True

    @bot.check
    async def dm_cooldown(ctx):
        """Clears the cooldown in DMs."""
        logger.info("global check: checking dm cooldown clear")
        if ctx.command.is_on_cooldown(ctx) and ctx.guild is None:
            ctx.command.reset_cooldown(ctx)
        return True

    @bot.check
    def bot_has_permissions(ctx):
        """Checks if the bot has correct permissions."""
        logger.info("global check: checking permissions")
        # code copied from @commands.bot_has_permissions(send_messages=True, embed_links=True, attach_files=True)
        if ctx.guild is not None:
            perms = {"send_messages": True, "embed_links": True, "attach_files": True, "manage_roles": True}
            guild = ctx.guild
            me = guild.me if guild is not None else ctx.bot.user
            permissions = ctx.channel.permissions_for(me)

            missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]

            if not missing:
                return True

            raise commands.BotMissingPermissions(missing)
        else:
            return True

    @bot.check
    def user_banned(ctx):
        """Disallows users that are banned from the bot."""
        logger.info("global check: checking banned")
        if database.zscore("banned:global", str(ctx.author.id)) is None:
            return True
        else:
            raise GenericError(code=842)

    @bot.check
    async def is_holiday(ctx):
        """Sends a picture of a turkey on Thanksgiving.
        
        Can be extended to other holidays as well.
        """
        logger.info("global check: checking holiday")
        now = datetime.now(tz=timezone(-timedelta(hours=4)))
        now = date(now.year, now.month, now.day)
        us = holidays.US()
        if now in us:
            if us.get(now) == "Thanksgiving":
                await send_bird(ctx, "Wild Turkey")
                await ctx.send("**It's Thanksgiving!**\nGo celebrate with your family.")
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
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " + str(round(error.retry_after)) + " s.", delete_after=5.0)

        elif isinstance(error, commands.CommandNotFound):
            capture_exception(error)
            await ctx.send("Sorry, the command was not found.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("This command requires an argument!")

        elif isinstance(error, commands.BadArgument):
            await ctx.send("The argument passed was invalid. Please try again.")

        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send("An invalid character was detected. Please try again.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "**The bot does not have enough permissions to fully function.**\n" +
                f"**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`\n" +
                "*Please try again once the correct permissions are set.*"
            )

        elif isinstance(error, commands.NoPrivateMessage):
            capture_exception(error)
            await ctx.send("**This command is unavaliable in DMs!**")

        elif isinstance(error, GenericError):
            if error.code == 842:
                await ctx.send("**Sorry, you cannot use this command.**")
            elif error.code == 666:
                logger.info("GenericError 666")
            elif error.code == 201:
                logger.info("HTTP Error")
                capture_exception(error)
                await ctx.send("**An unexpected HTTP Error has occurred.**\n *Please try again.*")
            else:
                logger.info("uncaught generic error")
                capture_exception(error)
                await ctx.send(
                    "**An uncaught generic error has occurred.**\n" +
                    "*Please log this message in #support in the support server below, or try again.*\n" +
                    "**Error:** " + str(error)
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
                raise error

        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, redis.exceptions.ResponseError):
                capture_exception(error.original)
                if database.exists(f"channel:{ctx.channel.id}"):
                    await ctx.send(
                        "**An unexpected ResponseError has occurred.**\n"
                        "*Please log this message in #support in the support server below, or try again.*\n"
                        "**Error:** " + str(error)
                    )
                    await ctx.send("https://discord.gg/fXxYyDJ")
                else:
                    await channel_setup(ctx)
                    await ctx.send("Please run that command again.")

            elif isinstance(error.original, wikipedia.exceptions.DisambiguationError):
                await ctx.send("Wikipedia page not found. (Disambiguation Error)")

            elif isinstance(error.original, wikipedia.exceptions.PageError):
                await ctx.send("Wikipedia page not found. (Page Error)")

            elif isinstance(error.original, wikipedia.exceptions.WikipediaException):
                capture_exception(error.original)
                await ctx.send("Wikipedia page unavaliable. Try again later.")

            elif isinstance(error.original, discord.Forbidden):
                if error.original.code == 50007:
                    await ctx.send("I was unable to DM you. Check if I was blocked and try again.")
                else:
                    capture_exception(error)
                    await ctx.send(
                        "**An unexpected Forbidden error has occurred.**\n"
                        "*Please log this message in #support in the support server below, or try again.*\n"
                        "**Error:** " + str(error)
                    )

            elif isinstance(error.original, discord.HTTPException):
                if error.original.status == 502:
                    await ctx.send("**An error has occured with discord. :(**\n*Please try again.*")
                else:
                    capture_exception(error.original)
                    await ctx.send(
                        "**An unexpected HTTPException has occurred.**\n" +
                        "*Please log this message in #support in the support server below, or try again*\n" +
                        "**Error:** " + str(error.original)
                    )
                    await ctx.send("https://discord.gg/fXxYyDJ")

            elif isinstance(error.original, aiohttp.ClientOSError):
                if error.original.errno == errno.ECONNRESET:
                    await ctx.send("**An error has occured with discord. :(**\n*Please try again.*")
                else:
                    capture_exception(error.original)
                    await ctx.send(
                        "**An unexpected ClientOSError has occurred.**\n" +
                        "*Please log this message in #support in the support server below, or try again.*\n" +
                        "**Error:** " + str(error.original)
                    )
                    await ctx.send("https://discord.gg/fXxYyDJ")

            else:
                logger.info("uncaught command error")
                capture_exception(error.original)
                await ctx.send(
                    "**An uncaught command error has occurred.**\n" +
                    "*Please log this message in #support in the support server below, or try again.*\n" +
                    "**Error:**  " + str(error)
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
                raise error

        else:
            logger.info("uncaught non-command")
            capture_exception(error)
            await ctx.send(
                "**An uncaught non-command error has occurred.**\n" +
                "*Please log this message in #support in the support server below, or try again.*\n" + "**Error:** " +
                str(error)
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    @tasks.loop(hours=24.0)
    async def refresh_cache():
        """Re-downloads all the images/songs."""
        logger.info("clear cache")
        try:
            shutil.rmtree(r'cache/images/', ignore_errors=True)
            logger.info("Cleared image cache.")
        except FileNotFoundError:
            logger.info("Already cleared image cache.")

        try:
            shutil.rmtree(r'cache/songs/', ignore_errors=True)
            logger.info("Cleared songs cache.")
        except FileNotFoundError:
            logger.info("Already cleared songs cache.")
        event_loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            await event_loop.run_in_executor(executor, start_precache)

    @tasks.loop(hours=6.0)
    async def refresh_backup():
        """Sends a copy of the database to a discord channel (BACKUPS_CHANNEL)."""
        logger.info("Refreshing backup")
        try:
            os.remove('backups/dump.dump')
            logger.info("Cleared backup dump")
        except FileNotFoundError:
            logger.info("Already cleared backup dump")
        try:
            os.remove('backups/keys.txt')
            logger.info("Cleared backup keys")
        except FileNotFoundError:
            logger.info("Already cleared backup keys")

        event_loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            await event_loop.run_in_executor(executor, start_backup)

        logger.info("Sending backup files")
        channel = bot.get_channel(BACKUPS_CHANNEL)
        with open("backups/dump.dump", 'rb') as f:
            await channel.send(file=discord.File(f, filename="dump"))
        with open("backups/keys.txt", 'r') as f:
            await channel.send(file=discord.File(f, filename="keys.txt"))
        logger.info("Backup Files Sent!")

    # Actually run the bot
    token = os.environ["SCIOLY_ID_BOT_TOKEN"]
    bot.run(token)
