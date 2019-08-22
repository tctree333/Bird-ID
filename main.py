# Import modules
from discord.ext import tasks
import shutil
import traceback
from functions import *


# Initialize bot
bot = commands.Bot(command_prefix=['b!', 'b.', 'b#'],
                   case_insensitive=True,
                   description="BirdID - Your Very Own Ornithologist")

# Logging
@bot.event
async def on_ready():
    print("Logged in as:")
    print(bot.user.name)
    print(bot.user.id)
    print("_" * 50)
    # Change discord activity
    await bot.change_presence(activity=discord.Activity(type=3, name="birds"))

# Here we load our extensions(cogs) that are located in the cogs directory
initial_extensions = ['cogs.get_birds',
                      'cogs.check',
                      'cogs.skip',
                      'cogs.hint',
                      'cogs.score',
                      'cogs.other']

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to load extension {extension}.')
            traceback.print_exc()

# task to clear downloads
@tasks.loop(hours=72.0)
async def clear_cache():
    print("clear cache")
    try:
        shutil.rmtree(r'downloads/')
        print("Cleared downloads cache.")
    except FileNotFoundError:
        print("Already cleared downloads.")

    try:
        shutil.rmtree(r'songs/')
        print("Cleared songs.")
    except FileNotFoundError:
        print("Already cleared songs.")


######
# GLOBAL ERROR CHECKING
######

@bot.event
async def on_command_error(ctx, error):
    print("Error: "+str(error))

    if isinstance(error, commands.CommandOnCooldown):  # send cooldown
        await ctx.send("**Cooldown.** Try again after "+str(round(error.retry_after))+" s.", delete_after=5.0)

    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, the command was not found.")

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("This command requires an argument!")

    elif isinstance(error, commands.BadArgument):
        print("bad argument")
        await ctx.send("The argument passed was invalid!")

    # don't handle errors with local handlers
    elif hasattr(ctx.command, 'on_error'):
            return

    elif isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, redis.exceptions.ResponseError):
            if database.exists(str(ctx.channel.id)):
                await ctx.send("""**An unexpected ResponseError has occurred.**
                                *Please log this message in #support in the support server below, or try again.*
                                **Error:** """ + str(error))
                await ctx.send("https://discord.gg/fXxYyDJ")
            else:
                await channel_setup(ctx)
                await ctx.send("Please run that command again.")

        else:
            print("uncaught command error")
            await ctx.send("""**An uncaught command error has occurred.**
                             *Please log this message in #support in the support server below, or try again.*
                             **Error:**  """ + str(error))
            await ctx.send("https://discord.gg/fXxYyDJ")
            raise error

    else:
        print("uncaught non-command")
        await ctx.send("""**An uncaught non-command error has occurred.**
                         *Please log this message in #support in the support server below, or try again.*
                         **Error:**  """ + str(error))
        await ctx.send("https://discord.gg/fXxYyDJ")
        raise error


# Start the task
clear_cache.start()

# Actually run the bot
token = os.getenv("token")
bot.run(token)
