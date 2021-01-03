# state.py | commands for state specific birds
# Copyright (C) 2019-2021  EraserBird, person_v1.32

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

import asyncio
import re
import string
import time

import aiohttp
import discord
from discord.ext import commands
from sentry_sdk import capture_exception, capture_message

from bot.core import valid_bird
from bot.data import GenericError, database, logger, states
from bot.functions import CustomCooldown, auto_decode


class States(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def broken_send(self, ctx, message, between=""):
        pages = []
        temp_out = ""
        for line in message.splitlines(keepends=True):
            temp_out += line
            if len(temp_out) > 1700:
                temp_out = f"{between}{temp_out}{between}"
                pages.append(temp_out.strip())
                temp_out = ""
        temp_out = f"{between}{temp_out}{between}"
        pages.append(temp_out.strip())
        for item in pages:
            await ctx.send(item)

    # set state role
    @commands.command(help="- Sets your state", name="set", aliases=["state"])
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    @commands.guild_only()
    async def state(self, ctx, *, args):
        logger.info("command: state set")

        raw_roles = ctx.author.roles
        role_ids = [role.id for role in raw_roles]
        role_names = [role.name.lower() for role in ctx.author.roles]
        args = args.upper().split(" ")

        if "CUSTOM" in args and (
            not database.exists(f"custom.list:{ctx.author.id}")
            or database.exists(f"custom.confirm:{ctx.author.id}")
        ):
            await ctx.send(
                "Sorry, you don't have a custom list! Use `b!custom` to set your custom list."
            )
            return

        added = []
        removed = []
        invalid = []
        for arg in args:
            if arg not in states:
                logger.info("invalid state")
                invalid.append(arg)

            # gets similarities
            elif not set(role_names).intersection(set(states[arg]["aliases"])):
                # need to add role (does not have role)
                logger.info("add roles")
                raw_roles = ctx.guild.roles
                guild_role_names = [role.name.lower() for role in raw_roles]
                guild_role_ids = [role.id for role in raw_roles]

                if states[arg]["aliases"][0].lower() in guild_role_names:
                    # guild has role
                    index = guild_role_names.index(states[arg]["aliases"][0].lower())
                    role = ctx.guild.get_role(guild_role_ids[index])

                else:
                    # create role
                    logger.info("creating role")
                    role = await ctx.guild.create_role(
                        name=string.capwords(states[arg]["aliases"][0]),
                        permissions=discord.Permissions.none(),
                        hoist=False,
                        mentionable=False,
                        reason="Create state role for bird list",
                    )

                await ctx.author.add_roles(role, reason="Set state role for bird list")
                added.append(role.name)

            else:
                # have roles already (there were similarities)
                logger.info("already has role, removing")
                index = role_names.index(states[arg]["aliases"][0].lower())
                role = ctx.guild.get_role(role_ids[index])
                await ctx.author.remove_roles(
                    role, reason="Remove state role for bird list"
                )
                removed.append(role.name)

        await ctx.send(
            (
                f"**Sorry,** `{'`, `'.join(invalid)}` **{'are' if len(invalid) > 1 else 'is'} not a valid state.**\n"
                + f"*Valid States:* `{'`, `'.join(states.keys())}`\n"
                if invalid
                else ""
            )
            + (
                f"**Added the** `{'`, `'.join(added)}` **role{'s' if len(added) > 1 else ''}**\n"
                if added
                else ""
            )
            + (
                f"**Removed the** `{'`, `'.join(removed)}` **role{'s' if len(removed) > 1 else ''}**\n"
                if removed
                else ""
            )
        )

    # set custom bird list
    @commands.command(
        brief="- Sets your custom bird list",
        help="- Sets your custom bird list. "
        + "This command only works in DMs. Lists have a max size of 200 birds. "
        + "When verifying, the bot may incorrectly say it didn't find any images. "
        + "If this is the case and you have verified yourself by going to https://macaulaylibrary.org, "
        + "just try again later. You can use your custom list anywhere you would use "
        + "a state with the `CUSTOM` 'state'.",
    )
    @commands.check(CustomCooldown(5.0, bucket=commands.BucketType.user))
    @commands.dm_only()
    async def custom(self, ctx, *, args=""):
        logger.info("command: custom list set")

        args = args.lower().strip().split(" ")
        logger.info(f"parsed args: {args}")

        if (
            "replace" not in args
            and ctx.message.attachments
            and database.exists(f"custom.list:{ctx.author.id}")
        ):
            await ctx.send(
                "Woah there. You already have a custom list. "
                + "To view its contents, use `b!custom view`. "
                + "If you want to replace your list, upload the file with `b!custom replace`."
            )
            return

        if "delete" in args and database.exists(f"custom.list:{ctx.author.id}"):
            if (
                database.exists(f"custom.confirm:{ctx.author.id}")
                and database.get(f"custom.confirm:{ctx.author.id}").decode("utf-8")
                == "delete"
            ):
                database.delete(
                    f"custom.list:{ctx.author.id}", f"custom.confirm:{ctx.author.id}"
                )
                await ctx.send("Ok, your list was deleted.")
                return

            database.set(f"custom.confirm:{ctx.author.id}", "delete", ex=86400)
            await ctx.send(
                "Are you sure you want to permanently delete your list? "
                + "Use `b!delete` again within 24 hours to clear your custom list."
            )
            return

        if (
            "confirm" in args
            and database.get(f"custom.confirm:{ctx.author.id}").decode("utf-8")
            == "confirm"
        ):
            # list was validated by server and user, making permanent
            logger.info("user confirmed")
            database.persist(f"custom.list:{ctx.author.id}")
            database.delete(f"custom.confirm:{ctx.author.id}")
            database.set(f"custom.cooldown:{ctx.author.id}", 0, ex=86400)
            await ctx.send(
                "Ok, your custom bird list is now available. Use `b!custom view` "
                + "to view your list. You can change your list again in 24 hours."
            )
            return

        if (
            "validate" in args
            and database.get(f"custom.confirm:{ctx.author.id}").decode("utf-8")
            == "valid"
        ):
            # list was validated, now for user confirm
            logger.info("valid list, user needs to confirm")
            database.expire(f"custom.list:{ctx.author.id}", 86400)
            database.set(f"custom.confirm:{ctx.author.id}", "confirm", ex=86400)
            birdlist = "\n".join(
                bird.decode("utf-8")
                for bird in database.smembers(f"custom.list:{ctx.author.id}")
            )
            await ctx.send(
                f"**Please confirm the following list.** ({int(database.scard(f'custom.list:{ctx.author.id}'))} items)"
            )
            await self.broken_send(ctx, birdlist, between="```\n")
            await ctx.send(
                "Once you have looked over the list and are sure you want to add it, "
                + "please use `b!custom confirm` to have this list added as a custom list. "
                + "You have another 24 hours to confirm. "
                + "To start over, upload a new list with the message `b!custom replace`."
            )
            return

        if "view" in args:
            if not database.exists(f"custom.list:{ctx.author.id}"):
                await ctx.send(
                    "You don't have a custom list. To add a custom list, "
                    + "upload a txt file with a bird's name on each line to this DM "
                    + "and put `b!custom` in the **Add a Comment** section."
                )
                return
            birdlist = "\n".join(
                bird.decode("utf-8")
                for bird in database.smembers(f"custom.list:{ctx.author.id}")
            )
            birdlist = f"{birdlist}"
            await ctx.send(
                f"**Your Custom Bird List** ({int(database.scard(f'custom.list:{ctx.author.id}'))} items)"
            )
            await self.broken_send(ctx, birdlist, between="```\n")
            return

        if not database.exists(f"custom.list:{ctx.author.id}") or "replace" in args:
            # user inputted bird list, now validating
            start = time.perf_counter()
            if database.exists(f"custom.cooldown:{ctx.author.id}"):
                await ctx.send(
                    "Sorry, you'll have to wait 24 hours between changing lists."
                )
                return
            logger.info("reading received bird list")
            if not ctx.message.attachments:
                logger.info("no file detected")
                await ctx.send(
                    "Sorry, no file was detected. Upload your txt file and put `b!custom` in the **Add a Comment** section."
                )
                return
            decoded = await auto_decode(await ctx.message.attachments[0].read())
            if not decoded:
                logger.info("invalid character encoding")
                await ctx.send(
                    "Sorry, something went wrong. Are you sure this is a text file?"
                )
                return
            parsed_birdlist = set(map(lambda x: x.strip(), decoded.strip().split("\n")))
            parsed_birdlist.discard("")
            parsed_birdlist = list(parsed_birdlist)
            if len(parsed_birdlist) > 200:
                logger.info("parsed birdlist too long")
                await ctx.send(
                    "Sorry, we're not supporting custom lists larger than 200 birds. Make sure there are no empty lines."
                )
                return
            logger.info("checking for invalid characters")
            char = re.compile("[^A-Za-z '\-\xC0-\xD6\xD8-\xF6\xF8-\xFF]")
            for item in parsed_birdlist:
                if len(item) > 1000:
                    logger.info("item too long")
                    await ctx.send(
                        f"Line starting with `{item[:100]}` exceeds 1000 characters."
                    )
                    return
                search = char.search(item)
                if search:
                    logger.info("invalid character detected")
                    await ctx.send(
                        f"An invalid character `{search.group()}` was detected. Only letters, spaces, hyphens, and apostrophes are allowed."
                    )
                    await ctx.send(
                        f"Error on line starting with `{item[:100]}`, position {search.span()[0]}"
                    )
                    return
            database.delete(
                f"custom.list:{ctx.author.id}", f"custom.confirm:{ctx.author.id}"
            )
            await self.validate(ctx, parsed_birdlist)
            elapsed = time.perf_counter() - start
            await ctx.send(
                f"**Finished validation in {round(elapsed//60)} minutes {round(elapsed%60, 4)} seconds.** {ctx.author.mention}"
            )
            logger.info(
                f"Finished validation in {round(elapsed//60)} minutes {round(elapsed%60, 4)} seconds."
            )
            return

        if database.exists(f"custom.confirm:{ctx.author.id}"):
            next_step = database.get(f"custom.confirm:{ctx.author.id}").decode("utf-8")
            if next_step == "valid":
                await ctx.send(
                    "You need to validate your list. Use `b!custom validate` to do so. "
                    + "You can also delete or replace your list with `b!custom [delete|replace]`"
                )
                return
            if next_step == "confirm":
                await ctx.send(
                    "You need to confirm your list. Use `b!custom confirm` to do so. "
                    + "You can also delete or replace your list with `b!custom [delete|replace]`"
                )
                return
            if next_step == "delete":
                await ctx.send(
                    "You're in the process of deleting your list. Use `b!custom delete` to do so. "
                    + "You can also replace your list with `b!custom replace`"
                )
                return
            capture_message(f"custom.confirm database invalid with {next_step}")
            await ctx.send(
                "Whoops, something went wrong. Please report this incident "
                + "in the support server below.\nhttps://discord.gg/fXxYyDJ"
            )
            return

        await ctx.send(
            "Use `b!custom view` to view your bird list or `b!custom replace` to replace your bird list."
        )

    async def validate(self, ctx, parsed_birdlist):
        validated_birdlist = []
        async with aiohttp.ClientSession() as session:
            logger.info("starting validation")
            await ctx.send("**Validating bird list...**\n*This may take a while.*")
            invalid_output = ""
            valid_output = ""
            validity = []
            for x in range(0, len(parsed_birdlist), 10):
                validity += await asyncio.gather(
                    *(valid_bird(bird, session) for bird in parsed_birdlist[x : x + 10])
                )
                logger.info("sleeping during validation...")
                await asyncio.sleep(5)
            logger.info("checking validation")
            for item in validity:
                if item[1]:
                    validated_birdlist.append(
                        string.capwords(
                            item[3].split(" - ")[0].strip().replace("-", " ")
                        )
                    )
                    valid_output += f"Item `{item[0]}`: Detected as **{item[3]}**\n"
                else:
                    invalid_output += f"Item `{item[0]}`: **{item[2]}** {f'(Detected as *{item[3]}*)' if item[3] else ''}\n"
            logger.info("done validating")

        if valid_output:
            logger.info("sending validation success")
            valid_output = (
                "**Succeeded Items:** Please verify items were detected correctly.\n"
                + valid_output
            )
            await self.broken_send(ctx, valid_output)
        if invalid_output:
            logger.info("sending validation failure")
            invalid_output = (
                "**FAILED ITEMS:** Please fix and resubmit.\n" + invalid_output
            )
            await self.broken_send(ctx, invalid_output)
            return False

        await ctx.send("**Saving bird list...**")
        database.sadd(f"custom.list:{ctx.author.id}", *validated_birdlist)
        database.expire(f"custom.list:{ctx.author.id}", 86400)
        database.set(f"custom.confirm:{ctx.author.id}", "valid", ex=86400)
        await ctx.send(
            "**Ok!** Your bird list has been temporarily saved. "
            + "Please use `b!custom validate` to view and confirm your bird list. "
            + "To start over, upload a new list with the message `b!custom replace`. "
            + "You have 24 hours to confirm before your bird list will automatically be deleted."
        )
        return True

    @state.error
    async def set_error(self, ctx, error):
        logger.info("state set error")
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"**Please enter your state.**\n*Valid States:* `{'`, `'.join(states.keys())}`"
            )
        elif isinstance(error, commands.CommandOnCooldown):  # send cooldown
            await ctx.send(
                f"**Cooldown.** Try again after {str(round(error.retry_after))}s.",
                delete_after=5.0,
            )
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("**This command is unavailable in DMs!**")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "**The bot does not have enough permissions to fully function.**\n"
                + f"**Permissions Missing:** `{', '.join(map(str, error.missing_perms))}`\n"
                + "*Please try again once the correct permissions are set.*"
            )
        elif isinstance(error, GenericError):
            if error.code == 192:
                # channel is ignored
                return
            if error.code == 842:
                await ctx.send("**Sorry, you cannot use this command.**")
            elif error.code == 666:
                logger.info("GenericError 666")
            elif error.code == 201:
                logger.info("HTTP Error")
                capture_exception(error)
                await ctx.send(
                    "**An unexpected HTTP Error has occurred.**\n *Please try again.*"
                )
            else:
                logger.info("uncaught generic error")
                capture_exception(error)
                await ctx.send(
                    "**An uncaught generic error has occurred.**\n"
                    + "*Please log this message in #support in the support server below, or try again.*\n"
                    + "**Error:** "
                    + str(error)
                )
                await ctx.send("https://discord.gg/fXxYyDJ")
                raise error
        else:
            capture_exception(error)
            await ctx.send(
                "**An uncaught set error has occurred.**\n"
                + "*Please log this message in #support in the support server below, or try again.*\n"
                + "**Error:** "
                + str(error)
            )
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error


def setup(bot):
    bot.add_cog(States(bot))
