# race.py | commands for racing/competition
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
import time

import discord
from discord.ext import commands

from bot.data import database, logger, states, taxons
from bot.functions import channel_setup, check_state_role, user_setup, DmCooldown

class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_options(self, ctx):
        bw, addon, state, media, limit, taxon = database.hmget(
            f"race.data:{ctx.channel.id}", ["bw", "addon", "state", "media", "limit", "taxon"]
        )
        options = str(
            f"**Age/Sex:** {addon.decode('utf-8') if addon else 'default'}\n" + f"**Black & White:** {bw==b'bw'}\n" +
            f"**Special bird list:** {state.decode('utf-8') if state else 'None'}\n" +
            f"**Taxons:** {taxon.decode('utf-8') if taxon else 'None'}\n" +
            f"**Media Type:** {media.decode('utf-8')}\n" + f"**Amount to Win:** {limit.decode('utf-8')}\n"
        )
        return options

    async def _send_stats(self, ctx, preamble):
        placings = 5
        database_key = f"race.scores:{ctx.channel.id}"
        if database.zcard(database_key) == 0:
            logger.info(f"no users in {database_key}")
            await ctx.send("There are no users in the database.")
            return

        if placings > database.zcard(database_key):
            placings = database.zcard(database_key)

        leaderboard_list = database.zrevrangebyscore(database_key, "+inf", "-inf", 0, placings, True)
        embed = discord.Embed(type="rich", colour=discord.Color.blurple(), title=preamble)
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

            leaderboard += f"{i+1}. {user} - {int(stats[1])}\n"

        start = int(database.hget(f"race.data:{ctx.channel.id}", "start"))
        elapsed = str(datetime.timedelta(seconds=round(time.time()) - start))

        embed.add_field(name="Options", value=await self._get_options(ctx), inline=False)
        embed.add_field(name="Stats", value=f"**Race Duration:** `{elapsed}`", inline=False)
        embed.add_field(name="Leaderboard", value=leaderboard, inline=False)

        if database.zscore(database_key, str(ctx.author.id)) is not None:
            placement = int(database.zrevrank(database_key, str(ctx.author.id))) + 1
            embed.add_field(name="You:", value=f"You are #{placement}.", inline=False)
        else:
            embed.add_field(name="You:", value="You haven't answered any correctly.")

        await ctx.send(embed=embed)

    async def stop_race_(self, ctx):
        first = database.zrevrange(f"race.scores:{ctx.channel.id}", 0, 0, True)[0]
        if ctx.guild is not None:
            user = ctx.guild.get_member(int(first[0]))
        else:
            user = None

        if user is None:
            user = self.bot.get_user(int(first[0]))
            if user is None:
                user = "Deleted"
            else:
                user = f"{user.name}#{user.discriminator}"
        else:
            user = f"{user.name}#{user.discriminator} ({user.mention})"

        await ctx.send(
            f"**Congratulations, {user}!**\n" +
            f"You have won the race by correctly identifying `{int(first[1])}` birds. " + "*Way to go!*"
        )

        database.hset(f"race.data:{ctx.channel.id}", "stop", round(time.time()))

        await self._send_stats(ctx, "**Race stopped.**")
        database.delete(f"race.data:{ctx.channel.id}")
        database.delete(f"race.scores:{ctx.channel.id}")

    @commands.group(
        brief="- Base race command",
        help="- Base race command\n" + "Races allow you to compete with others to see who can ID a bird first. " +
        "Starting a race will keep all cooldowns the same, but automatically run " +
        "'b!bird' (or 'b!song') after every check. You will still need to use 'b!check' " +
        "to check your answer. Races are channel-specific, and anyone in that channel can play." +
        "Races end when a player is the first to correctly ID a set amount of birds. (default 10)"
    )
    async def race(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid subcommand passed.**\n*Valid Subcommands:* `start, view, stop`')

    @race.command(
        brief="- Starts race",
        help="""- Starts race.
        Arguments passed will become the default arguments to 'b!bird', but can be manually overwritten during use.
        Arguments can be passed in any taxon.
        However, having both females and juveniles are not supported.""",
        aliases=["st"],
        usage="[bw] [state] [female|juvenile] [taxon] [amount to win (default 10)]"
    )
    @commands.check(DmCooldown(3.0, bucket=commands.BucketType.channel))
    async def start(self, ctx, *, args_str: str = ""):
        logger.info("command: start race")

        await channel_setup(ctx)
        await user_setup(ctx)

        if ctx.guild is None:
            logger.info("dm context")
            await ctx.send("**Sorry, racing is not avaliable in DMs.**")
            return

        if not str(ctx.channel.name).startswith("racing"):
            logger.info("not race channel")
            await ctx.send(
                "**Sorry, racing is not availiable in this channel.**\n" +
                "*Set the channel name to start with `racing` to enable it.*"
            )
            return

        if database.exists(f"race.data:{ctx.channel.id}"):
            logger.info("already race")
            await ctx.send("**There is already a race in session.** *Change settings/view stats with `b!race view`*")
            return
        else:
            args = args_str.split(" ")
            logger.info(f"args: {args}")
            if "bw" in args:
                bw = "bw"
            else:
                bw = ""

            taxon_args = set(taxons.keys()).intersection({arg.lower() for arg in args})
            if taxon_args:
                taxon = " ".join(taxon_args).strip()
            else:
                taxon = ""

            states_args = set(states.keys()).intersection({arg.upper() for arg in args})
            if states_args:
                state = " ".join(states_args).strip()
            else:
                state = " ".join(check_state_role(ctx))

            female = "female" in args or "f" in args
            juvenile = "juvenile" in args or "j" in args
            if female and juvenile:
                await ctx.send("**Juvenile females are not yet supported.**\n*Please try again*")
                return
            elif female:
                addon = "female"
            elif juvenile:
                addon = "juvenile"
            else:
                addon = ""

            song = "song" in args or "s" in args
            image = "image" in args or "i" in args or "picture" in args or "p" in args
            if song and image:
                await ctx.send("**Songs and images are not yet supported.**\n*Please try again*")
                return
            elif song:
                media = "song"
            elif image:
                media = "image"
            else:
                media = "image"

            ints = []
            for n in args:
                try:
                    ints.append(int(n))
                except ValueError:
                    continue
            if ints:
                limit = int(ints[0])
            else:
                limit = 10

            if limit > 1000000:
                await ctx.send("**Sorry, the maximum amount to win is 1 million.**")
                limit = 1000000

            logger.info(f"adding bw: {bw}; addon: {addon}; state: {state}; media: {media}; limit: {limit}")

            database.hmset(
                f"race.data:{ctx.channel.id}", {
                    "start": round(time.time()),
                    "stop": 0,
                    "limit": limit,
                    "bw": bw,
                    "state": state,
                    "addon": addon,
                    "media": media,
                    "taxon": taxon
                }
            )

            database.zadd(f"race.scores:{ctx.channel.id}", {str(ctx.author.id): 0})
            await ctx.send(f"**Race started with options:**\n{await self._get_options(ctx)}")

            if database.hget(f"race.data:{ctx.channel.id}", "media").decode("utf-8") == "image":
                logger.info("clearing previous bird")
                database.hset(f"channel:{ctx.channel.id}", "bird", "")
                database.hset(f"channel:{ctx.channel.id}", "answered", "1")

                logger.info("auto sending next bird image")
                addon, bw, taxon = database.hmget(f"race.data:{ctx.channel.id}", ["addon", "bw", "taxon"])
                birds = self.bot.get_cog("Birds")
                await birds.send_bird_(
                    ctx,
                    addon.decode("utf-8"),  # type: ignore
                    bw.decode("utf-8"),  # type: ignore
                    taxon.decode("utf-8")  # type: ignore
                )

            if database.hget(f"race.data:{ctx.channel.id}", "media").decode("utf-8") == "song":
                logger.info("clearing previous bird")
                database.hset(f"channel:{ctx.channel.id}", "sBird", "")
                database.hset(f"channel:{ctx.channel.id}", "sAnswered", "1")

                logger.info("auto sending next bird song")
                birds = self.bot.get_cog("Birds")
                await birds.send_song_(ctx)

    @race.command(
        brief="- Views race",
        help="- Views race.\nRaces allow you to compete with your friends to ID a certain bird first."
    )
    @commands.check(DmCooldown(3.0, bucket=commands.BucketType.channel))
    async def view(self, ctx):
        logger.info("command: view race")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"race.data:{ctx.channel.id}"):
            await self._send_stats(ctx, f"**Race In Progress**")
        else:
            await ctx.send("**There is no race in session.** *You can start one with `b!race start`*")

    @race.command(help="- Stops race", aliases=["stp", "end"])
    @commands.check(DmCooldown(3.0, bucket=commands.BucketType.channel))
    async def stop(self, ctx):
        logger.info("command: stop race")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"race.data:{ctx.channel.id}"):
            await self.stop_race_(ctx)
        else:
            await ctx.send("**There is no race in session.** *You can start one with `b!race start`*")

def setup(bot):
    bot.add_cog(Race(bot))
