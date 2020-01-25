# Bird-ID

[![Discord Invite](https://discordapp.com/api/guilds/601913706288381952/embed.png)](https://discord.gg/tNyGDve) [![Maintainability](https://api.codeclimate.com/v1/badges/6731bd218230bbc9e088/maintainability)](https://codeclimate.com/github/tctree333/Bird-ID/maintainability)

A discord bot for young ornithologists. This bot is designed to help people practice the identification portion of the Science Olympiad Ornithology event.

## Usage

The prefix for this bot is `b!`. Use `b!help` to get a list of commands, and `b!help [command]` for help with a specific command.

## Server

For help with the bot, feature requests, or any other questions, please join our support server [here.](https://discord.gg/tNyGdve) You can also add the bot to your own server, or use the bot too.

## Terms

By using this bot or adding it to a server, you agree to the [Terms of Service](TERMS.md), [Privacy Policy](PRIVACY.md), and [Community Code of Conduct](CODE_OF_CONDUCT.md).

## Contributing

If you have previous programming experience and would like to help us add features or fix issues, feel free to make a pull request. Our code probably isn't of the highest quality, so we value any suggestions you may have.

If you find an issue with the bot, please report it in the support server instead of opening a Github issue.

## Running Locally

To run the bot locally, you'll need to install some software first.

1. Clone the repo locally with `git clone https://github.com/tctree333/Bird-ID.git`.
2. Install a local Redis server by following the instructions [here.](https://redis.io/topics/quickstart) Start your Redis server with `redis-server`.
3. `cd` into this cloned repository. Modify line 30 of `data/data.py`.

```python
CHANGE: database = redis.from_url(os.getenv("REDIS_URL"))
TO: database = redis.Redis(host='localhost', port=6379, db=0)
```

4. Optionally, you can create a [sentry.io](https://sentry.io/) account, which we use for error monitoring. Update `setup.sh` to your Sentry DSN. If you don't do this, remove lines 41-46 of `data/data.py`.

```python
REMOVE:
# add sentry logging
sentry_sdk.init(
    dsn=str(os.getenv("SENTRY_DISCORD_DSN")),
    integrations=[RedisIntegration(), AioHttpIntegration()],
    before_send=before_sentry_send
)
```

5. Register a bot account on the [Discord Developers Portal](https://discordapp.com/developers/applications/). To do so, create a new application. Name your application, then navigate to the `Bot` section, and add a bot. Change your application name if necessary. Update `setup.sh` with your bot token (`Bot` section), client secret (`General Information` section), and Discord user id.
6. Install any necessary packages with `pip install -r requirements.txt`. You may also want to setup a python virtual environment to avoid package conflicts before installing packages.
7. You are now ready to run the application! Setup the environment with `source setup.sh`. Start the bot with `python3 main.py`.

If you need help or have any questions, let us know in our [Discord support server.](https://discord.gg/xDqYddK)

## Files and Folders

The main bot application uses `main.py`, `functions.py`, the `data` folder, the `cogs` folder, and the `achievements` folder.

-   `main.py` is the application start point, with `functions.py` containing assorted functions assisting with downloading bird files and other commonly used functions.
-   The `data` folder stores bird lists, with `data.py` managing those lists along with logging and database tasks.
-   The `cogs` folder contains the bot commands themselves, with each file being a different collection of commands (a category in `b!help`).
-   The `achievements` folder contains the image files for achievement badges.

The web API uses the `web` folder.

`runtime.txt` and `Procfile` are files used by Heroku, where we host the bot.

### **_Happy Identification!_**
