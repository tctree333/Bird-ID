import asyncio

import pytest

import discord_mock as mock
from bot.cogs import skip
from bot.data import database


class TestSkip:
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
        self.bot = mock.Bot()
        self.cog = skip.Skip(self.bot)
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

    ### Skip Command Tests
    def test_skip_nobird_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.skip.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_skip_bird_dm(self):
        self.setup(guild=True)
        test_word = "Canada Goose"
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)

        coroutine = self.cog.skip.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Ok, skipping {test_word.lower()}"


    ### Skipgoat Command Tests
    def test_skipgoat_nobird_dm(self):
        self.setup(guild=True)

        coroutine = self.cog.skipgoat.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_skipgoat_bird_dm(self):
        self.setup(guild=True)
        test_word = "Common Pauraque"
        database.hset(f"channel:{self.ctx.channel.id}", "goatsucker", test_word)

        coroutine = self.cog.skipgoat.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Ok, skipping {test_word.lower()}"


    ### Skipsong Command Tests
    def test_skipsong_nobird_dm(self):
        self.setup(guild=True)

        coroutine = self.cog.skipsong.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_skipsong_bird_dm(self):
        self.setup(guild=True)
        test_word = "Northern Cardinal"
        database.hset(f"channel:{self.ctx.channel.id}", "sBird", test_word)

        coroutine = self.cog.skipsong.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Ok, skipping {test_word.lower()}"
