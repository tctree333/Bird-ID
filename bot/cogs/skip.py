# skip.py | commands for skipping birds
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

from discord.ext import commands

from bot.data import database, get_wiki_url, logger
from bot.functions import CustomCooldown


class Skip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Skip command - no args
    @commands.command(help="- Skip the current bird to get a new one", aliases=["sk"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def skip(self, ctx):
        logger.info("command: skip")

        currentBird = str(database.hget(f"channel:{ctx.channel.id}", "bird"))[2:-1]
        database.hset(f"channel:{ctx.channel.id}", "bird", "")
        database.hset(f"channel:{ctx.channel.id}", "answered", "1")
        if currentBird != "":  # check if there is bird
            url = get_wiki_url(ctx, currentBird)
            await ctx.send(f"Ok, skipping {currentBird.lower()}")
            await ctx.send(url if not database.exists(f"race.data:{ctx.channel.id}") else f"<{url}>")  # sends wiki page
            database.zadd("streak:global", {str(ctx.author.id): 0})  # end streak
            if database.exists(f"race.data:{ctx.channel.id}") and database.hget(f"race.data:{ctx.channel.id}",
                                                                                "media").decode("utf-8") == "image":

                limit = int(database.hget(f"race.data:{ctx.channel.id}", "limit"))
                first = database.zrevrange(f"race.scores:{ctx.channel.id}", 0, 0, True)[0]
                if int(first[1]) >= limit:
                    logger.info("race ending")
                    race = self.bot.get_cog("Race")
                    await race.stop_race_(ctx)
                else:
                    logger.info("auto sending next bird image")
                    addon, bw, taxon, state = database.hmget(f"race.data:{ctx.channel.id}", ["addon", "bw", "taxon", "state"])
                    birds = self.bot.get_cog("Birds")
                    await birds.send_bird_(ctx, addon.decode("utf-8"), bw.decode("utf-8"), taxon.decode("utf-8"), state.decode("utf-8"))
        else:
            await ctx.send("You need to ask for a bird first!")

    # Skip command - no args
    @commands.command(help="- Skip the current goatsucker to get a new one", aliases=["goatskip", "sg"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def skipgoat(self, ctx):
        logger.info("command: skipgoat")

        currentBird = str(database.hget(f"channel:{ctx.channel.id}", "goatsucker"))[2:-1]
        database.hset(f"channel:{ctx.channel.id}", "goatsucker", "")
        database.hset(f"channel:{ctx.channel.id}", "gsAnswered", "1")
        if currentBird != "":  # check if there is bird
            url = get_wiki_url(ctx, currentBird)
            await ctx.send(f"Ok, skipping {currentBird.lower()}")  
            await ctx.send(url) # sends wiki page
            database.zadd("streak:global", {str(ctx.author.id): 0})
        else:
            await ctx.send("You need to ask for a bird first!")

    # Skip song command - no args
    @commands.command(help="- Skip the current bird call to get a new one", aliases=["songskip", "ss"])
    @commands.check(CustomCooldown(10.0, bucket=commands.BucketType.channel))
    async def skipsong(self, ctx):
        logger.info("command: skipsong")

        currentSongBird = str(database.hget(f"channel:{ctx.channel.id}", "sBird"))[2:-1]
        database.hset(f"channel:{ctx.channel.id}", "sBird", "")
        database.hset(f"channel:{ctx.channel.id}", "sAnswered", "1")
        if currentSongBird != "":  # check if there is bird
            url = get_wiki_url(ctx, currentSongBird)
            await ctx.send(f"Ok, skipping {currentSongBird.lower()}")
            await ctx.send(url if not database.exists(f"race.data:{ctx.channel.id}") else f"<{url}>")  # sends wiki page
            database.zadd("streak:global", {str(ctx.author.id): 0})
            if database.exists(f"race.data:{ctx.channel.id}") and str(
                database.hget(f"race.data:{ctx.channel.id}", "media")
            )[2:-1] == "song":

                limit = int(database.hget(f"race.data:{ctx.channel.id}", "limit"))
                first = database.zrevrange(f"race.scores:{ctx.channel.id}", 0, 0, True)[0]
                if int(first[1]) >= limit:
                    logger.info("race ending")
                    race = self.bot.get_cog("Race")
                    await race.stop_race_(ctx)
                else:
                    logger.info("auto sending next bird song")
                    birds = self.bot.get_cog("Birds")
                    await birds.send_song_(ctx)
        else:
            await ctx.send("You need to ask for a bird first!")

def setup(bot):
    bot.add_cog(Skip(bot))
