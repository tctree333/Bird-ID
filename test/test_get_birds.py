import asyncio

import pytest

import discord_mock as mock
from bot.cogs import get_birds
from bot.data import database
from bot.functions import channel_setup, user_setup


class TestBirds:
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
        self.cog = get_birds.Birds(self.bot)
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

    ### Bird Command Tests
    def test_bird_dm_1(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: good",
            "*Taxons*: `None`",
            "*Detected State*: `None`",
        ):
            assert i in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_dm_2(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="bw female"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: good",
            "sex: female",
            "bw: yes",
            "*Taxons*: `None`",
            "*Detected State*: `None`",
        ):
            assert i in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_dm_3(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="passeriformes yolo bw juvenile"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: good",
            "age: juvenile",
            "bw: yes",
            "*Taxons*: `passeriformes`",
            "*Detected State*: `None`",
        ):
            assert i in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_dm_4(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="13435 troglodytidae f"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: good",
            "sex: female",
            "*Taxons*: `troglodytidae`",
            "*Detected State*: `None`",
        ):
            assert i in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_state_na(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="na"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: good",
            "*Taxons*: `None`",
            "*Detected State*: `NA`",
        ):
            assert i in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_other_options(self):
        self.setup(guild=True)
        database.hset(f"channel:{self.ctx.channel.id}", "bird", "Canada Goose")
        database.hset(f"channel:{self.ctx.channel.id}", "answered", "0")

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="small egg nest"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "tags: eggs",
            "tags: nest",
            "small: yes",
            "quality: good",
        ):
            assert i in self.ctx.messages[2].content
        for i in ("Taxons","Detected State"):
            assert i not in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content

    def test_bird_quality_option(self):
        self.setup(guild=True)

        coroutine = self.cog.bird.callback(
            self.cog, self.ctx, args_str="q1"
        )  # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        for i in (
            "Active Filters",
            "quality: terrible",
        ):
            assert i in self.ctx.messages[2].content
        for i in ("quality: excellent","quality: average", "quality: good"):
            assert i not in self.ctx.messages[2].content
        for i in (
            "Here you go!",
            "Use `b!bird` again",
            "b!skip",
            "Use `b!check guess` to check your answer.",
        ):
            assert i in self.ctx.messages[4].content
