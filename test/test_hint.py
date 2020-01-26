import asyncio
import os
import sys

import pytest

from bot.cogs import hint
from bot.data import database
import discord_mock as mock


class TestHint:
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
        self.cog = hint.Hint(self.bot)
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

    ### Hint Command Tests
    def test_hint_nobird_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.hint.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_hint_bird_dm(self):
        test_word = "banana_test"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "bird", test_word)
        coroutine = self.cog.hint.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"The first letter is {test_word[0]}"


    ### Hintgoat Command Tests
    def test_hintgoat_nobird_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.hintgoat.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_hintgoat_bird_dm(self):
        test_word = "banana_test"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "goatsucker", test_word)
        coroutine = self.cog.hintgoat.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"The first letter is {test_word[0]}"


    ### Hintsong Command Tests
    def test_hintsong_nobird_dm(self):
        self.setup(guild=True)
        coroutine = self.cog.hintsong.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "You need to ask for a bird first!"

    def test_hintsong_bird_dm(self):
        test_word = "banana_test"

        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "sBird", test_word)
        coroutine = self.cog.hintsong.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[1].content == f"The first letter is {test_word[0]}"
