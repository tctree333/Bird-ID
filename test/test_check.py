import asyncio

import pytest

import discord_mock as mock
from bot.cogs import check
from bot.data import database
from bot.functions import channel_setup, user_setup


class TestCheck:
    @pytest.yield_fixture(autouse=True)
    def test_suite_cleanup_thing(self):
        yield
        database.delete(f"channel:{self.ctx.channel.id}")
        database.zrem("score:global", str(self.ctx.channel.id))

        database.zrem("users:global", str(self.ctx.author.id))
        database.zrem("streak:global", str(self.ctx.author.id))
        database.zrem("streak.max:global", str(self.ctx.author.id))
        database.delete(f"incorrect.user:{self.ctx.author.id}")

        if self.ctx.guild is not None:
            database.delete(f"users.server:{self.ctx.guild.id}")
            database.delete(f"incorrect.server:{self.ctx.guild.id}")

    def setup(self, guild=False):
        # pylint: disable=attribute-defined-outside-init
        self.bot = mock.Bot()
        self.cog = check.Check(self.bot)
        self.ctx = mock.Context(self.bot)

        if guild:
            self.ctx.set_guild()

        database.delete(f"channel:{self.ctx.channel.id}")
        database.zrem("score:global", str(self.ctx.channel.id))

        database.zrem("users:global", str(self.ctx.author.id))
        database.zrem("streak:global", str(self.ctx.author.id))
        database.zrem("streak.max:global", str(self.ctx.author.id))

        if self.ctx.guild is not None:
            database.delete(f"users.server:{self.ctx.guild.id}")

        asyncio.run(channel_setup(self.ctx))
        asyncio.run(user_setup(self.ctx))

    ### Check Command Tests
    def test_check_nobird_dm(self):
        self.setup(guild=True)

        coroutine = self.cog.check.callback(  # pylint: disable=no-member
            self.cog, self.ctx, arg="hehehe"
        )
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You must ask for a bird first!"

    def test_check_bird_dm_1(self):
        self.setup(guild=True)
        test_word = "Canada Goose"
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)

        coroutine = self.cog.check.callback(  # pylint: disable=no-member
            self.cog, self.ctx, arg=test_word
        )
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "Correct! Good job!"

    def test_check_bird_dm_2(self):
        self.setup(guild=True)
        test_word = "Canada Goose"
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)

        coroutine = self.cog.check.callback(  # pylint: disable=no-member
            self.cog, self.ctx, arg=test_word * 2
        )
        assert asyncio.run(coroutine) is None
        assert (
            self.ctx.messages[2].content
            == f"Sorry, the bird was actually {test_word.lower()}."
        )
