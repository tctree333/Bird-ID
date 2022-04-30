# other.py | misc. commands
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

import contextlib
import os
import random
import string
import typing
from difflib import get_close_matches

import discord
import wikipedia
from discord.ext import commands

from bot.core import get_sciname, get_taxon, send_bird
from bot.data import (
    alpha_codes,
    birdListMaster,
    logger,
    memeList,
    sciListMaster,
    states,
    taxons,
)
from bot.filters import Filter, MediaType
from bot.functions import CustomCooldown, build_id_list

# Discord max message length is 2000 characters, leave some room just in case
MAX_MESSAGE = 1900


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def broken_join(input_list: list[str], max_size: int = MAX_MESSAGE) -> list[str]:
        pages: list[str] = []
        lines: list[str] = []
        block_length = 0
        for line in input_list:
            if block_length + len(line) > max_size:
                page = "\n".join(lines)
                pages.append(page)
                lines.clear()
                block_length = 0
            lines.append(line)
            block_length += len(line)

        if lines:
            page = "\n".join(lines)
            pages.append(page)

        return pages

    # Info - Gives call+image of 1 bird
    @commands.command(
        brief="- Gives an image and call of a bird",
        help="- Gives an image and call of a bird. The bird name must come before any options.",
        usage="[bird] [options]",
        aliases=["i"],
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def info(self, ctx, *, arg):
        logger.info("command: info")
        arg = arg.lower().strip()

        filters = Filter.parse(arg)
        if filters.vc:
            filters.vc = False
            await ctx.send("**The VC filter is not allowed here!**")

        options = filters.display()
        arg = arg.split(" ")

        bird = None

        if len(arg[0]) == 4:
            bird = alpha_codes.get(arg[0].upper())

        if not bird:
            for i in reversed(range(1, 6)):
                # try the first 5 words, then first 4, etc. looking for a match
                matches = get_close_matches(
                    string.capwords(" ".join(arg[:i]).replace("-", " ")),
                    birdListMaster + sciListMaster,
                    n=1,
                    cutoff=0.8,
                )
                if matches:
                    bird = matches[0]
                    break

        if not bird:
            await ctx.send("Bird not found. Are you sure it's on the list?")
            return

        delete = await ctx.send("Please wait a moment.")
        if options:
            await ctx.send(f"**Detected filters**: `{'`, `'.join(options)}`")

        an = "an" if bird.lower()[0] in ("a", "e", "i", "o", "u") else "a"
        await send_bird(
            ctx, bird, MediaType.IMAGE, filters, message=f"Here's {an} *{bird.lower()}* image!"
        )
        await send_bird(
            ctx, bird, MediaType.SONG, filters, message=f"Here's {an} *{bird.lower()}* song!"
        )
        await delete.delete()
        return

    # Filter command - lists available Macaulay Library filters and aliases
    @commands.command(
        help="- Lists available Macaulay Library filters.", aliases=["filter"]
    )
    @commands.check(CustomCooldown(8.0, bucket=commands.BucketType.user))
    async def filters(self, ctx):
        logger.info("command: filters")
        filters = Filter.aliases()
        embed = discord.Embed(
            title="Media Filters",
            type="rich",
            description="Filters can be space-separated or comma-separated. "
            + "You can use any alias to set filters. "
            + "Please note media will only be shown if it "
            + "matches all the filters, so using filters can "
            + "greatly reduce the number of media returned.",
            color=discord.Color.green(),
        )
        embed.set_author(name="Bird ID - An Ornithology Bot")
        for title, subdict in filters.items():
            value = "".join(
                (
                    f"**{name.title()}**: `{'`, `'.join(aliases)}`\n"
                    for name, aliases in subdict.items()
                )
            )
            embed.add_field(name=title.title(), value=value, inline=False)
        await ctx.send(embed=embed)

    # List command - argument is state/bird list
    @commands.command(
        help="- DMs the user with the appropriate bird list.", name="list"
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def list_of_birds(self, ctx, state: str = "blank"):
        logger.info("command: list")

        state = state.upper()

        if state not in states:
            logger.info("invalid state")
            await ctx.send(
                f"**Sorry, `{state}` is not a valid state.**\n*Valid States:* `{', '.join(map(str, list(states.keys())))}`"
            )
            return

        state_birdlist = sorted(
            build_id_list(user_id=ctx.author.id, state=state, media_type=MediaType.IMAGE)
        )
        state_songlist = sorted(
            build_id_list(user_id=ctx.author.id, state=state, media_type=MediaType.SONG)
        )

        birdLists = self.broken_join(state_birdlist)
        songLists = self.broken_join(state_songlist)

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
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
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

        bird_list = sorted(
            build_id_list(
                user_id=ctx.author.id, taxon=taxon, state=state, media_type=MediaType.IMAGE
            )
        )
        song_bird_list = sorted(
            build_id_list(
                user_id=ctx.author.id, taxon=taxon, state=state, media_type=MediaType.SONG
            )
        )
        if not bird_list and not song_bird_list:
            logger.info("no birds for taxon/state")
            await ctx.send(
                "**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*"
            )
            return

        birdLists = self.broken_join(bird_list)
        songLists = self.broken_join(song_bird_list)

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
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    async def wikipedia(self, ctx, *, arg):
        logger.info("command: wiki")

        arg = arg.capitalize()

        try:
            page = wikipedia.page(arg, auto_suggest=False)
        except (
            wikipedia.exceptions.DisambiguationError,
            wikipedia.exceptions.PageError,
        ):
            try:
                page = wikipedia.page(f"{arg} (bird)", auto_suggest=False)
            except (
                wikipedia.exceptions.DisambiguationError,
                wikipedia.exceptions.PageError,
            ):
                # fall back to suggestion
                try:
                    page = wikipedia.page(arg)
                except wikipedia.exceptions.DisambiguationError:
                    await ctx.send(
                        "Sorry, that page was not found. Try being more specific."
                    )
                    return
                except wikipedia.exceptions.PageError:
                    await ctx.send("Sorry, that page was not found.")
                    return
        await ctx.send(page.url)

    # meme command - sends a random bird video/gif
    @commands.command(help="- Sends a funny bird video!")
    @commands.check(
        CustomCooldown(180.0, disable=True, bucket=commands.BucketType.user)
    )
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
        items = []
        with contextlib.suppress(FileNotFoundError):
            items += os.listdir("bot_files/cache/images/")
        with contextlib.suppress(FileNotFoundError):
            items += os.listdir("bot_files/cache/songs/")
        stats = {
            "sciname_cache": get_sciname.cache_info(),
            "taxon_cache": get_taxon.cache_info(),
            "num_downloaded_birds": len(items),
        }
        await ctx.send(f"```python\n{stats}```")

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    @commands.is_owner()
    async def error(self, ctx):
        logger.info("command: error")
        await ctx.send(1 / 0)

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    @commands.is_owner()
    async def test(
        self,
        ctx,
        *,
        user: typing.Optional[typing.Union[discord.Member, discord.User, str]] = None,
    ):
        logger.info("command: test")
        await ctx.send(
            f"```\nMembers Intent: {self.bot.intents.members}\n"
            + f"Message Mentions: {ctx.message.mentions}\n"
            + f"User: {user}\nType: {type(user)}```"
        )


def setup(bot):
    bot.add_cog(Other(bot))
