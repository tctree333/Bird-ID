# other.py | misc. commands
# Copyright (C) 2019  EraserBird, person_v1.32, hmmm

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
import typing
from difflib import get_close_matches

import discord
import wikipedia
from discord.ext import commands

from data.data import (birdListMaster, database, logger, memeList, taxons, sciBirdListMaster, states)
from functions import (channel_setup, get_sciname, owner_check, send_bird, send_birdsong, user_setup)

class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Info - Gives call+image of 1 bird
    @commands.command(help="- Gives an image and call of a bird", aliases=['i'])
    @commands.cooldown(1, 10.0, type=commands.BucketType.user)
    async def info(self, ctx, *, arg):
        logger.info("command: info")

        await channel_setup(ctx)
        await user_setup(ctx)

        matches = get_close_matches(arg, birdListMaster + sciBirdListMaster, n=1)
        if matches:
            bird = matches[0]

            delete = await ctx.send("Please wait a moment.")
            await send_bird(ctx, str(bird), message="Here's the image!")
            await send_birdsong(ctx, str(bird), message="Here's the call!")
            await delete.delete()

        else:
            await ctx.send("Bird not found. Are you sure it's on the list?")

    # List command - argument is state/bird list
    @commands.command(help="- DMs the user with the appropriate bird list.", name="list")
    @commands.cooldown(1, 8.0, type=commands.BucketType.user)
    async def list_of_birds(self, ctx, state: str = "blank"):
        logger.info("command: list")

        await channel_setup(ctx)
        await user_setup(ctx)

        state = state.upper()

        if state not in states:
            logger.info("invalid state")
            await ctx.send(
                f"**Sorry, `{state}` is not a valid state.**\n*Valid States:* `{', '.join(map(str, list(states.keys())))}`"
            )
            return

        birdLists = []
        temp = ""
        for bird in states[state]['birdList']:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                birdLists.append(temp)
                temp = ""
        birdLists.append(temp)

        songLists = []
        temp = ""
        for bird in states[state]['songBirds']:
            temp += f"{bird}\n"
            if len(temp) > 1950:
                songLists.append(temp)
                temp = ""
        songLists.append(temp)

        if ctx.author.dm_channel is None:
            await ctx.author.create_dm()

        await ctx.author.dm_channel.send(f"**The {state} bird list:**")
        for birds in birdLists:
            await ctx.author.dm_channel.send(f"```{birds}```")

        await ctx.author.dm_channel.send(f"**The {state} bird songs:**")
        for birds in songLists:
            await ctx.author.dm_channel.send(f"```{birds}```")

        await ctx.send(
            f"The `{state}` bird list has **{len(states[state]['birdList'])}** birds.\n" +
            f"The `{state}` bird list has **{len(states[state]['songBirds'])}** songs.\n" +
            "*A full list of birds has been sent to you via DMs.*"
        )

    # taxons command - argument is state/bird list
    @commands.command(
        help="- DMs the user with the appropriate bird list.",
        name="taxon",
        aliases=["taxons", "orders", "families", "order", "family"]
    )
    @commands.cooldown(1, 8.0, type=commands.BucketType.user)
    async def bird_taxons(self, ctx, taxon: str = "blank", state: str = "NATS"):
        logger.info("command: taxons")

        await channel_setup(ctx)
        await user_setup(ctx)

        taxon = taxon.lower()
        state = state.upper()

        if taxon not in taxons:
            logger.info("invalid taxon")
            await ctx.send(
                f"**Sorry, `{taxon}` is not a valid taxon.**\n*Valid taxons:* `{', '.join(map(str, list(taxons['taxons'])))}`"
            )
            return

        if state not in states:
            logger.info("invalid state")
            await ctx.send(
                f"**Sorry, `{state}` is not a valid state.**\n*Valid States:* `{', '.join(map(str, list(states.keys())))}`"
            )
            return

        birds_in_taxon = set(taxons[taxon])
        birds_in_state = set(states[state]["birdList"])
        song_birds_in_state = set(states[state]["songBirds"])
        bird_list = list(birds_in_taxon.intersection(birds_in_state))
        song_bird_list = list(birds_in_taxon.intersection(song_birds_in_state))

        if not bird_list and not song_bird_list:
            logger.info("no birds for taxon/state")
            await ctx.send(f"**Sorry, no birds could be found for the taxon/state combo.**\n*Please try again*")
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

        await ctx.author.dm_channel.send(f"**The `{taxon}` in the `{state}` bird list:**")
        for birds in birdLists:
            await ctx.author.dm_channel.send(f"```{birds}```")

        await ctx.author.dm_channel.send(f"**The `{taxon}` in the `{state}` bird songs:**")
        for birds in songLists:
            await ctx.author.dm_channel.send(f"```{birds}```")

        await ctx.send(
            f"The `{taxon}` in the `{state}` bird list has **{len(bird_list)}** birds.\n" +
            f"The `{taxon}` in the `{state}` bird list has **{len(song_bird_list)}** songs.\n" +
            "*A full list of birds has been sent to you via DMs.*"
        )

    # Wiki command - argument is the wiki page
    @commands.command(help="- Fetch the wikipedia page for any given argument", aliases=["wiki"])
    @commands.cooldown(1, 8.0, type=commands.BucketType.user)
    async def wikipedia(self, ctx, *, arg):
        logger.info("command: wiki")

        await channel_setup(ctx)
        await user_setup(ctx)

        try:
            page = wikipedia.page(arg)
            await ctx.send(page.url)
        except wikipedia.exceptions.DisambiguationError:
            await ctx.send("Sorry, that page was not found. Try being more specific.")
        except wikipedia.exceptions.PageError:
            await ctx.send("Sorry, that page was not found.")

    # meme command - sends a random bird video/gif
    @commands.command(help="- Sends a funny bird video!")
    @commands.cooldown(1, 300.0, type=commands.BucketType.user)
    async def meme(self, ctx):
        logger.info("command: meme")

        await channel_setup(ctx)
        await user_setup(ctx)
        await ctx.send(random.choice(memeList))

    # bot info command - gives info on bot
    @commands.command(
        help="- Gives info on bot, support server invite, stats", aliases=["bot_info", "support", "stats"]
    )
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def botinfo(self, ctx):
        logger.info("command: botinfo")

        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(
            name="Bot Info",
            value="This bot was created by EraserBird and person_v1.32 " +
            "for helping people practice bird identification for Science Olympiad.\n" +
            "**By adding this bot to a server, you are agreeing to our `Privacy Policy` and `Terms of Service`**.\n" +
            "<https://github.com/tctree333/Bird-ID/blob/master/PRIVACY.md>, " +
            "<https://github.com/tctree333/Bird-ID/blob/master/TERMS.md>",
            inline=False
        )
        embed.add_field(
            name="Support",
            value="If you are experiencing any issues, have feature requests, " +
            "or want to get updates on bot status, join our support server below.",
            inline=False
        )
        embed.add_field(
            name="Stats",
            value=f"This bot can see {len(self.bot.users)} users and is in {len(self.bot.guilds)} servers. " +
            f"There are {int(database.zcard('users:global'))} active users in {int(database.zcard('score:global'))} channels. "
            + f"The WebSocket latency is {round((self.bot.latency*1000))} ms.",
            inline=False
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # invite command - sends invite link
    @commands.command(help="- Get the invite link for this bot")
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def invite(self, ctx):
        logger.info("command: invite")

        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(
            name="Invite",
            value="""To invite this bot to your own server, use the following invite links.
**Bird-ID:** https://discordapp.com/api/oauth2/authorize?client_id=601917808137338900&permissions=268486656&scope=bot
**Orni-Bot:** https://discordapp.com/api/oauth2/authorize?client_id=601755752410906644&permissions=268486656&scope=bot\n
**By adding this bot to a server, you are agreeing to our `Privacy Policy` and `Terms of Service`**.
<https://github.com/tctree333/Bird-ID/blob/master/PRIVACY.md>, <https://github.com/tctree333/Bird-ID/blob/master/TERMS.md>\n
Unfotunately, Orni-Bot is currently unavaliable. For more information, visit our support server below.""",
            inline=False
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # ban command - prevents certain users from using the bot
    @commands.command(help="- ban command", hidden=True)
    @commands.check(owner_check)
    async def ban(self, ctx, *, user: discord.Member = None):
        logger.info("command: ban")
        if user is None:
            logger.info("no args")
            await ctx.send("Invalid User!")
            return
        logger.info(f"user-id: {user.id}")
        database.zadd("banned:global", {str(user.id): 0})
        await ctx.send(f"Ok, {user.name} cannot use the bot anymore!")

    # unban command - prevents certain users from using the bot
    @commands.command(help="- unban command", hidden=True)
    @commands.check(owner_check)
    async def unban(self, ctx, *, user: typing.Optional[typing.Union[discord.Member, str]] = None):
        logger.info("command: unban")
        if user is None:
            logger.info("no args")
            await ctx.send("Invalid User!")
            return
        logger.info(f"user-id: {user.id}")
        database.zrem("banned:global", str(user.id))
        await ctx.send(f"Ok, {user.name} can use the bot!")

    # Send command - for testing purposes only
    @commands.command(help="- send command", hidden=True, aliases=["sendas"])
    @commands.check(owner_check)
    async def send_as_bot(self, ctx, *, args):
        logger.info("command: send")
        logger.info(f"args: {args}")
        channel_id = int(args.split(' ')[0])
        message = args.strip(str(channel_id))
        channel = self.bot.get_channel(channel_id)
        await channel.send(message)
        await ctx.send("Ok, sent!")

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    async def test(self, ctx, *, bird):
        logger.info("command: test")
        sciname = await get_sciname(bird)
        await ctx.send(sciname)

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    async def error(self, ctx):
        logger.info("command: error")
        await ctx.send(1 / 0)

def setup(bot):
    bot.add_cog(Other(bot))
