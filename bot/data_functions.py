# data_functions.py | function definitions for database related things
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

import datetime
import string

from bot.data import database, logger, states


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
        channel_id = "web"
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
