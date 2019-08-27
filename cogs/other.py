# other.py | misc. commands 
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

from functions import *


class Other(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Gives call+image of 1 bird
    @commands.command(help="- Gives an image and call of a bird", aliases=['i'])
    @commands.cooldown(1, 10.0, type=commands.BucketType.channel)
    async def info(self, ctx, *, arg):
        print("info")

        await channel_setup(ctx)
        await user_setup(ctx)

        bird = arg
        print("info")
        await ctx.send("Please wait a moment.")
        await send_bird(ctx, str(bird), message="Here's the image!")
        await send_birdsong(ctx, str(bird),  "Here's the call!")

    # Wiki command - argument is the wiki page
    @commands.command(help="- Fetch the wikipedia page for any given argument")
    @commands.cooldown(1, 8.0, type=commands.BucketType.channel)
    async def wiki(self, ctx, *, arg):
        print("wiki")

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
    @commands.cooldown(1, 300.0, type=commands.BucketType.channel)
    async def meme(self, ctx):
        print("meme")

        await channel_setup(ctx)
        await user_setup(ctx)

        x = randint(0, len(memeList))
        await ctx.send(memeList[x])

    # bot info command - gives info on bot
    @commands.command(help="- Gives info on bot, support server invite, stats", aliases=["bot_info", "support", "stats"])
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def botinfo(self, ctx):
        print("bot info")
        
        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="Bot Info",
                        value="This bot was created by EraserBird and person_v1.32 for helping people practice bird identification for Science Olympiad.",
                        inline=False)
        embed.add_field(name="Support",
                        value="If you are experiencing any issues, have feature requests, or want to get updates on bot status, join our support server below.",
                        inline=False)
        embed.add_field(name="Stats",
                        value=f"This bot can see {len(self.bot.users)} users and is in {len(self.bot.guilds)} servers. The WebSocket latency is {str(round((self.bot.latency*1000)))} ms.",
                        inline=False)
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # invite command - sends invite link
    @commands.command(help="- Get the invite link for this bot")
    @commands.cooldown(1, 5.0, type=commands.BucketType.channel)
    async def invite(self, ctx):
        print("invite")
        
        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="Invite",
                        value="""To invite this bot to your own server, use the following invite links.\n
                        **Bird-ID:** https://discordapp.com/api/oauth2/authorize?client_id=601917808137338900&permissions=51200&scope=bot\n
                        **Orni-Bot:** https://discordapp.com/api/oauth2/authorize?client_id=601755752410906644&permissions=51200&scope=bot\n
                        For more information on the differences between the two bots, visit our support server below.""",
                        inline=False)
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # Test command - for testing purposes only
    @commands.command(help="- test command", hidden=True)
    async def test(self, ctx):
        print("test")
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="Test",
                        value="Errors whee",
                        inline=False)
        await ctx.send(embed=embed)
        raise GenericError("Test Error")


def setup(bot):
    bot.add_cog(Other(bot))
