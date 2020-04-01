# Bird-ID

[![Discord Invite](https://discordapp.com/api/guilds/601913706288381952/embed.png)](https://discord.gg/tNyGDve) [![Build Status](https://travis-ci.org/tctree333/Bird-ID.svg?branch=master)](https://travis-ci.org/tctree333/Bird-ID) [![Maintainability](https://api.codeclimate.com/v1/badges/6731bd218230bbc9e088/maintainability)](https://codeclimate.com/github/tctree333/Bird-ID/maintainability) [![Test Coverage](https://api.codeclimate.com/v1/badges/6731bd218230bbc9e088/test_coverage)](https://codeclimate.com/github/tctree333/Bird-ID/test_coverage) [![Total alerts](https://img.shields.io/lgtm/alerts/g/tctree333/Bird-ID.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/tctree333/Bird-ID/alerts/)

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
2. Install a local Redis server by running `chmod +x install-redis.sh && ./install-redis.sh`. [Source](https://redis.io/topics/quickstart). Start your Redis server with `redis-server`. We're using Redis 4.0.14.
3. Tell the code to use your local Redis server by setting the environment variable `LOCAL_REDIS` to `true` with `export LOCAL_REDIS="true"`.
4. Optionally, you can create a [sentry.io](https://sentry.io/) account, which we use for error monitoring. Update `setup.sh` to your Sentry DSN. If you don't do this, set the `NO_SENTRY` environment variable to `true` before running the bot.
5. Register a bot account on the [Discord Developers Portal](https://discordapp.com/developers/applications/). To do so, create a new application. Name your application, then navigate to the `Bot` section, and add a bot. Change your application name if necessary. Update `setup.sh` with your bot token (`Bot` section) and Discord user id.
6. Generate your bot invite link by going to the `OAuth2` section in the Discord Developers Portal. Select `bot` as the scope, and check `Send Messages`, `Embed Links`, `Attach Files`, and `Manage Roles` in the `Bot Permissions` section. Copy the generated link (it should look like this: `https://discordapp.com/api/oauth2/authorize?client_id=(Your Client ID)&permissions=268486656&scope=bot`). Add the bot to your own server by pasting the link into your browser.
7. Install any necessary packages with `pip install -r requirements.txt`. You may also want to setup a python virtual environment to avoid package conflicts before installing packages.
8. You are now ready to run the application! Setup the environment with `source setup.sh`. Start the bot with `python3 -m bot`. Make sure you're on Python version 3.7.

If you're running this locally for personal use or development, you may want to disable precaching of media files since the bot will download a lot of files all at once, which slows response during startup, especially with slower internet. To disable the precache, comment out the line `refresh_cache.start()` (around L65) in `__main__.py`.

The bot will also attempt to backup the Redis database to a set Discord channel, to disable this, comment out the line `refresh_backup.start()` (around L66) in `__main__.py`. Alternatively, you can set the `BACKUPS_CHANNEL` variable with a channel ID that the bot can access (around L37, `__main__.py`).

If you need help or have any questions, let us know in our [Discord support server.](https://discord.gg/xDqYddK)

## Troubleshooting
If you are having issues running the bot locally, here are some tips and common issues people run into.

* Make sure you're on Python 3.7, since we're using some language features only avaliable in version 3.7.
* If you're having issues with Redis, make sure you're on version 4.0.14 or later. If you're still having issues, see the Redis [documentation](https://redis.io/documentation).
* Common Redis errors include:
  * `ValueError: Redis URL must specify one of the followingschemes (redis://, rediss://, unix://)` - Make sure you've set the `LOCAL_REDIS` environment variable to `true` if you're using a local Redis server. If you're using a remote Redis server, make sure the `REDIS_URL` environment variable is set correctly.
  * `redis.exceptions.ConnectionError: Error 61 connecting to localhost:6379. Connection refused.` - Make sure your Redis server is actually running.
* If your error message mentions errors with the `covid` cog or a coronavirus API and you aren't terribly concerned about this feature, disable the cog manually by commenting out the line `'bot.cogs.covid'` (around L74) in the `bot/__main__.py` file.
* If your error is about missing Discord Permissions, make sure your bot account has permission to send messages, send files, embed links, and manage roles in that channel.

Having other issues not listed here? Ask in our [Discord support server](https://discord.gg/xDqYddK) and we will do our best to solve the problem.

## Files and Folders

The main bot application uses the bot folder.
  * `__main__.py` is the application start point, with `functions.py` containing assorted functions assisting with downloading bird files and other commonly used functions.
  * The `data` folder stores bird lists, with `data.py` managing those lists along with logging and database tasks.
  * The `cogs` folder contains the bot commands themselves, with each file being a different collection of commands (a category in `b!help`).
  * The `media` folder contains assorted image files for achievement badges and other things.

Bot unit tests uses the `test` folder. Currently, test coverage is quite poor and these tests are mostly just for fun and learning. If you would like to contribute to tests and increase test coverage, that would be greatly appreciated.
  * `discord_mock.py` contains classes to replicate discord.py functionality.
  * `test_{COG NAME}.py` contains the tests for the respective cog.

The web API uses the `web` folder. Currently, development of the web API is paused.

`.travis.yml` is the config file for Travis CI, which runs the tests. `travis_pr_script.sh` is a script for Travis that installs and runs a local Redis instance for PRs, since private environment variables in PRs are disabled for security reasons.

`runtime.txt` and `Procfile` are files used by Heroku, where we host the bot.

### **_Happy Identification!_**
