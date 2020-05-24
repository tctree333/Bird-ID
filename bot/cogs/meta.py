# meta.py | commands about the bot
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

import typing

import discord
from discord.ext import commands

from bot.data import database, logger
from bot.functions import channel_setup, user_setup, CustomCooldown


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # bot info command - gives info on bot
    @commands.command(
        help="- Gives info on bot, support server invite, stats",
        aliases=["bot_info", "support", "stats"],
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def botinfo(self, ctx):
        logger.info("command: botinfo")

        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(
            name="Bot Info",
            value="This bot was created by EraserBird and person_v1.32 "
            + "for helping people practice bird identification for Science Olympiad.\n"
            + "**By adding this bot to a server, you are agreeing to our "
            + "[Privacy Policy](<https://github.com/tctree333/Bird-ID/blob/master/PRIVACY.md>) and "
            + "[Terms of Service](<https://github.com/tctree333/Bird-ID/blob/master/TERMS.md>)**.\n"
            + "Bird-ID is licensed under the [GNU GPL v3.0](<https://github.com/tctree333/Bird-ID/blob/master/LICENSE>).",
            inline=False,
        )
        embed.add_field(
            name="Support",
            value="If you are experiencing any issues, have feature requests, "
            + "or want to get updates on bot status, join our support server below.",
            inline=False,
        )
        embed.add_field(
            name="Stats",
            value=f"This bot can see {len(self.bot.users)} users and is in {len(self.bot.guilds)} servers. "
            + f"There are {int(database.zcard('users:global'))} active users in {int(database.zcard('score:global'))} channels. "
            + f"The WebSocket latency is {round((self.bot.latency*1000))} ms.",
            inline=False,
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # invite command - sends invite link
    @commands.command(help="- Get the invite link for this bot")
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.channel))
    async def invite(self, ctx):
        logger.info("command: invite")

        await channel_setup(ctx)
        await user_setup(ctx)

        embed = discord.Embed(type="rich", colour=discord.Color.blurple())
        embed.set_author(name="Bird ID - An Ornithology Bot")
        embed.add_field(
            name="Invite",
            value="To invite this bot to your own server, use the following invite links.\n"
            + "**Bird-ID:** https://discord.com/api/oauth2/authorize?client_id=601917808137338900&permissions=268486656&scope=bot\n"
            + "**Orni-Bot:** https://discord.com/api/oauth2/authorize?client_id=601755752410906644&permissions=268486656&scope=bot\n\n"
            + "**By adding this bot to a server, you are agreeing to our `Privacy Policy` and `Terms of Service`**.\n"
            + "<https://github.com/tctree333/Bird-ID/blob/master/PRIVACY.md>, <https://github.com/tctree333/Bird-ID/blob/master/TERMS.md>\n\n"
            + "Unfotunately, Orni-Bot is currently unavaliable. For more information, visit our support server below.",
            inline=False,
        )
        await ctx.send(embed=embed)
        await ctx.send("https://discord.gg/fXxYyDJ")

    # ignore command - ignores a given channel
    @commands.command(
        brief="- Ignore all commands in a channel",
        help="- Ignore all commands in a channel. The 'manage guild' permission is needed to use this command.",
    )
    @commands.check(CustomCooldown(3.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def ignore(self, ctx, channels: commands.Greedy[discord.TextChannel] = None):
        logger.info("command: invite")

        await channel_setup(ctx)
        await user_setup(ctx)

        added = ""
        removed = ""
        if channels is not None:
            logger.info(f"ignored channels: {[c.name for c in channels]}")
            for channel in channels:
                if database.zscore("ignore:global", str(channel.id)) is None:
                    added += f"`#{channel.name}` (`{channel.category.name if channel.category else 'No Category'}`)\n"
                    database.zadd("ignore:global", {str(channel.id): ctx.guild.id})
                else:
                    removed += f"`#{channel.name}` (`{channel.category.name if channel.category else 'No Category'}`)\n"
                    database.zrem("ignore:global", str(channel.id))
        else:
            await ctx.send("**No valid channels were passed.**")

        ignored = "".join(
            [
                f"`#{channel.name}` (`{channel.category.name if channel.category else 'No Category'}`)\n"
                for channel in map(
                    lambda c: ctx.guild.get_channel(int(c)),
                    database.zrangebyscore(
                        "ignore:global", ctx.guild.id - 0.1, ctx.guild.id + 0.1
                    ),
                )
            ]
        )

        await ctx.send(
            (f"**Ignoring:**\n{added}" if added else "")
            + (f"**Stopped ignoring:**\n{removed}" if removed else "")
            + (f"**Ignored Channels:**\n{ignored}" if ignored else "**No channels in this server are currently ignored.**")
        )

    # leave command - removes itself from guild
    @commands.command(
        brief="- Remove the bot from the guild",
        help="- Remove the bot from the guild. The 'manage guild' permission is needed to use this command.",
        aliases=["kick"],
    )
    @commands.check(CustomCooldown(2.0, bucket=commands.BucketType.channel))
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def leave(self, ctx, confirm: typing.Optional[bool] = False):
        logger.info("command: leave")

        await channel_setup(ctx)
        await user_setup(ctx)

        if database.exists(f"leave:{ctx.guild.id}"):
            logger.info("confirming")
            if confirm:
                logger.info(f"confirmed. Leaving {ctx.guild}")
                database.delete(f"leave:{ctx.guild.id}")
                await ctx.send("**Ok, bye!**")
                await ctx.guild.leave()
                return
            logger.info("confirm failed. leave canceled")
            database.delete(f"leave:{ctx.guild.id}")
            await ctx.send("**Leave canceled.**")
            return

        logger.info("not confirmed")
        database.set(f"leave:{ctx.guild.id}", 0, ex=60)
        await ctx.send(
            "**Are you sure you want to remove me from the guild?**\n"
            + "Use `b!leave yes` to confirm, `b!leave no` to cancel. "
            + "You have 60 seconds to confirm before it will automatically cancel."
        )

    # ban command - prevents certain users from using the bot
    @commands.command(help="- ban command", hidden=True)
    @commands.is_owner()
    async def ban(self, ctx, *, user: typing.Optional[discord.Member] = None):
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
    @commands.is_owner()
    async def unban(self, ctx, *, user: typing.Optional[discord.Member] = None):
        logger.info("command: unban")
        if user is None:
            logger.info("no args")
            await ctx.send("Invalid User!")
            return
        logger.info(f"user-id: {user.id}")
        database.zrem("banned:global", str(user.id))
        await ctx.send(f"Ok, {user.name} can use the bot!")


def setup(bot):
    bot.add_cog(Meta(bot))
