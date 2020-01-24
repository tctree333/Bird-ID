# score.py | commands to show score related things
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

import typing

import discord
from discord.ext import commands
from sentry_sdk import capture_exception

from data.data import database, logger
from functions import channel_setup, user_setup

class Score(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # returns total number of correct answers so far
    @commands.command(help="- Total correct answers in a channel")
    @commands.cooldown(1, 8.0, type=commands.BucketType.channel)
    async def score(self, ctx):
        logger.info("command: score")

        await channel_setup(ctx)
        await user_setup(ctx)

        totalCorrect = int(database.zscore("score:global", str(ctx.channel.id)))
        await ctx.send(
            f"Wow, looks like a total of {totalCorrect} birds have been answered correctly in this channel! " +
            "Good job everyone!"
        )

    # sends correct answers by a user
    @commands.command(
        brief="- How many correct answers given by a user",
        help="- Gives the amount of correct answers by a user.\n" +
        "Mention someone to get their score, Don't mention anyone to get your score.",
        aliases=["us"]
    )
    @commands.cooldown(1, 5.0, type=commands.BucketType.user)
    async def userscore(self, ctx, *, user: typing.Optional[typing.Union[discord.Member, str]] = None):
        logger.info("command: userscore")

        await channel_setup(ctx)
        await user_setup(ctx)

        if user is not None:
            if isinstance(user, str):
                await ctx.send("Not a user!")
                return
            usera = user.id
            logger.info(usera)
            if database.zscore("users:global", str(usera)) is not None:
                times = str(int(database.zscore("users:global", str(usera))))
                user = f"<@{usera}>"
            else:
                await ctx.send("This user does not exist on our records!")
                return
        else:
            if database.zscore("users:global", str(ctx.author.id)) is not None:
                user = f"<@{ctx.author.id}>"
                times = str(int(database.zscore("users:global", str(ctx.author.id))))
            else:
                await ctx.send("You haven't used this bot yet! (except for this)")
                return

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="User Score:", value=f"{user} has answered correctly {times} times.")
        await ctx.send(embed=embed)

    # gives streak of a user
    @commands.command(help='- Gives your current/max streak', aliases=["streaks", "stk"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.user)
    async def streak(self, ctx):

        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple(), title="**User Streaks**")
        embed.set_author(name="Bird ID - An Ornithology Bot")
        current_streak = f"You have answered `{int(database.zscore('streak:global', str(ctx.author.id)))}` in a row!"
        max_streak = f"Your max was `{int(database.zscore('streak.max:global', str(ctx.author.id)))}` in a row!"
        embed.add_field(name=f"**Current Streak**", value=current_streak, inline=False)
        embed.add_field(name=f"**Max Streak**", value=max_streak, inline=False)

        await ctx.send(embed=embed)

    # leaderboard - returns top 1-10 users
    @commands.command(
        brief="- Top scores", help="- Top scores, scope is either global or server. (g, s)", aliases=["lb"]
    )
    @commands.cooldown(1, 5.0, type=commands.BucketType.user)
    async def leaderboard(self, ctx, scope="", page=1):
        logger.info("command: leaderboard")

        await channel_setup(ctx)
        await user_setup(ctx)

        try:
            page = int(scope)
        except ValueError:
            if scope == "":
                scope = "global"
            scope = scope.lower()
        else:
            scope = "global"

        logger.info(f"scope: {scope}")
        logger.info(f"page: {page}")

        if not scope in ("global", "server", "g", "s"):
            logger.info("invalid scope")
            await ctx.send(f"**{scope} is not a valid scope!**\n*Valid Scopes:* `global, server`")
            return

        if page < 1:
            logger.info("invalid page")
            await ctx.send("Not a valid number. Pick a positive integer!")
            return

        database_key = ""
        if scope in ("server", "s"):
            if ctx.guild is not None:
                database_key = f"users.server:{ctx.guild.id}"
                scope = "server"
            else:
                logger.info("dm context")
                await ctx.send("**Server scopes are not avaliable in DMs.**\n*Showing global leaderboard instead.*")
                scope = "global"
                database_key = "users:global"
        else:
            database_key = "users:global"
            scope = "global"

        user_amount = int(database.zcard(database_key))
        page = (page * 10) - 10

        if user_amount == 0:
            logger.info(f"no users in {database_key}")
            await ctx.send("There are no users in the database.")
            return

        if page > user_amount:
            page = user_amount - (user_amount % 10)

        leaderboard_list = database.zrevrangebyscore(database_key, "+inf", "-inf", page, 10, True)
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        leaderboard = ""

        for i, stats in enumerate(leaderboard_list):
            if ctx.guild is not None:
                user = ctx.guild.get_member(int(stats[0]))
            else:
                user = None

            if user is None:
                user = self.bot.get_user(int(stats[0]))
                if user is None:
                    user = "**Deleted**"
                else:
                    user = f"**{user.name}#{user.discriminator}**"
            else:
                user = f"**{user.name}#{user.discriminator}** ({user.mention})"

            leaderboard += f"{i+1+page}. {user} - {int(stats[1])}\n"

        embed.add_field(name=f"Leaderboard ({scope})", value=leaderboard, inline=False)

        if database.zscore(database_key, str(ctx.author.id)) is not None:
            placement = int(database.zrevrank(database_key, str(ctx.author.id))) + 1
            distance = (
                int(database.zrevrange(database_key, placement - 2, placement - 2, True)[0][1]) -
                int(database.zscore(database_key, str(ctx.author.id)))
            )
            if placement == 1:
                embed.add_field(
                    name="You:",
                    value=f"You are #{placement} on the leaderboard.\nYou are in first place.",
                    inline=False
                )
            elif distance == 0:
                embed.add_field(
                    name="You:",
                    value=f"You are #{placement} on the leaderboard.\nYou are tied with #{placement-1}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="You:",
                    value=f"You are #{placement} on the leaderboard.\nYou are {distance} away from #{placement-1}",
                    inline=False
                )
        else:
            embed.add_field(name="You:", value="You haven't answered any correctly.")

        await ctx.send(embed=embed)

    # missed - returns top 1-10 missed birds
    @commands.command(
        brief="- Top incorrect birds",
        help="- Top incorrect birds, scope is either global, server, or me. (g, s, m)",
        aliases=["m"]
    )
    @commands.cooldown(1, 5.0, type=commands.BucketType.user)
    async def missed(self, ctx, scope="", page=1):
        logger.info("command: missed")

        await channel_setup(ctx)
        await user_setup(ctx)

        try:
            page = int(scope)
        except ValueError:
            if scope == "":
                scope = "global"
                scope = scope.lower()
        else:
            scope = "global"

        logger.info(f"scope: {scope}")
        logger.info(f"page: {page}")

        if not scope in ("global", "server", "me", "g", "s", "m"):
            logger.info("invalid scope")
            await ctx.send(f"**{scope} is not a valid scope!**\n*Valid Scopes:* `global, server, me`")
            return

        if page < 1:
            logger.info("invalid page")
            await ctx.send("Not a valid number. Pick a positive integer!")
            return

        database_key = ""
        if scope in ("server", "s"):
            if ctx.guild is not None:
                database_key = f"incorrect.server:{ctx.guild.id}"
                scope = "server"
            else:
                logger.info("dm context")
                await ctx.send("**Server scopes are not avaliable in DMs.**\n*Showing global leaderboard instead.*")
                scope = "global"
                database_key = "incorrect:global"
        elif scope in ("me", "m"):
            database_key = f"incorrect.user:{ctx.author.id}"
            scope = "me"
        else:
            database_key = "incorrect:global"
            scope = "global"

        user_amount = int(database.zcard(database_key))
        page = (page * 10) - 10

        if user_amount == 0:
            logger.info(f"no users in {database_key}")
            await ctx.send("There are no birds in the database.")
            return

        if page > user_amount:
            page = user_amount - (user_amount % 10)

        leaderboard_list = database.zrevrangebyscore(database_key, "+inf", "-inf", page, 10, True)
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        leaderboard = ""

        for i, stats in enumerate(leaderboard_list):
            leaderboard += f"{i+1+page}. **{stats[0].decode('utf-8')}** - {int(stats[1])}\n"
        embed.add_field(name=f"Top Missed Birds ({scope})", value=leaderboard, inline=False)

        await ctx.send(embed=embed)

    # Command-specific error checking
    @leaderboard.error
    async def leader_error(self, ctx, error):
        logger.info("leaderboard error")
        if isinstance(error, commands.BadArgument):
            await ctx.send('Not an integer!')
        elif isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " + str(round(error.retry_after)) + " s.", delete_after=5.0)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                f"""**The bot does not have enough permissions to fully function.**
**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`
*Please try again once the correct permissions are set.*"""
            )
        else:
            capture_exception(error)
            await ctx.send(
                "**An uncaught leaderboard error has occurred.**\n" +
                "*Please log this message in #support in the support server below, or try again.*\n" + "**Error:** " +
                str(error)
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    @missed.error
    async def missed_error(self, ctx, error):
        logger.info("missed error")
        if isinstance(error, commands.BadArgument):
            await ctx.send('Not an integer!')
        elif isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " + str(round(error.retry_after)) + " s.", delete_after=5.0)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "**The bot does not have enough permissions to fully function.**\n" +
                f"**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`\n" +
                "*Please try again once the correct permissions are set.*"
            )
        else:
            capture_exception(error)
            await ctx.send(
                "**An uncaught missed birds error has occurred.**\n"
                "*Please log this message in #support in the support server below, or try again.*\n"
                "**Error:** " + str(error)
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

def setup(bot):
    bot.add_cog(Score(bot))
