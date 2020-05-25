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

import datetime
import textwrap
import typing

import discord
import pandas as pd
from discord.ext import commands
from sentry_sdk import capture_exception

from bot.data import GenericError, database, logger
from bot.functions import CustomCooldown, send_leaderboard


class Score(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _server_total(self, ctx):
        logger.info("fetching server totals")
        channels = map(
            lambda x: x.decode("utf-8").split(":")[1],
            database.zrangebylex("channels:global", f"[{ctx.guild.id}", f"({ctx.guild.id}\xff")
        )
        pipe = database.pipeline() # use a pipeline to get all the scores
        for channel in channels:
            pipe.zscore("score:global", channel)
        scores = pipe.execute()
        return int(sum(scores))

    def _monthly_lb(self, ctx):
        logger.info("generating monthly leaderboard")
        today = datetime.datetime.now(datetime.timezone.utc).date()
        past_month = pd.date_range(today-datetime.timedelta(29), today).date
        pipe = database.pipeline()
        for day in past_month:
            pipe.zrevrangebyscore(f"daily.score:{day}", "+inf", "-inf", withscores=True)
        result = pipe.execute()
        total_scores = pd.Series(dtype="int64")
        for daily_score in result:
            daily_score = pd.Series({e[0]:e[1] for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), daily_score)})
            total_scores = total_scores.add(daily_score, fill_value=0)
        total_scores = total_scores.sort_values(ascending=False)
        return total_scores

    def _monthly_missed(self, ctx):
        logger.info("generating monthly missed bitds")
        today = datetime.datetime.now(datetime.timezone.utc).date()
        past_month = pd.date_range(today-datetime.timedelta(29), today).date
        pipe = database.pipeline()
        for day in past_month:
            pipe.zrevrangebyscore(f"daily.incorrect:{day}", "+inf", "-inf", withscores=True)
        result = pipe.execute()
        total_missed = pd.Series(dtype="int64")
        for daily_missed in result:
            daily_missed = pd.Series({e[0]:e[1] for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), daily_missed)})
            total_missed = total_missed.add(daily_missed, fill_value=0)
        total_missed = total_missed.sort_values(ascending=False)
        return total_missed

    # returns total number of correct answers so far
    @commands.command(
        brief="- Total correct answers in a channel or server",
        help="- Total correct answers in a channel or server. Defaults to channel.",
        usage="[total|server|t|s]")
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.channel))
    async def score(self, ctx, scope=""):
        logger.info("command: score")

        if scope in ("total", "server", "t", "s"):
            total_correct = self._server_total(ctx)
            await ctx.send(
                f"Wow, looks like a total of `{total_correct}` birds have been answered correctly in this **server**!\n" +
                "Good job everyone!"
            )
        else:
            total_correct = int(database.zscore("score:global", str(ctx.channel.id)))
            await ctx.send(
                f"Wow, looks like a total of `{total_correct}` birds have been answered correctly in this **channel**!\n" +
                "Good job everyone!"
            )

    # sends correct answers by a user
    @commands.command(
        brief="- How many correct answers given by a user",
        help="- Gives the amount of correct answers by a user.\n" +
        "Mention someone to get their score, don't mention anyone to get your score.",
        aliases=["us"]
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def userscore(self, ctx, *, user: typing.Optional[typing.Union[discord.Member, str]] = None):
        logger.info("command: userscore")

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
            user = f"<@{ctx.author.id}>"
            times = str(int(database.zscore("users:global", str(ctx.author.id))))

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="User Score:", value=f"{user} has answered correctly {times} times.")
        await ctx.send(embed=embed)

    # gives streak of a user
    @commands.command(help='- Gives your current/max streak', aliases=["streaks", "stk"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def streak(self, ctx):

        embed = discord.Embed(type="rich", colour=discord.Color.blurple(), title="**User Streaks**")
        embed.set_author(name="Bird ID - An Ornithology Bot")
        current_streak = f"You have answered `{int(database.zscore('streak:global', str(ctx.author.id)))}` in a row!"
        max_streak = f"Your max was `{int(database.zscore('streak.max:global', str(ctx.author.id)))}` in a row!"
        embed.add_field(name=f"**Current Streak**", value=current_streak, inline=False)
        embed.add_field(name=f"**Max Streak**", value=max_streak, inline=False)

        await ctx.send(embed=embed)

    # leaderboard - returns top 1-10 users
    @commands.command(
        brief="- Top scores",
        help="- Top scores, either global, server, or monthly.",
        usage="[global|g server|s month|monthly|m] [page]",
        aliases=["lb"]
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def leaderboard(self, ctx, scope="", page=1):
        logger.info("command: leaderboard")

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

        if not scope in ("global", "server", "month", "monthly", "m", "g", "s"):
            logger.info("invalid scope")
            await ctx.send(f"**{scope} is not a valid scope!**\n*Valid Scopes:* `global, server, month`")
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
        elif scope in ("month", "monthly", "m"):
            database_key = None
            scope = "Last 30 Days"
            monthly_scores = self._monthly_lb(ctx)
        else:
            database_key = "users:global"
            scope = "global"

        user_amount = (int(database.zcard(database_key)) if database_key is not None else monthly_scores.count())
        page = (page * 10) - 10

        if user_amount == 0:
            logger.info(f"no users in {database_key}")
            await ctx.send("There are no users in the database.")
            return

        if page > user_amount:
            page = user_amount - (user_amount % 10)

        users_per_page = 10
        leaderboard_list = (
            database.zrevrangebyscore(database_key, "+inf", "-inf", page, users_per_page, True)
            if database_key is not None
            else monthly_scores.iloc[page:page+users_per_page-1].items()
        )

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

        user_score = (
            database.zscore(database_key, str(ctx.author.id))
            if database_key is not None
            else monthly_scores.get(str(ctx.author.id))
        )

        if user_score is not None:
            if database_key is not None:
                placement = int(database.zrevrank(database_key, str(ctx.author.id))) + 1
                distance = (
                    int(database.zrevrange(database_key, placement - 2, placement - 2, True)[0][1]) -
                    int(user_score))
            else:
                placement = int(monthly_scores.rank(ascending=False)[str(ctx.author.id)])
                distance = int(monthly_scores.iloc[placement-2] - user_score)

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
        help="- Top incorrect birds, either global, server, personal, or monthly.",
        usage="[global|g server|s me|m month|monthly|mo] [page]",
        aliases=["m"]
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def missed(self, ctx, scope="", page=1):
        logger.info("command: missed")

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

        if not scope in ("global", "server", "me", "month", "monthly", "mo", "g", "s", "m"):
            logger.info("invalid scope")
            await ctx.send(f"**{scope} is not a valid scope!**\n*Valid Scopes:* `global, server, me, month`")
            return

        if scope in ("server", "s"):
            data = None
            if ctx.guild is not None:
                database_key = f"incorrect.server:{ctx.guild.id}"
                scope = "server"
            else:
                logger.info("dm context")
                await ctx.send("**Server scopes are not avaliable in DMs.**\n*Showing global leaderboard instead.*")
                scope = "global"
                database_key = "incorrect:global"
        elif scope in ("me", "m"):
            data = None
            database_key = f"incorrect.user:{ctx.author.id}"
            scope = "me"
        elif scope in ("month", "monthly", "mo"):
            data = self._monthly_missed(ctx)
            database_key = None
            scope = "Last 30 days"
        else:
            data = None
            database_key = "incorrect:global"
            scope = "global"

        await send_leaderboard(ctx, f"Top Missed Birds ({scope})", page, database_key, data)

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
                textwrap.dedent(
                    f"""\
                    **The bot does not have enough permissions to fully function.**
                    **Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`
                    *Please try again once the correct permissions are set.*
                    """
                )
            )
        elif isinstance(error, GenericError):
            if error.code == 192:
                #channel is ignored
                return
            elif error.code == 842:
                await ctx.send("**Sorry, you cannot use this command.**")
            elif error.code == 666:
                logger.info("GenericError 666")
            elif error.code == 201:
                logger.info("HTTP Error")
                capture_exception(error)
                await ctx.send("**An unexpected HTTP Error has occurred.**\n *Please try again.*")
            else:
                logger.info("uncaught generic error")
                capture_exception(error)
                await ctx.send(
                    "**An uncaught generic error has occurred.**\n" +
                    "*Please log this message in #support in the support server below, or try again.*\n" +
                    "**Error:** " + str(error)
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
                raise error
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
        elif isinstance(error, GenericError):
            if error.code == 192:
                #channel is ignored
                return
            elif error.code == 842:
                await ctx.send("**Sorry, you cannot use this command.**")
            elif error.code == 666:
                logger.info("GenericError 666")
            elif error.code == 201:
                logger.info("HTTP Error")
                capture_exception(error)
                await ctx.send("**An unexpected HTTP Error has occurred.**\n *Please try again.*")
            else:
                logger.info("uncaught generic error")
                capture_exception(error)
                await ctx.send(
                    "**An uncaught generic error has occurred.**\n" +
                    "*Please log this message in #support in the support server below, or try again.*\n" +
                    "**Error:** " + str(error)
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
                raise error
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
