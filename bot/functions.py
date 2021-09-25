# functions.py | function definitions
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
import difflib
import errno
import functools
import hashlib
import itertools
import os
import pickle
import random

import aiohttp
import chardet
import discord
import redis
import wikipedia
from discord.ext import commands
from sentry_sdk import capture_exception

from bot.data import (
    GenericError,
    birdList,
    birdListMaster,
    database,
    logger,
    sciListMaster,
    songBirds,
    states,
    taxons,
)
from bot.data_functions import channel_setup


def cache(func=None, pre=None, local=True):
    """Cache decorator based on functools.lru_cache.

    This is not a very good cache, but it "works" for our
    purposes.

    This (optionally) caches items into a Redis database
    (bot.data.database). It does not have a max_size but sets
    key expiration to 90 days. Items are pickled before storing
    into the database.

    Cache keys are based on a sha1 hash. Currently, only strings
    and integers are supported and it will not tell the difference
    between a string and an integer with the same value.

    If multiple functions with the same name are used, colisions
    will occur.

    In addition, results are only cached by the first positional
    argument. If pre is provided, the cache key will be the
    first positional argument transformed by pre.
    """

    def wrapper(func):
        _cache = {}
        sentinel = object()
        hits = misses = 0

        def _cache_store(key, value):
            if local:
                _cache[key] = value
                return
            pickled = pickle.dumps(value, protocol=4)
            database.set(
                f"cache.{func.__name__}:{key}", pickled, ex=7776000
            )  # 60*60*24*90

        def _cache_get(key, default=None):
            if local:
                return _cache.get(key, default)
            data = database.get(f"cache.{func.__name__}:{key}")
            if data is None:
                return default
            return pickle.loads(data)

        def _cache_len():
            if local:
                return _cache.__len__()
            return sum(
                1
                for _ in database.scan_iter(
                    match=f"cache.{func.__name__}:*", count=1000
                )
            )

        def _get_hash(item):
            if local:
                return hash(item)
            if not isinstance(item, (str, int)):
                raise TypeError(
                    "cache is only available with strings or ints in non-local mode!"
                )
            return hashlib.sha1(str(item).encode()).hexdigest()

        def evict():
            """Evicts a random item from the local cache."""
            if not local:
                raise ValueError("Cannot evict from Redis cache!")
            _cache.pop(random.choice((*_cache, object())), 0)

        async def wrapped(*args, **kwds):
            # Simple caching without ordering or size limit
            nonlocal hits, misses
            if pre:
                key = _get_hash(pre(args[0]))
            else:
                key = _get_hash(args[0])
            result = _cache_get(key, sentinel)
            if result is not sentinel:
                # print("hit")
                hits += 1
                return result
            # print("miss")
            misses += 1
            result = await func(*args, **kwds)
            _cache_store(key, result)
            return result

        def cache_info():
            """Report cache statistics"""
            return functools._CacheInfo(hits, misses, None, _cache_len())

        wrapped.cache_info = cache_info
        wrapped.evict = evict
        return functools.update_wrapper(wrapped, func)

    if func:
        return wrapper(func)
    return wrapper


def check_state_role(ctx) -> list:
    """Returns a list of state roles a user has.

    `ctx` - Discord context object
    """
    logger.info("checking roles")
    user_states = []
    if ctx.guild is not None:
        logger.info("server context")
        user_role_names = [role.name.lower() for role in ctx.author.roles]
        for state in states:
            # gets similarities
            if set(user_role_names).intersection(set(states[state]["aliases"])):
                user_states.append(state)
    else:
        logger.info("dm context")
    logger.info(f"user roles: {user_states}")
    return user_states


async def fetch_get_user(user_id: int, ctx=None, bot=None, member: bool = False):
    if (ctx is None and bot is None) or (ctx is not None and bot is not None):
        raise ValueError("Only one of ctx or bot must be passed")
    if ctx:
        bot = ctx.bot
    elif member:
        raise ValueError("ctx must be passed for member lookup")
    if not member:
        return await _fetch_cached_user(user_id, bot)
    if bot.intents.members:
        return ctx.guild.get_member(user_id)
    try:
        return await ctx.guild.fetch_member(user_id)
    except discord.HTTPException:
        return None


@cache()
async def _fetch_cached_user(user_id: int, bot):
    if bot.intents.members:
        return bot.get_user(user_id)
    try:
        return await bot.fetch_user(user_id)
    except discord.HTTPException:
        return None


async def send_leaderboard(
    ctx, title, page, database_key=None, data=None, items_per_page=10
):
    logger.info("building/sending leaderboard")

    if database_key is None and data is None:
        raise GenericError("database_key and data are both NoneType", 990)
    if database_key is not None and data is not None:
        raise GenericError("database_key and data are both set", 990)

    if page < 1:
        page = 1

    entry_count = (
        int(database.zcard(database_key)) if database_key is not None else data.count()
    )
    page = (page * 10) - 10

    if entry_count == 0:
        logger.info(f"no items in {database_key}")
        await ctx.send("There are no items in the database.")
        return

    if page > entry_count:
        page = entry_count - (entry_count % 10)

    leaderboard_list = (
        map(
            lambda x: (x[0].decode("utf-8"), x[1]),
            database.zrevrangebyscore(
                database_key, "+inf", "-inf", page, items_per_page, True
            ),
        )
        if database_key is not None
        else data.iloc[page : page + items_per_page - 1].items()
    )
    embed = discord.Embed(type="rich", colour=discord.Color.blurple())
    embed.set_author(name="Bird ID - An Ornithology Bot")
    leaderboard = "".join(
        (
            f"{i+1+page}. **{stats[0]}** - {int(stats[1])}\n"
            for i, stats in enumerate(leaderboard_list)
        )
    )
    embed.add_field(name=title, value=leaderboard, inline=False)

    await ctx.send(embed=embed)


def build_id_list(user_id=None, taxon=None, state=None, media="images") -> list:
    """Generates an ID list based on given arguments

    - `user_id`: User ID of custom list
    - `taxon`: taxon string/list
    - `state`: state string/list
    - `media`: images/songs
    """
    logger.info("building id list")
    if isinstance(taxon, str):
        taxon = taxon.split(" ")
    if isinstance(state, str):
        state = state.split(" ")

    state_roles = state if state else []
    if media in ("songs", "song", "s", "a"):
        state_list = "songBirds"
        default = songBirds
    elif media in ("images", "image", "i", "p"):
        state_list = "birdList"
        default = birdList
    else:
        raise GenericError("Invalid media type", code=990)

    custom_list = []
    if (
        user_id
        and "CUSTOM" in state_roles
        and database.exists(f"custom.list:{user_id}")
        and not database.exists(f"custom.confirm:{user_id}")
    ):
        custom_list = [
            bird.decode("utf-8") for bird in database.smembers(f"custom.list:{user_id}")
        ]

    birds = []
    if taxon:
        birds_in_taxon = set(
            itertools.chain.from_iterable(taxons.get(o, []) for o in taxon)
        )
        if state_roles:
            birds_in_state = set(
                itertools.chain(
                    *(states[state][state_list] for state in state_roles), custom_list
                )
            )
            birds = list(birds_in_taxon.intersection(birds_in_state))
        else:
            birds = list(birds_in_taxon.intersection(set(default)))
    elif state_roles:
        birds = list(
            set(
                itertools.chain(
                    *(states[state][state_list] for state in state_roles), custom_list
                )
            )
        )
    else:
        birds = default
    logger.info(f"number of birds: {len(birds)}")
    return birds


async def drone_attack(ctx):
    logger.info(f"holiday check: invoked command: {str(ctx.command)}")

    def video_embed():
        if random.randint(0, 1) == 1:
            embed = discord.Embed(
                title="YouTube",
                type="rich",
                colour=discord.Colour(0xD0021B),
                url="https://bit.ly/are-birds-real",
            )
            embed.set_image(url="http://i3.ytimg.com/vi/Fg_JcKSHUtQ/hqdefault.jpg")
            embed.add_field(
                name="TED",
                value="[A robot that flies like a bird | Markus Fischer](https://bit.ly/are-birds-real)",
            )
        else:
            embed = discord.Embed(
                title="Are Birds Real?",
                type="rich",
                colour=discord.Colour.default(),
                url="https://bit.ly/are-birds-real",
            )
            embed.set_image(
                url="https://www.sciencenews.org/sites/default/files/main/articles/feature_drones_opener.jpg"
            )
            embed.add_field(
                name="Wikipedia",
                value="In 1947 the C.I.A. was founded, its sole responsibility to watch and survey tens of thousands of Americans suspected of doing communist things. In 1953 Allen Dulles was made the first civilian director of the Central Intelligence Agency (C.I.A.) and made it his mission to ramp up the surveillance program. Dulles and his team hated birds with a passion, as they would often poop on their cars in the parking lot of the C.I.A. headquarters. This was one of the driving forces that led Dulles to not only implement robots into the sky, but actually replace birds in the process...",
            )

        return embed

    if str(ctx.command) in (
        "help",
        "covid",
        "botinfo",
        "invite",
        "list",
        "meme",
        "taxon",
        "wikipedia",
        "remove",
        "set",
        "give_role",
        "remove_role",
        "test",
        "error",
        "ban",
        "unban",
        "send_as_bot",
    ):
        logger.info("Passthrough Command")
        return True

    if str(ctx.command) in ("bird", "song", "goatsucker"):
        images = os.listdir("bot/media/images/drone")
        path = f"bot/media/images/drone/{images[random.randint(0,len(images)-1)]}"
        BASE_MESSAGE = (
            "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, "
            + "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. "
            + "Use `b!{hint_cmd}` for a hint.**"
        )

        if str(ctx.command) == "bird":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="image",
                    new_cmd="bird",
                    skip_cmd="skip",
                    check_cmd="check",
                    hint_cmd="hint",
                )
                + "\n*This is an image.*"
            )
        elif str(ctx.command) == "goatsucker":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="image",
                    new_cmd="gs",
                    skip_cmd="skip",
                    check_cmd="check",
                    hint_cmd="hint",
                )
            )
        elif str(ctx.command) == "bird":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="song",
                    new_cmd="song",
                    skip_cmd="skip",
                    check_cmd="check",
                    hint_cmd="hint",
                )
            )

        file_obj = discord.File(path, filename=f"bird.{path.split('.')[-1]}")
        await ctx.send(file=file_obj)

    elif str(ctx.command) in ("check",):
        args = ctx.message.content.split(" ")[1:]
        matches = difflib.get_close_matches(
            " ".join(args), birdListMaster + sciListMaster, n=1
        )
        if "drone" in args:
            await ctx.send(
                "SHHHHHH! Birds are **NOT** government drones! You'll blow our cover, and we'll need to get rid of you."
            )
        elif matches:
            await ctx.send(
                "Correct! Good job! The bird was **definitely a real bird**."
            )
            await ctx.send(embed=video_embed())
        else:
            await ctx.send("Sorry, the bird was actually **definitely a real bird**.")
            await ctx.send(embed=video_embed())

    elif str(ctx.command) in ("skip",):
        await ctx.send("Ok, skipping **definitely a real bird.**")
        await ctx.send(embed=video_embed())

    elif str(ctx.command) in ("hint",):
        await ctx.send("This is definitely a real bird, **NOT** a government drone.")

    elif str(ctx.command) in ("info",):
        await ctx.send(
            "Birds are real. Don't believe what others may say. **BIRDS ARE VERY REAL!**"
        )

    elif str(ctx.command) in ("race", "session"):
        await ctx.send(
            "Races and sessions have been disabled today. We apologize for any inconvenience."
        )

    elif str(ctx.command) in ("leaderboard", "missed", "score", "streak", "userscore"):
        embed = discord.Embed(
            type="rich",
            colour=discord.Color.blurple(),
            title=f"**{str(ctx.command).title()}**",
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(
            name=f"**{str(ctx.command).title()}**",
            value="User scores and data have been cleared. We apologize for the inconvenience.",
            inline=False,
        )
        await ctx.send(embed=embed)

    raise GenericError(code=666)


def backup_all():
    """Backs up the database to a file.

    This function serializes all data in the REDIS database
    into a file in the `backups` directory.

    This function is run with a task every 6 hours and sends the files
    to a specified discord channel.
    """
    logger.info("Starting Backup")
    logger.info("Creating Dump")
    keys = (key.decode("utf-8") for key in database.keys())
    dump = ((database.dump(key), key) for key in keys)
    logger.info("Finished Dump")
    logger.info("Writing To File")
    os.makedirs("bot_files/backups", exist_ok=True)
    with open("bot_files/backups/dump.dump", "wb") as f:
        with open("bot_files/backups/keys.txt", "w") as k:
            for item, key in dump:
                pickle.dump(item, f)
                k.write(f"{key}\n")
    logger.info("Backup Finished")


async def get_all_users(bot):
    logger.info("Starting user cache")
    user_ids = map(int, database.zrangebyscore("users:global", "-inf", "+inf"))
    for user_id in user_ids:
        await fetch_get_user(user_id, bot=bot, member=False)
    logger.info("User cache finished")


def prune_user_cache(count: int = 5):
    """Evicts `count` items from the user cache."""
    for _ in range(count):
        _fetch_cached_user.evict()


async def auto_decode(data: bytes):
    def _get_encoding():
        detector = chardet.UniversalDetector()
        for chunk in data.splitlines(keepends=True):
            detector.feed(chunk)
            if detector.done:
                break
        detector.close()
        return detector.result

    event_loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(1) as executor:
        detected = await event_loop.run_in_executor(executor, _get_encoding)
    if detected["encoding"] and detected["confidence"] > 0.4:
        return data.decode(detected["encoding"])
    return None


class CustomCooldown:
    """Halve cooldown times in DM channels."""

    # Code adapted from discord.py example
    def __init__(
        self,
        per: float,
        disable: bool = False,
        bucket: commands.BucketType = commands.BucketType.channel,
    ):
        """Initialize a custom cooldown.

        `per` (float) - Cooldown default duration, halves in DM channels
        `bucket` (commands.BucketType) - cooldown scope, defaults to channel
        """
        self.disable = disable

        rate = 1

        dm_per = per / 2  # half cooldowns in DMs
        race_per = 0.5  # pin check cooldown during races to 0.5 seconds
        rate_limit_per = (
            per * 1.75
        )  # 75% longer cooldowns on core commands during macaulay issues

        self.default_mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)
        self.dm_mapping = commands.CooldownMapping.from_cooldown(rate, dm_per, bucket)
        self.race_mapping = commands.CooldownMapping.from_cooldown(
            rate, race_per, bucket
        )
        self.rate_limit_mapping = commands.CooldownMapping.from_cooldown(
            rate, rate_limit_per, bucket
        )

    def __call__(self, ctx: commands.Context):
        if (
            ctx.command.name
            in (
                "bird",
                "song",
                "goatsucker",
                "check",
                "skip",
            )
            and database.exists("cooldown:global")
            and int(database.get("cooldown:global")) > 1
        ):
            bucket = self.rate_limit_mapping.get_bucket(ctx.message)

        elif not self.disable and ctx.guild is None:
            bucket = self.dm_mapping.get_bucket(ctx.message)

        elif ctx.channel.name.startswith("racing") and ctx.command.name.startswith(
            "check"
        ):
            bucket = self.race_mapping.get_bucket(ctx.message)

        else:
            bucket = self.default_mapping.get_bucket(ctx.message)

        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        return True


async def handle_error(ctx, error):
    """Function for comprehensive error handling."""

    if isinstance(error, commands.CommandOnCooldown):  # send cooldown
        await ctx.send(
            (
                "**Cooldowns have been temporarily increased due to increased usage.**"
                if getattr(error.cooldown, "rate_limit", False)
                else "**Cooldown.** "
            )
            + "Try again after "
            + str(round(error.retry_after, 2))
            + " s.",
            delete_after=5.0,
        )

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
            "**The bot does not have enough permissions to fully function.**\n"
            + f"**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`\n"
            + "*Please try again once the correct permissions are set.*"
        )

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You do not have the required permissions to use this command.\n"
            + f"**Required Perms:** `{'`, `'.join(error.missing_perms)}`"
        )

    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("**This command is unavailable in DMs!**")

    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("**This command is only available in DMs!**")

    elif isinstance(error, commands.NotOwner):
        logger.info("not owner")
        await ctx.send("Sorry, the command was not found.")

    elif isinstance(error, GenericError):
        if error.code == 192:
            # channel is ignored
            return
        if error.code == 842:
            await ctx.send("**Sorry, you cannot use this command.**")
        elif error.code == 666:
            logger.info("GenericError 666")
        elif error.code == 201:
            logger.info("HTTP Error")
            capture_exception(error)
            await ctx.send(
                "**An unexpected HTTP Error has occurred.**\n *Please try again.*"
            )
        else:
            logger.info("uncaught generic error")
            capture_exception(error)
            await ctx.send(
                "**An uncaught generic error has occurred.**\n"
                + "*Please log this message in #support in the support server below, or try again.*\n"
                + f"**Error code:** `{error.code}`"
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    elif isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, redis.exceptions.ResponseError):
            capture_exception(error.original)
            if database.exists(f"channel:{ctx.channel.id}"):
                await ctx.send(
                    "**An unexpected ResponseError has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again.*\n"
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
            await ctx.send("Wikipedia page unavailable. Try again later.")

        elif isinstance(error.original, discord.Forbidden):
            if error.original.code == 50007:
                await ctx.send(
                    "I was unable to DM you. Check if I was blocked and try again."
                )
            elif error.original.code == 50013:
                await ctx.send(
                    "There was an error with permissions. Check the bot has proper permissions and try again."
                )
            else:
                capture_exception(error)
                await ctx.send(
                    "**An unexpected Forbidden error has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again.*\n"
                    + f"**Error code:** `{error.original.code}`"
                )
                await ctx.send("https://discord.gg/fXxYyDJ")

        elif isinstance(error.original, discord.HTTPException):
            capture_exception(error.original)
            if error.original.status == 502:
                await ctx.send(
                    "**An error has occurred with discord. :(**\n*Please try again.*"
                )
            else:
                await ctx.send(
                    "**An unexpected HTTPException has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again*\n"
                    + f"**Reponse Code:** `{error.original.status}`"
                )
                await ctx.send("https://discord.gg/fXxYyDJ")

        elif isinstance(error.original, aiohttp.ClientOSError):
            capture_exception(error.original)
            if error.original.errno == errno.ECONNRESET:
                await ctx.send(
                    "**An error has occurred with discord. :(**\n*Please try again.*"
                )
            else:
                await ctx.send(
                    "**An unexpected ClientOSError has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again.*\n"
                    + f"**Error code:** `{error.original.errno}`"
                )
                await ctx.send("https://discord.gg/fXxYyDJ")

        elif isinstance(error.original, aiohttp.ServerDisconnectedError):
            capture_exception(error.original)
            await ctx.send("**The server disconnected.**\n*Please try again.*")

        elif isinstance(error.original, asyncio.TimeoutError):
            capture_exception(error.original)
            await ctx.send("**The request timed out.**\n*Please try again in a bit.*")

        elif isinstance(error.original, OSError):
            capture_exception(error.original)
            if error.original.errno == errno.ENOSPC:
                await ctx.send(
                    "**No space is left on the server!**\n"
                    + "*Please report this message in #support in the support server below!*\n"
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
            else:
                await ctx.send(
                    "**An unexpected OSError has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again.*\n"
                    + f"**Error code:** `{error.original.errno}`"
                )
                await ctx.send("https://discord.gg/fXxYyDJ")

        else:
            logger.info("uncaught command error")
            capture_exception(error.original)
            await ctx.send(
                "**An uncaught command error has occurred.**\n"
                + "*Please log this message in #support in the support server below, or try again.*\n"
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    else:
        logger.info("uncaught non-command")
        capture_exception(error)
        await ctx.send(
            "**An uncaught non-command error has occurred.**\n"
            + "*Please log this message in #support in the support server below, or try again.*\n"
        )
        await ctx.send("https://discord.gg/fXxYyDJ")
        raise error
