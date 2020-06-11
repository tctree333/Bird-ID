# functions.py | function definitions
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

import datetime
import difflib
import itertools
import os
import pickle
import random
import string

import discord
from discord.ext import commands

from bot.data import (GenericError, birdList, birdListMaster, database, logger,
                      sciListMaster, songBirds, states, taxons)


async def channel_setup(ctx):
    """Sets up a new discord channel.

    `ctx` - Discord context object
    """
    logger.info("checking channel setup")
    if database.exists(f"channel:{ctx.channel.id}"):
        logger.info("channel data ok")
    else:
        database.hset(
            f"channel:{ctx.channel.id}",
            mapping={"bird": "", "answered": 1, "prevB": "", "prevJ": 20, "prevK": 20,},
        )
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        logger.info("channel data added")
        await ctx.send("Ok, setup! I'm all ready to use!")

    if database.zscore("score:global", str(ctx.channel.id)) is not None:
        logger.info("channel score ok")
    else:
        database.zadd("score:global", {str(ctx.channel.id): 0})
        logger.info("channel score added")

    if ctx.guild is not None:
        if (
            database.zadd("channels:global", {f"{ctx.guild.id}:{ctx.channel.id}": 0})
            is not 0
        ):
            logger.info("server lookup ok")
        else:
            logger.info("server lookup added")


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
    if database.zscore("users:global", user_id) is not None:
        logger.info("user global ok")
    else:
        database.zadd("users:global", {user_id: 0})
        logger.info("user global added")
        if ctx is not None:
            await ctx.send("Welcome <@" + user_id + ">!")

    date = str(datetime.datetime.now(datetime.timezone.utc).date())
    if database.zscore(f"daily.score:{date}", user_id) is not None:
        logger.info("user daily ok")
    else:
        database.zadd(f"daily.score:{date}", {user_id: 0})
        logger.info("user daily added")

    # Add streak
    if (database.zscore("streak:global", user_id) is not None) and (
        database.zscore("streak.max:global", user_id) is not None
    ):
        logger.info("user streak in already")
    else:
        database.zadd("streak:global", {user_id: 0})
        database.zadd("streak.max:global", {user_id: 0})
        logger.info("added streak")

    if guild is not None:
        logger.info("no dm")
        if (
            database.zscore(f"users.server:{ctx.guild.id}", str(ctx.author.id))
            is not None
        ):
            server_score = database.zscore(
                f"users.server:{ctx.guild.id}", str(ctx.author.id)
            )
            global_score = database.zscore("users:global", str(ctx.author.id))
            if server_score == global_score:
                logger.info("user server ok")
            else:
                database.zadd(
                    f"users.server:{ctx.guild.id}", {str(ctx.author.id): global_score}
                )
        else:
            score = int(database.zscore("users:global", str(ctx.author.id)))
            database.zadd(f"users.server:{ctx.guild.id}", {str(ctx.author.id): score})
            logger.info("user server added")

        role_ids = [role.id for role in ctx.author.roles]
        role_names = [role.name.lower() for role in ctx.author.roles]
        if set(role_names).intersection(
            set(states["CUSTOM"]["aliases"])
        ) and not database.exists(f"custom.list:{ctx.author.id}"):
            index = role_names.index(states["CUSTOM"]["aliases"][0].lower())
            role = ctx.guild.get_role(role_ids[index])
            await ctx.author.remove_roles(
                role, reason="Remove state role for bird list"
            )
    else:
        logger.info("dm context")


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
        logger.info("bird user ok")
    else:
        database.zadd(f"incorrect.user:{user_id}", {string.capwords(bird): 0})
        logger.info("bird user added")

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


def error_skip(ctx):
    """Skips the current bird.

    Passed to send_bird() as on_error to skip the bird when an error occurs to prevent error loops.
    """
    logger.info("ok")
    database.hset(f"channel:{ctx.channel.id}", "bird", "")
    database.hset(f"channel:{ctx.channel.id}", "answered", "1")


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


async def send_leaderboard(ctx, title, page, database_key=None, data=None):
    logger.info("building/sending leaderboard")

    if database_key is None and data is None:
        raise GenericError("database_key and data are both NoneType", 990)
    elif database_key is not None and data is not None:
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

    items_per_page = 10
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


def build_id_list(user_id=None, taxon=(), roles=(), state=(), media="images") -> list:
    """Generates an ID list based on given arguments

    - `user_id`: User ID of custom list
    - `taxon`: taxon string/list
    - `roles`: role list
    - `state`: state string/list
    - `media`: image/song
    """
    logger.info("building id list")
    if isinstance(taxon, str):
        taxon = taxon.split(" ")
    if isinstance(state, str):
        state = state.split(" ")

    state_roles = state + roles
    if media in ("songs", "song", "s", "a"):
        state_list = "songBirds"
        default = songBirds
    else:
        state_list = "birdList"
        default = birdList

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
        birds_in_taxon = set(itertools.chain.from_iterable(taxons[o] for o in taxon))
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

    elif str(ctx.command) in ("bird", "song", "goatsucker"):
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
                    skip_cmd="skipgoat",
                    check_cmd="checkgoat",
                    hint_cmd="hintgoat",
                )
            )
        elif str(ctx.command) == "bird":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="song",
                    new_cmd="song",
                    skip_cmd="skipsong",
                    check_cmd="checksong",
                    hint_cmd="hintsong",
                )
            )

        file_obj = discord.File(path, filename=f"bird.{path.split('.')[-1]}")
        await ctx.send(file=file_obj)

    elif str(ctx.command) in ("check", "checkgoat", "checksong"):
        args = ctx.message.content.split(" ")[1:]
        matches = difflib.get_close_matches(
            " ".join(args), birdListMaster + sciListMaster, n=1
        )
        if "drone" in args:
            await ctx.send(
                "SHHHHHH! Birds are **NOT** government drones! You'll blow our cover, and we'll need to get rid of you."
            )
        elif matches:
            await ctx.send("Correct! Good job!")
            await ctx.send(embed=video_embed())
        else:
            await ctx.send("Sorry, the bird was actually **definitely a real bird.**")
            await ctx.send(embed=video_embed())

    elif str(ctx.command) in ("skip", "skipgoat", "skipsong"):
        await ctx.send("Ok, skipping **definitely a real bird.**")
        await ctx.send(embed=video_embed())

    elif str(ctx.command) in ("hint", "hintgoat", "hintsong"):
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


async def backup_all():
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
    try:
        os.mkdir("backups")
        logger.info("Created backups directory")
    except FileExistsError:
        logger.info("Backups directory exists")
    with open("backups/dump.dump", "wb") as f:
        with open("backups/keys.txt", "w") as k:
            for item, key in dump:
                pickle.dump(item, f)
                k.write(f"{key}\n")
    logger.info("Backup Finished")


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
        rate = 1
        dm_per = per / 2
        race_per = 0.5
        self.disable = disable
        self.default_mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)
        self.dm_mapping = commands.CooldownMapping.from_cooldown(rate, dm_per, bucket)
        self.race_mapping = commands.CooldownMapping.from_cooldown(
            rate, race_per, bucket
        )

    def __call__(self, ctx: commands.Context):
        if not self.disable and ctx.guild is None:
            # halve cooldown in DMs
            bucket = self.dm_mapping.get_bucket(ctx.message)

        elif ctx.command.name.startswith("check") and ctx.channel.name.startswith(
            "racing"
        ):
            # tiny check cooldown in racing channels
            bucket = self.race_mapping.get_bucket(ctx.message)

        else:
            bucket = self.default_mapping.get_bucket(ctx.message)

        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(bucket, retry_after)
        return True
