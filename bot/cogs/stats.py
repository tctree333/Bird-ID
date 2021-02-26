# stats.py | commands for bot statistics
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
from io import BytesIO, StringIO

import discord
import numpy as np
import pandas as pd
from discord.ext import commands

from bot.data import database, logger
from bot.functions import CustomCooldown, send_leaderboard, fetch_get_user


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def generate_series(database_key):
        """Generates a pandas.Series from a Redis sorted set."""
        logger.info("generating series")
        data = database.zrevrangebyscore(database_key, "+inf", "-inf", withscores=True)
        return pd.Series(
            {e[0]: e[1] for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), data)}
        )

    @staticmethod
    def generate_dataframe(database_keys, titles):
        """Generates a pandas.DataFrame from multiple Redis sorted sets."""
        pipe = database.pipeline()
        for key in database_keys:
            pipe.zrevrangebyscore(key, "+inf", "-inf", withscores=True)
        result = pipe.execute()
        df = pd.DataFrame()
        for i, item in enumerate(result):
            df.insert(
                len(df.columns),
                titles[i],
                pd.Series(
                    {
                        e[0]: e[1]
                        for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), item)
                    }
                ),
            )
        df = df.fillna(value=0).astype(int)
        return df

    async def convert_users(self, df):
        """Converts discord user ids in DataFrames or Series indexes to usernames."""
        current_ids = df.index
        new_index = []
        for user_id in current_ids:
            user = await fetch_get_user(int(user_id), bot=self.bot, member=False)

            if user is None:
                new_index.append("User Unavailable")
            else:
                new_index.append(f"{user.name}#{user.discriminator}")
        df.index = new_index
        return df

    # give frequency stats
    @commands.command(
        help="- Gives info on command/bird frequencies",
        usage="[command|commands|c  bird|birds|b] [page]",
        aliases=["freq"],
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def frequency(self, ctx, scope="", page=1):
        logger.info("command: frequency")

        if scope in ("command", "commands", "c"):
            database_key = "frequency.command:global"
            title = "Most Frequently Used Commands"
        elif scope in ("bird", "birds", "b"):
            database_key = "frequency.bird:global"
            title = "Most Frequent Birds"
        else:
            await ctx.send("**Invalid Scope!**\n*Valid Scopes:* `commands, birds`")
            return

        await send_leaderboard(ctx, title, page, database_key)

    # give bot stats
    @commands.command(
        help="- Gives statistics on different topics",
        usage="[topic]",
        aliases=["stat"],
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def stats(self, ctx, topic="help"):
        logger.info("command: stats")

        if topic in ("scores", "score", "s"):
            topic = "scores"
        elif topic in ("usage", "u"):
            topic = "usage"
        elif topic in ("web", "w"):
            topic = "web"
        elif topic in ("help", ""):
            topic = "help"
        else:
            valid_topics = ("help", "scores", "usage", "web")
            await ctx.send(
                f"**`{topic}` is not a valid topic!**\nValid Topics: `{'`, `'.join(valid_topics)}`"
            )
            return

        embed = discord.Embed(
            title="Bot Stats",
            type="rich",
            color=discord.Color.blue(),
        )

        if topic == "help":
            embed.description = (
                "**Available statistic topics.**\n"
                + "This command is in progress and more stats may be added. "
                + "If there is a statistic you would like to see here, "
                + "please let us know in the support server."
            )
            embed.add_field(
                name="Scores",
                value="`b!stats [scores|score|s]`\n*Displays stats about scores.*",
            ).add_field(
                name="Usage",
                value="`b!stats [usage|u]`\n*Displays stats about usage.*",
            ).add_field(
                name="Web",
                value="`b!stats [web|w]`\n*Displays stats about web usage.*",
            )

        elif topic == "scores":
            embed.description = "**Score Statistics**"
            scores = self.generate_series("users:global")
            scores = scores[scores > 0]
            c, d = np.histogram(scores, bins=range(0, 1100, 100), range=(0, 1000))
            c = (c / len(scores) * 100).round(1)
            embed.add_field(
                name="Totals",
                inline=False,
                value="**Sum of top 10 user scores:** `{:,}`\n".format(
                    scores.nlargest(n=10).sum()
                )
                + "**Sum of all positive user scores:** `{:,}`\n".format(scores.sum()),
            ).add_field(
                name="Computations",
                inline=False,
                value="**Mean of all positive user scores:** `{:,.2f}`\n".format(
                    scores.mean()
                )
                + "**Median of all positive user scores:** `{:,.1f}`\n".format(
                    scores.median()
                ),
            ).add_field(
                name="Distributions",
                inline=False,
                value=f"**Number of users with scores over mean:** `{len(scores[scores > scores.mean()])}`\n"
                + "**Percentage of users with scores over mean:** `{:.1%}`".format(
                    len(scores[scores > scores.mean()]) / len(scores)
                )
                + "\n**Percentage of users with scores between:**\n"
                + "".join(
                    f"\u2192 *{d[i]}-{d[i+1]-1}*: `{c[i]}%`\n"  # \u2192 is the "Rightwards Arrow"
                    for i in range(len(c))
                ),
            )

        elif topic == "usage":
            embed.description = "**Usage Statistics**"

            today = datetime.datetime.now(datetime.timezone.utc).date()
            past_month = pd.date_range(  # pylint: disable=no-member
                today - datetime.timedelta(29), today
            ).date
            keys = list(f"daily.score:{str(date)}" for date in past_month)
            keys = ["users:global"] + keys
            titles = list(
                reversed(range(1, 32))
            )  # label columns by # days ago, today is 1 day ago
            month = self.generate_dataframe(keys, titles)
            total = month.loc[:, 31]
            month = month.loc[:, 30:1]  # remove totals column
            month = month.loc[(month != 0).any(1)]  # remove users with all 0s
            week = month.loc[:, 7:1]  # generate week from month
            week = week.loc[(week != 0).any(1)]
            today = week.loc[:, 1]  # generate today from week
            today = today.loc[today != 0]

            channels_see = len(list(self.bot.get_all_channels()))
            channels_used = int(database.zcard("score:global"))

            embed.add_field(
                name="Today (Since midnight UTC)",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(today)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(today.sum()),
            ).add_field(
                name="Last 7 Days",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(week)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(
                    week.sum().sum()
                ),
            ).add_field(
                name="Last 30 Days",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(month)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(
                    month.sum().sum()
                ),
            ).add_field(
                name="Total",
                inline=False,
                value="**Channels the bot can see:** `{:,}`\n".format(channels_see)
                + "**Channels that have used the bot at least once:** `{:,} ({:,.1%})`\n".format(
                    channels_used, channels_used / channels_see
                )
                + "*(Note: Deleted channels or channels that the bot can't see anymore are still counted).*\n"
                + "**Accounts that have used any command at least once:** `{:,}`\n".format(
                    len(total)
                )
                + "**Accounts that answered at least 1 correctly:** `{:,} ({:,.1%})`\n".format(
                    len(total[total > 0]), len(total[total > 0]) / len(total)
                ),
            )

        elif topic == "web":
            embed.description = "**Web Usage Statistics**"

            today = datetime.datetime.now(datetime.timezone.utc).date()
            past_month = pd.date_range(  # pylint: disable=no-member
                today - datetime.timedelta(29), today
            ).date
            web_score = (f"daily.webscore:{str(date)}" for date in past_month)
            web_usage = (f"daily.web:{str(date)}" for date in past_month)
            titles = (
                reversed(range(1, 31))
            )  # label columns by # days ago, today is 1 day ago

            web_score_month = self.generate_dataframe(web_score, titles)
            web_score_week = web_score_month.loc[:, 7:1]  # generate week from month
            web_score_week = web_score_week.loc[(web_score_week != 0).any(1)]  # remove users with no correct answers
            web_score_today = web_score_week.loc[:, 1]  # generate today from week
            web_score_today = web_score_today.loc[web_score_today != 0]  # remove users with no correct answers

            web_usage_month = self.generate_dataframe(web_usage, titles)
            web_usage_week = web_usage_month.loc[:, 7:1]
            web_usage_today = web_usage_week.loc[:, 1]

            score_totals_keys = sorted(map(
                lambda x: x.decode("utf-8"),
                database.scan_iter(match="daily.webscore:????-??-??", count=5000),
            ))
            score_totals_titles = ",".join(map(lambda x: x.split(":")[1], keys))
            web_score_total = self.generate_dataframe(score_totals_keys, score_totals_titles)
            
            usage_totals_keys = sorted(map(
                lambda x: x.decode("utf-8"),
                database.scan_iter(match="daily.webscore:????-??-??", count=5000),
            ))
            usage_totals_titles = ",".join(map(lambda x: x.split(":")[1], keys))
            web_usage_total = self.generate_dataframe(usage_totals_keys, usage_totals_titles)


            embed.add_field(
                name="Today (Since midnight UTC)",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(web_score_today)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(web_score_today.sum())
                + "**Check command usage:** `{:,}`\n".format(web_usage_today.loc["check"])
                + "**Skip command usage:** `{:,}`\n".format(web_usage_today.loc["skip"])
                + "**Hint command usage:** `{:,}`\n".format(web_usage_today.loc["hint"]),
            ).add_field(
                name="Last 7 Days",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(web_score_week)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(web_score_week.sum().sum())
                + "**Check command usage:** `{:,}`\n".format(web_usage_week.loc["check"].sum())
                + "**Skip command usage:** `{:,}`\n".format(web_usage_week.loc["skip"].sum())
                + "**Hint command usage:** `{:,}`\n".format(web_usage_week.loc["hint"].sum()),
            ).add_field(
                name="Last 30 Days",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(web_score_month)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(web_score_month.sum().sum())
                + "**Check command usage:** `{:,}`\n".format(web_usage_month.loc["check"].sum())
                + "**Skip command usage:** `{:,}`\n".format(web_usage_month.loc["skip"].sum())
                + "**Hint command usage:** `{:,}`\n".format(web_usage_month.loc["hint"].sum()),
            ).add_field(
                name="Total",
                inline=False,
                value="**Accounts that answered at least 1 correctly:** `{:,}`\n".format(
                    len(web_score_total)
                )
                + "**Total birds answered correctly:** `{:,}`\n".format(web_score_total.sum().sum())
                + "**Check command usage:** `{:,}`\n".format(web_usage_total.loc["check"].sum())
                + "**Skip command usage:** `{:,}`\n".format(web_usage_total.loc["skip"].sum())
                + "**Hint command usage:** `{:,}`\n".format(web_usage_total.loc["hint"].sum()),
            )

        await ctx.send(embed=embed)
        return

    # export data as csv
    @commands.command(help="- Exports bot data as a csv")
    @commands.check(CustomCooldown(60.0, bucket=commands.BucketType.channel))
    async def export(self, ctx):
        logger.info("command: export")

        files = []

        async def _export_helper(database_keys, header: str, filename: str, users=False):
            if not isinstance(database_keys, str) and len(database_keys) > 1:
                data = self.generate_dataframe(
                    database_keys, header.strip().split(",")[1:]
                )
            else:
                key = (
                    database_keys
                    if isinstance(database_keys, str)
                    else database_keys[0]
                )
                data = self.generate_series(key)
            if users:
                data = await self.convert_users(data)
            with StringIO() as f:
                f.write(header)
                data.to_csv(f, header=False)
                with BytesIO(f.getvalue().encode("utf-8")) as b:
                    files.append(discord.File(b, filename))

        logger.info("exporting freq command")
        await _export_helper(
            "frequency.command:global",
            "command,amount used\n",
            "command_frequency.csv",
            users=False,
        )

        logger.info("exporting freq bird")
        await _export_helper(
            "frequency.bird:global",
            "bird,amount seen\n",
            "bird_frequency.csv",
            users=False,
        )

        logger.info("exporting streaks")
        await _export_helper(
            ["streak:global", "streak.max:global"],
            "username#discrim,current streak,max streak\n",
            "streaks.csv",
            True,
        )

        logger.info("exporting missed")
        keys = list(
            map(
                lambda x: x.decode("utf-8"),
                database.scan_iter(match="daily.incorrect:????-??-??", count=5000),
            )
        )
        keys.sort()
        titles = ",".join(map(lambda x: x.split(":")[1], keys))
        keys = ["incorrect:global"] + keys
        await _export_helper(
            keys, f"bird name,total missed,{titles}\n", "missed.csv", users=False
        )

        logger.info("exporting scores")
        keys = list(
            map(
                lambda x: x.decode("utf-8"),
                database.scan_iter(match="daily.score:????-??-??", count=5000),
            )
        )
        keys.sort()
        titles = ",".join(map(lambda x: x.split(":")[1], keys))
        keys = ["users:global"] + keys
        await _export_helper(
            keys, f"username#discrim,total score,{titles}\n", "scores.csv", users=True
        )

        await ctx.send(files=files)


def setup(bot):
    bot.add_cog(Stats(bot))
