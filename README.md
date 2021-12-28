# Bird-ID

[![Discord Invite](https://discord.com/api/guilds/601913706288381952/embed.png)](https://discord.gg/tNyGDve) [![Build Status](https://travis-ci.org/tctree333/Bird-ID.svg?branch=master)](https://travis-ci.org/tctree333/Bird-ID) [![Maintainability](https://api.codeclimate.com/v1/badges/6731bd218230bbc9e088/maintainability)](https://codeclimate.com/github/tctree333/Bird-ID/maintainability) [![Test Coverage](https://api.codeclimate.com/v1/badges/6731bd218230bbc9e088/test_coverage)](https://codeclimate.com/github/tctree333/Bird-ID/test_coverage) [![Total alerts](https://img.shields.io/lgtm/alerts/g/tctree333/Bird-ID.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/tctree333/Bird-ID/alerts/)

A discord bot for young ornithologists. This bot is designed to help people practice the identification portion of the Science Olympiad Ornithology event.

## Usage

The prefix for this bot is `b!`. Use `b!help` to get a list of commands, and `b!help [command]` for help with a specific command. A demo of the bot is available [here](example.mp4).

## Server

For help with the bot, feature requests, or any other questions, please join our support server [here.](https://discord.gg/2HbshwGjnm) You can also add the bot to your own server, or use the bot too.

## Terms

By using this bot or adding it to a server, you agree to the [Terms of Service](TERMS.md), [Privacy Policy](PRIVACY.md), and [Community Code of Conduct](CODE_OF_CONDUCT.md).

## Contributing

If you have previous programming experience and would like to help us add features or fix issues, feel free to make a pull request. Our code probably isn't of the highest quality, so we value any suggestions you may have.

If you find an issue with the bot, please report it in the support server instead of opening a Github issue.

## Running Locally

To run the bot locally, you'll need to install some software first.

1. Clone the repo locally with `git clone https://github.com/tctree333/Bird-ID.git`.
2. Install a local Redis server by running `chmod +x install-redis.sh && ./install-redis.sh`. [Source](https://redis.io/topics/quickstart). Start your Redis server with `redis-server`. We're using Redis 4.0.14.
3. Copy the file `.env.example` to `.env` (**DO NOT** edit `.env.example` directly)
4. If using a remote redis server, or an address other than the default `redis://localhost:6379`, set `SCIOLY_ID_BOT_LOCAL_REDIS` to `false` and change `SCIOLY_ID_BOT_REDIS_URL` appropriately
5. Optionally, you can create a [sentry.io](https://sentry.io/) account, which we use for error monitoring. Set `SCIOLY_ID_BOT_USE_SENTRY` to `true` and `SCIOLY_ID_BOT_SENTRY_DISCORD_DSN` to your Sentry DSN in `.env`.
6. Register a bot account on the [Discord Developers Portal](https://discord.com/developers/applications/). To do so, create a new application. Name your application, then navigate to the `Bot` section, and add a bot. Change your application name if necessary. In `.env`, update `SCIOLY_ID_BOT_TOKEN` with your bot token (`Bot` section) and update `SCIOLY_ID_BOT_OWNER_IDS` to a comma separated list of user-ids of owners. You can find your user-id by enabling Developer mode in Discord Settings > Appearance, right clicking on your username in the Member List, and selecting `Copy ID`.
7. Generate your bot invite link by going to the `OAuth2` section in the Discord Developers Portal. Select `bot` as the scope, and check `Send Messages`, `Embed Links`, `Attach Files`, and `Manage Roles` in the `Bot Permissions` section. Copy the generated link (it should look like this: `https://discord.com/api/oauth2/authorize?client_id=(Your Client ID)&permissions=268486656&scope=bot`). Add the bot to your own server by pasting the link into your browser.
8. Install any necessary packages with `pip install -r requirements.txt`. You may also want to setup a python virtual environment to avoid package conflicts before installing packages.
9. You are now ready to run the application! Start the bot with `python3 -m bot`. Make sure you're on Python version 3.7.

The bot can also attempt to backup the Redis database to a set Discord channel. To enable this, set `SCIOLY_ID_BOT_ENABLE_BACKUPS` to `true` and `SCIOLY_ID_BOT_BACKUPS_CHANNEL` to the channel id of a channel the bot has access to in `.env`.

If you need help or have any questions, let us know in our [Discord support server.](https://discord.gg/2HbshwGjnm)

## Troubleshooting

If you are having issues running the bot locally, here are some tips and common issues people run into.

- Make sure you're on Python 3.7, since we're using some language features only available in version 3.7.
- If you're having issues with Redis, make sure you're on version 4.0.14 or later. If you're still having issues, see the Redis [documentation](https://redis.io/documentation).
- Common Redis errors include:
  - `ValueError: Redis URL must specify one of the followingschemes (redis://, rediss://, unix://)` - Make sure the `SCIOLY_ID_BOT_LOCAL_REDIS` environment variable is set to `true` if you're using a local Redis server. If you're using a remote Redis server, or a server with a different address, make sure `SCIOLY_ID_BOT_LOCAL_REDIS` is `false` and the `SCIOLY_ID_BOT_REDIS_URL` environment variable is set correctly.
  - `redis.exceptions.ConnectionError: Error 61 connecting to localhost:6379. Connection refused.` - Make sure your Redis server is actually running. You can start it with `redis-server` from the `redis-stable` directory.
- If your error message mentions errors with the `covid` cog or a coronavirus API and you aren't terribly concerned about this feature, disable the cog manually by removing `bot.cogs.covid` from `SCIOLY_ID_BOT_EXTRA_COGS` in `.env`.
- If your error is about missing Discord Permissions, make sure your bot account has permission to send messages, send files, embed links, and manage roles in that channel.

Having other issues not listed here? Ask in our [Discord support server](https://discord.gg/2HbshwGjnm) and we will do our best to solve the problem.

## Files and Folders

The main bot application uses the bot folder.

- `__main__.py` is the application start point, with `functions.py` containing assorted functions assisting with downloading bird files and other commonly used functions.
- The `data` folder stores bird lists, with `data.py` managing those lists along with logging and database tasks.
- The `cogs` folder contains the bot commands themselves, with each file being a different collection of commands (a category in `b!help`).
- The `media` folder contains assorted image files for achievement badges and other things.

Bot unit tests uses the `test` folder. Currently, test coverage is quite poor and these tests are mostly just for fun and learning. If you would like to contribute to tests and increase test coverage, that would be greatly appreciated.

- `discord_mock.py` contains classes to replicate discord.py functionality.
- `test_{COG NAME}.py` contains the tests for the respective cog.

The web API uses the `web` folder. Currently, development of the web API is paused.

`.travis.yml` is the config file for Travis CI, which runs the tests. `travis_pr_script.sh` is a script for Travis that installs and runs a local Redis instance for PRs, since private environment variables in PRs are disabled for security reasons.

`runtime.txt` and `Procfile` are files used by Heroku, where we host the bot.

`.env.example` is the template for the `.env` file (which itself cannot be tracked by git).

### **_Happy Identification!_**
