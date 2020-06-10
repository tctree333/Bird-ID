# other.py | misc. commands
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

import random
from difflib import get_close_matches

import discord
import wikipedia
from discord.ext import commands

from bot.core import get_sciname, get_taxon, send_bird, send_birdsong
from bot.data import birdListMaster, logger, memeList, sciListMaster, states, taxons
from bot.filters import Filter
from bot.functions import CustomCooldown, build_id_list


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Info - Gives call+image of 1 bird
    @commands.command(
        brief="- Gives an image and call of a bird",
        help="- Gives an image and call of a bird. The bird name must come before any options.",
        usage="[bird] [options]",
        aliases=["i"],
    )
    @commands.check(CustomCooldown(10.0, bucket=commands.BucketType.user))
    async def info(self, ctx, *, arg):
        logger.info("command: info")
        arg = arg.lower().strip()

        filters = Filter().parse(arg)
        options = filters.display()
        arg = arg.split(" ")
        for i in reversed(range(1, 6)):
            matches = get_close_matches(
                " ".join(arg[:i]), birdListMaster + sciListMaster, n=1
            )
            if matches:
                bird = matches[0]
                delete = await ctx.send("Please wait a moment.")
                if options:
                    await ctx.send(f"**Detected filters**: `{'`, `'.join(options)}`")
                await send_bird(
                    ctx, bird, filters, message=f"Here's a *{bird.lower()}* image!"
                )
                await send_birdsong(
                    ctx, bird, message=f"Here's a *{bird.lower()}* call!"
                )
                await delete.delete()
                return
        await ctx.send("Bird not found. Are you sure it's on the list?")

    # Filter command - lists available Macaulay Library filters and aliases
    @commands.command(
        help="- Lists available Macaulay Library filters.", aliases=["filter"]
    )
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.user))
    async def filters(self, ctx):
        logger.info("command: filters")
        filters = Filter().aliases()
        embed = discord.Embed(
            title="Media Filters",
            type="rich",
            description="Filters can be space-seperated or comma-seperated. "
            + "You can use any alias to set filters. "
            + "Please note media will only be shown if it "
            + "matches all the filters, so using filters can "
            + "greatly reduce the number of media returned.",
            color=discord.Color.green(),
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")
        for title, subdict in filters.items():
            value = ""
            for name, aliases in subdict.items():
                value += f"**{name.title()}**: `{'`, `'.join(aliases)}`\n"
            embed.add_field(name=title.title(), value=value, inline=False)
        await ctx.send(embed=embed)

    # List command - argument is state/bird list
    @commands.command(
        help="- DMs the user with the appropriate bird list.", name="list"
    )
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.user))
    async def list_of_birds(self, ctx, state: str = "blank"):
        logger.info("command: list")

        state = state.upper()

        if state not in states:
            logger.info("invalid state")
            await ctx.send(
                f"**Sorry, `{state}` is not a valid state.**\n*Valid States:* `{', '.join(map(str, list(states.keys())))}`"
            )
            return

        state_birdlist = build_id_list(
            user_id=ctx.author.id, state=state, media="images"
        )
        state_songlist = build_id_list(
            user_id=ctx.author.id, state=state, media="songs"
        )

        birdLists = []
        temp = ""
        for bird in state_birdlist:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                birdLists.append(temp)
                temp = ""
        birdLists.append(temp)

        songLists = []
        temp = ""
        for bird in state_songlist:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                songLists.append(temp)
                temp = ""
        songLists.append(temp)

        if ctx.author.dm_channel is None:
            await ctx.author.create_dm()

        await ctx.author.dm_channel.send(f"**The {state} bird list:**")
        for birds in birdLists:
            await ctx.author.dm_channel.send(f"```\n{birds}```")

        await ctx.author.dm_channel.send(f"**The {state} bird songs:**")
        for birds in songLists:
            await ctx.author.dm_channel.send(f"```\n{birds}```")

        await ctx.send(
            f"The `{state}` bird list has **{len(state_birdlist)}** birds.\n"
            + f"The `{state}` bird list has **{len(state_songlist)}** songs.\n"
            + "*A full list of birds has been sent to you via DMs.*"
        )

    # taxons command - argument is state/bird list
    @commands.command(
        help="- DMs the user with the appropriate bird list.",
        name="taxon",
        aliases=["taxons", "orders", "families", "order", "family"],
    )
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.user))
    async def bird_taxons(self, ctx, taxon: str = "blank", state: str = "NATS"):
        logger.info("command: taxons")

        taxon = taxon.lower()
        state = state.upper()

        if taxon not in taxons:
            logger.info("invalid taxon")
            await ctx.send(
                f"**Sorry, `{taxon}` is not a valid taxon.**\n*Valid taxons:* `{', '.join(map(str, list(taxons.keys())))}`"
            )
            return

        if state not in states:
            logger.info("invalid state")
            await ctx.send(
                f"**Sorry, `{state}` is not a valid state.**\n*Valid States:* `{', '.join(map(str, list(states.keys())))}`"
            )
            return

        bird_list = build_id_list(
            user_id=ctx.author.id, taxon=taxon, state=state, media="images"
        )
        song_bird_list = build_id_list(
            user_id=ctx.author.id, taxon=taxon, state=state, media="songs"
        )
        if not bird_list and not song_bird_list:
            logger.info("no birds for taxon/state")
            await ctx.send(
                f"**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*"
            )
            return

        birdLists = []
        temp = ""
        for bird in bird_list:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                birdLists.append(temp)
                temp = ""
        birdLists.append(temp)

        songLists = []
        temp = ""
        for bird in song_bird_list:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                songLists.append(temp)
                temp = ""
        songLists.append(temp)

        if ctx.author.dm_channel is None:
            await ctx.author.create_dm()

        await ctx.author.dm_channel.send(
            f"**The `{taxon}` in the `{state}` bird list:**"
        )
        for birds in birdLists:
            await ctx.author.dm_channel.send(f"```\n{birds}```")

        await ctx.author.dm_channel.send(
            f"**The `{taxon}` in the `{state}` bird songs:**"
        )
        for birds in songLists:
            await ctx.author.dm_channel.send(f"```\n{birds}```")

        await ctx.send(
            f"The `{taxon}` in the `{state}` bird list has **{len(bird_list)}** birds.\n"
            + f"The `{taxon}` in the `{state}` bird list has **{len(song_bird_list)}** songs.\n"
            + "*A full list of birds has been sent to you via DMs.*"
        )

    # Wiki command - argument is the wiki page
    @commands.command(
        help="- Fetch the wikipedia page for any given argument", aliases=["wiki"]
    )
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.user))
    async def wikipedia(self, ctx, *, arg):
        logger.info("command: wiki")

        try:
            page = wikipedia.page(arg)
            await ctx.send(page.url)
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, that page was not found. Try being more specific.")
        except wikipedia.exceptions.PageError:
            await ctx.send("Sorry, that page was not found.")

    # meme command - sends a random bird video/gif
    @commands.command(help="- Sends a funny bird video!")
    @commands.check(CustomCooldown(300.0, bucket=commands.BucketType.user))
    async def meme(self, ctx):
        logger.info("command: meme")
        await ctx.send(random.choice(memeList))

    # Send command - for testing purposes only
    @commands.command(help="- send command", hidden=True, aliases=["sendas"])
    @commands.is_owner()
    async def send_as_bot(self, ctx, *, args):
        logger.info("command: send")
        logger.info(f"args: {args}")
        channel_id = int(args.split(" ")[0])
        message = args.strip(str(channel_id))
        channel = self.bot.get_channel(channel_id)
        await channel.send(message)
        await ctx.send("Ok, sent!")

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    @commands.is_owner()
    async def cache(self, ctx):
        logger.info("command: cache stats")
        stats = {
            "sciname_cache": get_sciname.cache_info(),
            "taxon_cache": get_taxon.cache_info(),
        }
        await ctx.send(f"```python\n{stats}```")

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    @commands.is_owner()
    async def error(self, ctx):
        logger.info("command: error")
        await ctx.send(1 / 0)


def setup(bot):
    bot.add_cog(Other(bot))
