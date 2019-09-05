# score.py | commands to show score related things
# Copyright (C) 2019  EraserBird, person_v1.32

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

from data.data import database
from functions import channel_setup, user_setup


class Score(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # returns total number of correct answers so far
    @commands.command(help="- Total correct answers in a channel")
    @commands.cooldown(1, 8.0, type=commands.BucketType.channel)
    async def score(self, ctx):
        print("score")

        await channel_setup(ctx)
        await user_setup(ctx)

        totalCorrect = int(database.lindex(str(ctx.channel.id), 4))
        await ctx.send(
            f"Wow, looks like a total of {str(totalCorrect)} birds have been answered correctly in this channel! Good job everyone!"
        )

    # sends correct answers by a user
    @commands.command(brief="- How many correct answers given by a user",
                      help="""- How many correct answers given by a user.
                            Mention someone to get their score.
                            Don't mention anyone to get your score.""",
                      aliases=["us"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def userscore(
            self,
            ctx,
            *,
            user: typing.Optional[typing.Union[discord.Member, str]] = None):
        print("user score")

        await channel_setup(ctx)
        await user_setup(ctx)

        if user is not None:
            if isinstance(user, str):
                await ctx.send("Not a user!")
                return
            usera = user.id
            print(usera)
            if database.zscore("users", str(usera)) is not None:
                times = str(int(database.zscore("users", str(usera))))
                user = f"<@{str(usera)}>"
            else:
                await ctx.send("This user does not exist on our records!")
                return
        else:
            if database.zscore("users", str(
                    ctx.message.author.id)) is not None:
                user = f"<@{str(ctx.message.author.id)}>"
                times = str(
                    int(database.zscore("users", str(ctx.message.author.id))))
            else:
                await ctx.send(
                    "You haven't used this bot yet! (except for this)")
                return

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="User Score:",
                        value=f"{user} has answered correctly {times} times.")
        await ctx.send(embed=embed)

    # leaderboard - returns top 1-10 users
    @commands.command(
        brief="- Top scores",
        help="- Top scores, argument can be between 1 and 10, default is 5",
        aliases=["lb"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def leaderboard(self, ctx, placings=5):
        print("leaderboard")

        await channel_setup(ctx)
        await user_setup(ctx)

        leaderboard_list = []
        if database.zcard("users") == 0:
            await ctx.send("There are no users in the database.")
            return
        if placings > 10 or placings < 1:
            await ctx.send("Not a valid number. Pick one between 1 and 10!")
            return
        if placings > database.zcard("users"):
            placings = database.zcard("users")

        leaderboard_list = database.zrevrangebyscore("users", "+inf", "-inf",
                                                     0, placings, True)
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        leaderboard = ""

        for x in range(len(leaderboard_list)):
            user = ctx.guild.get_member(int(leaderboard_list[x][0]))
            if user is None:
                user = self.bot.get_user(int(leaderboard_list[x][0]))
                if user is None:
                    user = "**Deleted**"
                else:
                    user = f"**{user.name}#{user.discriminator}**"
            else:
                user = f"<@{str(leaderboard_list[x][0])[2:-1]}>"
            leaderboard += f"{str(x+1)}. {user} - {str(int(leaderboard_list[x][1]))}\n"
        embed.add_field(name="Leaderboard", value=leaderboard, inline=False)

        if database.zscore("users", str(ctx.message.author.id)) is not None:
            placement = int(
                database.zrevrank("users", str(ctx.message.author.id))) + 1
            embed.add_field(
                name="You:",
                value=f"You are #{str(placement)} on the leaderboard.",
                inline=False)
        else:
            embed.add_field(name="You:",
                            value="You haven't answered any correctly.")

        await ctx.send(embed=embed)

    # missed - returns top 1-10 missed birds
    @commands.command(
        brief="- Top globally incorrect birds",
        help=
        "- Top globally incorrect birds, argument can be between 1 and 10, default is 5",
        aliases=["m"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def missed(self, ctx, placings=5):
        print("missed")

        await channel_setup(ctx)
        await user_setup(ctx)

        leaderboard_list = []
        if database.zcard("incorrect") == 0:
            await ctx.send("There are no birds in the database.")
            return
        if placings > 10 or placings < 1:
            await ctx.send("Not a valid number. Pick one between 1 and 10!")
            return
        if placings > database.zcard("incorrect"):
            placings = database.zcard("incorrect")

        leaderboard_list = database.zrevrangebyscore("incorrect", "+inf",
                                                     "-inf", 0, placings, True)
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        leaderboard = ""

        for x in range(len(leaderboard_list)):
            leaderboard += f"{str(x+1)}. {str(leaderboard_list[x][0])[2:-1]} - {str(int(leaderboard_list[x][1]))}\n"
        embed.add_field(name="Top Missed Birds",
                        value=leaderboard,
                        inline=False)

        await ctx.send(embed=embed)

    # Command-specific error checking
    @leaderboard.error
    async def leader_error(self, ctx, error):
        print("leaderboard error")
        if isinstance(error, commands.BadArgument):
            await ctx.send('Not an integer!')
        elif isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " +
                           str(round(error.retry_after)) + " s.",
                           delete_after=5.0)
        else:
            await ctx.send("""**An uncaught leaderboard error has occurred.**
*Please log this message in #support in the support server below, or try again.* 
**Error:** """ + str(error))
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    @missed.error
    async def missed_error(self, ctx, error):
        print("missed error")
        if isinstance(error, commands.BadArgument):
            await ctx.send('Not an integer!')
        elif isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send("**Cooldown.** Try again after " +
                           str(round(error.retry_after)) + " s.",
                           delete_after=5.0)
        else:
            await ctx.send("""**An uncaught missed birds error has occurred.**
*Please log this message in #support in the support server below, or try again.* 
**Error:** """ + str(error))
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error


def setup(bot):
    bot.add_cog(Score(bot))
