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
import datetime
import difflib
import functools
import hashlib
import itertools
import os
import pickle
import random
import string

import chardet
import discord
from discord.ext import commands

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


def cache(func=None, pre=None, local=True):
    """Cache decorator based on functools.lru_cache.

    This is not a very good cache, but it "works" for our
    purposes.

    This (optionally) caches items into a Redis database
    (bot.data.database). It does not have a max_size but sets
    key expiration to 7 days. Items are pickled before storing
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
                f"cache.{func.__name__}:{key}", pickled, ex=604800
            )  # 60*60*24*7

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
            _cache.pop(random.choice(tuple(_cache)), 0)

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
        return functools.update_wrapper(wrapped, func)

    if func:
        return wrapper(func)
    return wrapper


async def channel_setup(ctx):
    """Sets up a new discord channel.

    `ctx` - Discord context object
    """
    logger.info("checking channel setup")
    if not database.exists(f"channel:{ctx.channel.id}"):
        database.hset(
            f"channel:{ctx.channel.id}",
            mapping={"bird": "", "answered": 1, "prevB": "", "prevJ": 20},
        )
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        logger.info("channel data added")
        await ctx.send("Ok, setup! I'm all ready to use!")

    if database.zscore("score:global", str(ctx.channel.id)) is None:
        database.zadd("score:global", {str(ctx.channel.id): 0})
        logger.info("channel score added")

    if ctx.guild is not None:
        database.zadd("channels:global", {f"{ctx.guild.id}:{ctx.channel.id}": 0})


async def user_setup(ctx):
    """Sets up a new discord user for score tracking.

    `ctx` - Discord context object or user id
    """
    if isinstance(ctx, (str, int)):
        user_id = str(ctx)
        guild = None
        ctx = None
    else:
        user_id = str(ctx.author.id)
        guild = ctx.guild

    logger.info("checking user data")
    if database.zscore("users:global", user_id) is None:
        database.zadd("users:global", {user_id: 0})
        logger.info("user global added")
        if ctx is not None:
            await ctx.send("Welcome <@" + user_id + ">!")

    date = str(datetime.datetime.now(datetime.timezone.utc).date())
    if database.zscore(f"daily.score:{date}", user_id) is None:
        database.zadd(f"daily.score:{date}", {user_id: 0})
        logger.info("user daily added")

    # Add streak
    if (database.zscore("streak:global", user_id) is None) or (
        database.zscore("streak.max:global", user_id) is None
    ):
        database.zadd("streak:global", {user_id: 0})
        database.zadd("streak.max:global", {user_id: 0})
        logger.info("added streak")

    if guild is not None:
        global_score = database.zscore("users:global", str(ctx.author.id))
        database.zadd(
            f"users.server:{ctx.guild.id}", {str(ctx.author.id): global_score}
        )
        logger.info("synced scores")

        if not database.exists(f"custom.list:{ctx.author.id}"):
            role_ids = [role.id for role in ctx.author.roles]
            role_names = [role.name.lower() for role in ctx.author.roles]
            if set(role_names).intersection(set(states["CUSTOM"]["aliases"])):
                index = role_names.index(states["CUSTOM"]["aliases"][0].lower())
                role = ctx.guild.get_role(role_ids[index])
                await ctx.author.remove_roles(
                    role, reason="Remove state role for bird list"
                )
                logger.info("synced roles")


def bird_setup(ctx, bird: str):
    """Sets up a new bird for incorrect tracking.

    `ctx` - Discord context object or user id\n
    `bird` - bird to setup
    """
    if isinstance(ctx, (str, int)):
        user_id = ctx
        guild = None
    else:
        user_id = ctx.author.id
        guild = ctx.guild

    logger.info("checking bird data")
    if database.zscore("incorrect:global", string.capwords(bird)) is not None:
        logger.info("bird global ok")
    else:
        database.zadd("incorrect:global", {string.capwords(bird): 0})
        logger.info("bird global added")

    if database.zscore(f"incorrect.user:{user_id}", string.capwords(bird)) is not None:
        logger.info("incorrect bird user ok")
    else:
        database.zadd(f"incorrect.user:{user_id}", {string.capwords(bird): 0})
        logger.info("incorrect bird user added")

    if database.zscore(f"correct.user:{user_id}", string.capwords(bird)) is not None:
        logger.info("correct bird user ok")
    else:
        database.zadd(f"correct.user:{user_id}", {string.capwords(bird): 0})
        logger.info("correct bird user added")

    date = str(datetime.datetime.now(datetime.timezone.utc).date())
    if database.zscore(f"daily.incorrect:{date}", string.capwords(bird)) is not None:
        logger.info("bird daily ok")
    else:
        database.zadd(f"daily.incorrect:{date}", {string.capwords(bird): 0})
        logger.info("bird daily added")

    if database.zscore("frequency.bird:global", string.capwords(bird)) is not None:
        logger.info("bird freq global ok")
    else:
        database.zadd("frequency.bird:global", {string.capwords(bird): 0})
        logger.info("bird freq global added")

    if guild is not None:
        logger.info("no dm")
        if (
            database.zscore(f"incorrect.server:{ctx.guild.id}", string.capwords(bird))
            is not None
        ):
            logger.info("bird server ok")
        else:
            database.zadd(
                f"incorrect.server:{ctx.guild.id}", {string.capwords(bird): 0}
            )
            logger.info("bird server added")
    else:
        logger.info("dm context")

    if database.exists(f"session.data:{user_id}"):
        logger.info("session in session")
        if (
            database.zscore(f"session.incorrect:{user_id}", string.capwords(bird))
            is not None
        ):
            logger.info("bird session ok")
        else:
            database.zadd(f"session.incorrect:{user_id}", {string.capwords(bird): 0})
            logger.info("bird session added")
    else:
        logger.info("no session")


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
    leaderboard = ""

    for i, stats in enumerate(leaderboard_list):
        leaderboard += f"{i+1+page}. **{stats[0]}** - {int(stats[1])}\n"
    embed.add_field(name=title, value=leaderboard, inline=False)

    await ctx.send(embed=embed)


def build_id_list(
    user_id=None, taxon=None, roles=None, state=None, media="images"
) -> list:
    """Generates an ID list based on given arguments

    - `user_id`: User ID of custom list
    - `taxon`: taxon string/list
    - `roles`: role list
    - `state`: state string/list
    - `media`: images/songs
    """
    logger.info("building id list")
    if isinstance(taxon, str):
        taxon = taxon.split(" ")
    if isinstance(state, str):
        state = state.split(" ")

    state_roles = (state if state else []) + (roles if roles else [])
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


def session_increment(ctx, item: str, amount: int):
    """Increments the value of a database hash field by `amount`.

    `ctx` - Discord context object or user id\n
    `item` - hash field to increment (see data.py for details,
    possible values include correct, incorrect, total)\n
    `amount` (int) - amount to increment by, usually 1
    """
    if isinstance(ctx, (str, int)):
        user_id = ctx
    else:
        user_id = ctx.author.id

    if database.exists(f"session.data:{user_id}"):
        logger.info("session active")
        logger.info(f"incrementing {item} by {amount}")
        value = int(database.hget(f"session.data:{user_id}", item))
        value += int(amount)
        database.hset(f"session.data:{user_id}", item, str(value))
    else:
        logger.info("session not active")


def incorrect_increment(ctx, bird: str, amount: int):
    """Increments the value of an incorrect bird by `amount`.

    `ctx` - Discord context object or user id\n
    `bird` - bird that was incorrect\n
    `amount` (int) - amount to increment by, usually 1
    """
    if isinstance(ctx, (str, int)):
        user_id = ctx
        guild = None
    else:
        user_id = ctx.author.id
        guild = ctx.guild

    logger.info(f"incrementing incorrect {bird} by {amount}")
    date = str(datetime.datetime.now(datetime.timezone.utc).date())
    database.zincrby("incorrect:global", amount, string.capwords(str(bird)))
    database.zincrby(f"incorrect.user:{user_id}", amount, string.capwords(str(bird)))
    database.zincrby(f"daily.incorrect:{date}", amount, string.capwords(str(bird)))
    if guild is not None:
        logger.info("no dm")
        database.zincrby(
            f"incorrect.server:{ctx.guild.id}", amount, string.capwords(str(bird))
        )
    else:
        logger.info("dm context")
    if database.exists(f"session.data:{user_id}"):
        logger.info("session in session")
        database.zincrby(
            f"session.incorrect:{user_id}", amount, string.capwords(str(bird))
        )
    else:
        logger.info("no session")


def score_increment(ctx, amount: int):
    """Increments the score of a user by `amount`.

    `ctx` - Discord context object\n
    `amount` (int) - amount to increment by, usually 1
    """
    if isinstance(ctx, (str, int)):
        user_id = str(ctx)
        guild = None
        channel_id = ""
    else:
        user_id = str(ctx.author.id)
        guild = ctx.guild
        channel_id = str(ctx.channel.id)

    logger.info(f"incrementing score by {amount}")
    date = str(datetime.datetime.now(datetime.timezone.utc).date())
    database.zincrby("score:global", amount, channel_id)
    database.zincrby("users:global", amount, user_id)
    database.zincrby(f"daily.score:{date}", amount, user_id)
    if guild is not None:
        logger.info("no dm")
        database.zincrby(f"users.server:{ctx.guild.id}", amount, user_id)
        if database.exists(f"race.data:{ctx.channel.id}"):
            logger.info("race in session")
            database.zincrby(f"race.scores:{ctx.channel.id}", amount, user_id)
    else:
        logger.info("dm context")


def streak_increment(ctx, amount: int):
    """Increments the streak of a user by `amount`.

    `ctx` - Discord context object or user id\n
    `amount` (int) - amount to increment by, usually 1.
    If amount is None, the streak is ended.
    """
    if isinstance(ctx, (str, int)):
        user_id = str(ctx)
    else:
        user_id = str(ctx.author.id)

    if amount is not None:
        # increment streak and update max
        database.zincrby("streak:global", amount, user_id)
        if database.zscore("streak:global", user_id) > database.zscore(
            "streak.max:global", user_id
        ):
            database.zadd(
                "streak.max:global",
                {user_id: database.zscore("streak:global", user_id)},
            )
    else:
        database.zadd("streak:global", {user_id: 0})


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
            await ctx.send("Correct! Good job! The bird was **definitely a real bird**.")
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
