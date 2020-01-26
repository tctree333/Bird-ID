import asyncio
import os
import sys

import pytest

sys.path.append(os.getcwd())
from cogs import check
from data.data import database
import discord_mock as mock


class TestCheck:
    @pytest.yield_fixture(autouse=True)
    def test_suite_cleanup_thing(self):
        yield
        database.delete(f"channel:{self.ctx.channel.id}")
        database.zrem("score:global", str(self.ctx.channel.id))

        database.zrem("users:global", str(self.ctx.author.id))
        database.zrem("streak:global", str(self.ctx.author.id))
        database.zrem("streak.max:global", str(self.ctx.author.id))

        if self.ctx.guild is not None:
            database.delete(f"users.server:{self.ctx.guild.id}")

    def setup(self, guild=False):
        self.bot = mock.Bot()
        self.cog = check.Check(self.bot)
        self.ctx = mock.Context()

        if guild:
            self.ctx.set_guild()

        database.delete(f"channel:{self.ctx.channel.id}")
        database.zrem("score:global", str(self.ctx.channel.id))

        database.zrem("users:global", str(self.ctx.author.id))
        database.zrem("streak:global", str(self.ctx.author.id))
        database.zrem("streak.max:global", str(self.ctx.author.id))

        if self.ctx.guild is not None:
            database.delete(f"users.server:{self.ctx.guild.id}")

    ### Check Command Tests

    def test_check_nobird_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.check.callback(self.cog, self.ctx, arg="hehehe") # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You must ask for a bird first!"

    def test_check_bird_dm(self):
        test_word = "Canada Goose"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)
        coroutine = self.cog.check.callback(self.cog, self.ctx, arg=test_word) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == "Correct! Good job!"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)
        coroutine = self.cog.check.callback(self.cog, self.ctx, arg=test_word*2) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Sorry, the bird was actually {test_word.lower()}."

    def test_check_nosong_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.checksong.callback(self.cog, self.ctx, arg="hehehe") # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You must ask for a bird call first!"

    def test_check_song_dm(self):
        test_word = "Northern Cardinal"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "sBird", test_word)
        coroutine = self.cog.checksong.callback(self.cog, self.ctx, arg=test_word) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == "Correct! Good job!"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "sBird", test_word)
        coroutine = self.cog.checksong.callback(self.cog, self.ctx, arg=test_word*2) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Sorry, the bird was actually {test_word.lower()}."

    def test_check_nogoat_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.checkgoat.callback(self.cog, self.ctx, arg="hehehe") # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You must ask for a bird first!"

    def test_check_goat_dm(self):
        test_word = "Common Pauraque"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "goatsucker", test_word)
        coroutine = self.cog.checkgoat.callback(self.cog, self.ctx, arg=test_word) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == "Correct! Good job!"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "goatsucker", test_word)
        coroutine = self.cog.checkgoat.callback(self.cog, self.ctx, arg=test_word*2) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"Sorry, the bird was actually {test_word.lower()}."
