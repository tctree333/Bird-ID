# stats.py | commands for bot statistics
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

from io import BytesIO, StringIO

import discord
import pandas as pd
from discord.ext import commands

from bot.data import database, logger
from bot.functions import CustomCooldown, send_leaderboard


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_series(self, database_key):
        """Generates a pandas.Series from a Redis sorted set."""
        logger.info("generating series")
        data = database.zrevrangebyscore(database_key, "+inf", "-inf", withscores=True)
        return pd.Series({e[0]:e[1] for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), data)})

    def generate_dataframe(self, database_keys, titles):
        """Generates a pandas.DataFrame from multiple Redis sorted sets."""
        pipe = database.pipeline()
        for key in database_keys:
            pipe.zrevrangebyscore(key, "+inf", "-inf", withscores=True)
        result = pipe.execute()
        df = pd.DataFrame()
        for i, item in enumerate(result):
            df.insert(len(df.columns), titles[i], pd.Series({e[0]:e[1] for e in map(lambda x: (x[0].decode("utf-8"), int(x[1])), item)}))
        df = df.fillna(value=0).astype(int)
        return df

    def convert_users(self, df):
        """Converts discord user ids in DataFrames or Series indexes to usernames."""
        current_ids = df.index
        new_index = []
        for user_id in current_ids:
            user = self.bot.get_user(int(user_id))
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
        aliases=["freq"])
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

    # export data as csv
    @commands.command(help="- Exports bot data as a csv")
    @commands.check(CustomCooldown(60.0, bucket=commands.BucketType.channel))
    async def export(self, ctx):
        logger.info("command: export")

        files = []

        def _export_helper(database_keys, header, filename, users=False):
            if not isinstance(database_keys, str) and len(database_keys) > 1:
                data = self.generate_dataframe(database_keys, header.strip().split(",")[1:])
            else:
                key = (database_keys if isinstance(database_keys, str) else database_keys[0])
                data = self.generate_series(key)
            if users:
                data = self.convert_users(data)
            with StringIO() as f:
                f.write(header)
                data.to_csv(f, mode="wb", header=False)
                with BytesIO(f.getvalue().encode("utf-8")) as b:
                    files.append(discord.File(b, filename))

        logger.info("exporting freq command")
        _export_helper("frequency.command:global", "command,amount used\n", "command_frequency.csv", users=False)

        logger.info("exporting freq bird")
        _export_helper("frequency.bird:global", "bird,amount seen\n", "bird_frequency.csv", users=False)

        logger.info("exporting streaks")
        _export_helper(["streak:global", "streak.max:global"], "username#discrim,current streak,max streak\n", "streaks.csv", True)

        logger.info("exporting missed")
        keys = list(map(lambda x: x.decode("utf-8"), database.scan_iter(match="daily.incorrect:????-??-??", count=5000)))
        keys.sort()
        keys = ["incorrect:global"] + keys
        titles = ",".join(map(lambda x: x.split(":")[1], keys))
        _export_helper(keys, f"bird name,total missed,{titles}\n", "missed.csv", users=False)

        logger.info("exporting scores")
        keys = list(map(lambda x: x.decode("utf-8"), database.scan_iter(match="daily.score:????-??-??", count=5000)))
        keys.sort()
        keys = ["users:global"] + keys
        titles = ",".join(map(lambda x: x.split(":")[1], keys))
        _export_helper(keys, f"username#discrim,total score,{titles}\n", "scores.csv", users=True)

        await ctx.send(files=files)


def setup(bot):
    bot.add_cog(Stats(bot))
