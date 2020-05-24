import asyncio

import discord
import pytest

import discord_mock as mock
from bot.cogs import score
from bot.data import database


class TestScore:
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
        self.cog = score.Score(self.bot)
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


    ### Score Command Tests
    def test_score_none(self):
        self.setup(guild=True)

        coroutine = self.cog.score.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "Wow, looks like a total of `0` birds have been answered correctly in this **channel**!\nGood job everyone!"

    def test_with_score(self):
        self.setup(guild=True)
        database.zincrby("score:global", 20, str(self.ctx.channel.id))

        coroutine = self.cog.score.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "Wow, looks like a total of `20` birds have been answered correctly in this **channel**!\nGood job everyone!"

    ### Userscore Command Tests
    def test_userscore_self(self):
        self.setup(guild=True)

        coroutine = self.cog.userscore.callback(self.cog, self.ctx) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].embed.type == "rich"
        assert self.ctx.messages[2].embed.colour == discord.Color.blurple()
        assert self.ctx.messages[2].embed.author.name == "Bird ID - An Ornithology Bot"
        assert self.ctx.messages[2].embed.fields[0].name == "User Score:"
        assert self.ctx.messages[2].embed.fields[0].value == f"<@{self.ctx.author.id}> has answered correctly 0 times."

    def test_userscore_bad_input(self):
        self.setup(guild=True)
        test_input = "banana"
        
        coroutine = self.cog.userscore.callback(self.cog, self.ctx, user=test_input) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "Not a user!"

    def test_userscore_user_none(self):
        self.setup(guild=True)
        test_input = "banana"
        self.ctx.guild.add_member(test_input)

        coroutine = self.cog.userscore.callback(self.cog, self.ctx, user=self.ctx.guild.members[0]) # pylint: disable=no-member
        assert asyncio.run(coroutine) is None
        assert self.ctx.messages[2].content == "This user does not exist on our records!"
