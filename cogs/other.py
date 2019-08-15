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
            await ctx.send("Sorry, that page was not found.")
        except wikipedia.exceptions.PageError:
            await ctx.send("Sorry, that page was not found.")

    # meme command - sends a random bird video/gif
    @commands.command(help="- sends a funny bird video!")
    @commands.cooldown(1, 300.0, type=commands.BucketType.channel)
    async def meme(self, ctx):
        print("meme")

        await channel_setup(ctx)
        await user_setup(ctx)

        x = randint(0, len(memeList))
        await ctx.send(memeList[x])

    # Test command - for testing purposes only
    @commands.command(help="- test command")
    async def test(self, ctx):
        print("test")
        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(name="Test",
                        value="https://en.wikipedia.org/wiki/Bald_eagle",
                        inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Other(bot))
