# data/__init__.py | import data from lists
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

import csv
import logging
import logging.handlers
import os
import string
import sys
from typing import Dict, List

import redis
import sentry_sdk
import wikipedia
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration

load_dotenv(find_dotenv(), verbose=True)


# define database for one connection
if os.getenv("SCIOLY_ID_BOT_LOCAL_REDIS") == "true":
    host = os.getenv("SCIOLY_ID_BOT_LOCAL_REDIS_HOST")
    if host is None:
        host = "localhost"
    database = redis.Redis(host=host, port=6379, db=0)
else:
    database = redis.from_url(os.getenv("REDIS_URL"))


def before_sentry_send(event, hint):
    """Fingerprint certain events before sending to Sentry."""
    if "exc_info" in hint:
        error = hint["exc_info"][1]
        if isinstance(error, commands.CommandNotFound):
            event["fingerprint"] = ["command-not-found"]
        elif isinstance(error, commands.CommandOnCooldown):
            event["fingerprint"] = ["command-cooldown"]
    return event


# add sentry logging
if os.getenv("SCIOLY_ID_BOT_USE_SENTRY") != "false":
    sentry_sdk.init(
        release=f"{os.getenv('CURRENT_PLATFORM', 'LOCAL')} Release "
        + (
            f"{os.getenv('GIT_REV', '')[:8]}"
            if os.getenv("CURRENT_PLATFORM") != "Heroku"
            else f"{os.getenv('HEROKU_RELEASE_VERSION')}:{os.getenv('HEROKU_SLUG_DESCRIPTION')}"
        ),
        dsn=os.getenv("SCIOLY_ID_BOT_SENTRY_DISCORD_DSN"),
        integrations=[RedisIntegration(), AioHttpIntegration()],
        before_send=before_sentry_send,
    )

# Database Format Definitions

# server format:
# channel:channel_id : {
#                    "bird",
#                    "answered",
#                    "prevB", (make sure it sends diff birds)
#                    "prevJ" (make sure it sends diff media)
# }

# session format:
# session.data:user_id : {
#                    "start": 0,
#                    "stop": 0,
#                    "correct": 0,
#                    "incorrect": 0,
#                    "total": 0,
#                    "state": state,
#                    "filter": filter (int),
#                    "wiki": wiki, - Enables if "wiki", disables if empty (""), default "wiki"
#                    "strict": strict - Enables strict spelling if "strict", disables if empty, default ""
# }
# session.incorrect:user_id : [bird name, # incorrect]

# race format:
# race.data:ctx.channel.id : {
#                    "start": 0
#                    "stop": 0,
#                    "limit": 10,
#                    "state": state,
#                    "filter": filter (int),
#                    "media": media,
#                    "taxon": taxon,
#                    "strict": strict - Enables strict spelling if "strict", disables if empty, default "",
#                    "alpha": alpha - Enables alpha codes if "alpha", disables if empty, default ""
# }
# race.scores:ctx.channel.id : [ctx.author.id, #correct]

# voice formats:
# voice.server:guild_id : channel_id

# leaderboard formats:
#    users:global : [user id, # of correct]
#    users.server.id:guild_id : [user id ... ]

# streaks format:
#    streak:global : [user id, current streak]
#    streak.max:global : [user id, max streak]

# incorrect birds format:
#    incorrect:global : [bird name, # incorrect]
#    incorrect.server:guild_id : [bird name, # incorrect]
#    incorrect.user:user_id: : [bird name, # incorrect]

# correct birds format:
#    correct.user:user_id : [bird name, # correct]

# bird frequency format:
#   frequency.bird:global : [bird name, # displayed]

# command frequency format:
#   frequency.command:global : [command, # used]

# channel score format:
#   score:global : [channel id, # of correct]
#   channels:guild_id : [channel id ... ]

# daily update format:
#     daily.score:YYYY-MM-DD : [user id, # correct today]
#     daily.incorrect:YYYY-MM-DD : [bird name, # incorrect today]
#     daily.web:YYYY-MM-DD : [("check", "skip", "hint"), daily value]
#     daily.webscore:YYYY-MM-DD : [user id, # correct today]

# ban format:
#   banned:global : [user id, 0]

# ignore format:
#   ignore:global : [channel id, guild id]

# leave confirm format:
#   leave:guild_id : 0

# custom list confirm format:
#   custom.confirm:user_id : "valid" after server list validation
#                            "confirm" after user list validation
#                            "delete" if user is about to delete lists

# custom list cooldown format:
#   custom.cooldown:user_id : 0

# custom list format (set):
#   custom.list:user_id : [validated birds, ...]

# cooldown rate limit format:
#   cooldown:global : 0

# media type, bird, and filter media frequency format:
# (for media eviction)
#   frequency.media:global : ["{type}/{sciname}{filter}", count]

# media cursor format:
#   media.cursor:{type}/{sciname}{filter} : cursor

#  states = {
#          state name:
#               {
#               aliases: [alias1, alias2...],
#               birdList: [bird1, bird2...],
#               songBirds: [etc.],
#               }
#          }

# cookie expiration:
#  cookies.expired:global : "false"
#  set expiration to autoremove this key

# state birds are picked from state/[state]/birdList or songBirds
# either list can be in any taxon


# setup logging
logger = logging.getLogger("bird-id")
discordLogger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
discordLogger.setLevel(logging.INFO)
os.makedirs("bot_files/logs", exist_ok=True)

file_handler = logging.handlers.TimedRotatingFileHandler(
    "bot_files/logs/log.txt", backupCount=4, when="midnight"
)
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

file_handler.setFormatter(
    logging.Formatter(
        "{asctime} - {filename:10} -  {levelname:8} - {message}", style="{"
    )
)
stream_handler.setFormatter(
    logging.Formatter("{filename:12} -  {levelname:8} - {message}", style="{")
)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
discordLogger.addHandler(file_handler)
discordLogger.addHandler(stream_handler)

# log uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


class GenericError(commands.CommandError):
    """A custom error class.

    Error codes: (can add more if needed)\n
        0 - no code
        111 - Index Error
        201 - HTTP Error
        999 - Invalid
        990 - Invalid Input
        100 - Blank
        842 - Banned User
        192 - Ignored Channel
        666 - No output error
    """

    def __init__(self, message=None, code=0):
        self.code = code
        super().__init__(message=message)


# Error codes: (can add more if needed)
# 0 - no code
# 111 - Index Error
# 201 - HTTP Error
# 999 - Invalid
# 990 - Invalid Input
# 100 - Blank
# 842 - Banned User
# 666 - No output error

# Lists of birds, memes, and other info
goatsuckers = ["Common Pauraque", "Chuck Will's Widow", "Eastern Whip Poor Will"]
# sciGoat = [
#     "Nyctidromus albicollis",
#     "Antrostomus carolinensis",
#     "Antrostomus vociferus",
# ]

screech_owls = ["Whiskered Screech Owl", "Western Screech Owl", "Eastern Screech Owl"]
sci_screech_owls = ["Megascops trichopsis", "Megascops kennicottii", "Megascops asio"]


def _wiki_urls() -> Dict[str, str]:
    logger.info("Working on wiki urls")
    urls = {}
    with open("bot/data/wikipedia.txt", "r") as f:
        r = csv.reader(f)
        for bird, url in r:
            urls[string.capwords(bird.replace("-", " "))] = url
    logger.info("Done with wiki urls")
    return urls


def get_wiki_url(ctx, bird: str = None) -> str:
    logger.info("fetching wiki url")
    if bird is None:
        bird = ctx
        user_id = 0
        channel_id = 0
    else:
        user_id = ctx.author.id
        channel_id = ctx.channel.id

    bird = string.capwords(bird.replace("-", " "))
    url = wikipedia_urls.get(bird, "")
    if not url:
        logger.info(f"{bird} not found in wikipedia url cache, falling back")
        page = wikipedia.page(bird)
        url = page.url
    else:
        logger.info("found in cache")

    if database.hget(f"session.data:{user_id}", "wiki") == b"" or database.exists(
        f"race.data:{channel_id}"
    ):
        logger.info("disabling preview")
        url = f"<{url}>"

    return url


def _alpha_codes() -> Dict[str, str]:
    logger.info("Working on alpha codes")
    lookup = {}
    with open("bot/data/alpha.txt", "r") as f:
        r = csv.reader(f)
        for bird, code in r:
            bird = string.capwords(bird.strip().replace("-", " "))
            code = code.strip().upper()
            lookup[bird] = code
            lookup[code] = bird
    logger.info("Done with alpha codes")
    return lookup


def _nats_lists() -> List[List[str]]:
    """Converts txt files of national bird data into lists."""
    filenames = ("birdList", "songBirds", "sciListMaster", "memeList")
    # Converts txt file of data into lists
    lists = []
    for filename in filenames:
        logger.info(f"Working on {filename}")
        with open(f"bot/data/{filename}.txt", "r") as f:
            lists.append(
                [
                    string.capwords(line.strip().replace("-", " "))
                    if filename != "memeList"
                    else line.strip()
                    for line in f
                ]
            )
        logger.info(f"Done with {filename}")
    logger.info("Done with nats list!")
    return lists


def _taxons() -> Dict[str, List[str]]:
    """Converts txt files of taxon data into lists."""
    logger.info("Working on taxon lists")
    logger.info("Working on taxon master list")
    taxon_lists = {}
    logger.info("Done with taxon master list")
    for directory in os.listdir("bot/data/taxons"):
        for filename in os.listdir(f"bot/data/taxons/{directory}"):
            logger.info(f"Working on {filename}")
            with open(f"bot/data/taxons/{directory}/{filename}", "r") as f:
                taxon_lists[filename[: filename.rfind(".")]] = [
                    string.capwords(line.strip().replace("-", " ")) for line in f
                ]
            logger.info(f"Done with {filename}")
    logger.info("Done with taxon lists!")
    return taxon_lists


def _state_lists():
    """Converts txt files of state data into lists."""
    filenames = ("birdList", "songBirds", "aliases")
    states_: Dict[str, Dict[str, List[str]]] = {}
    state_names = os.listdir("bot/data/state")
    for state in state_names:
        states_[state] = {}
        logger.info(f"Working on {state}")
        for filename in filenames:
            logger.info(f"Working on {filename}")
            with open(f"bot/data/state/{state}/{filename}.txt", "r") as f:
                states_[state][filename] = [
                    string.capwords(line.strip().replace("-", " "))
                    if filename != "aliases"
                    else line.strip()
                    for line in f
                    if line != "EMPTY"
                ]
            logger.info(f"Done with {filename}")
        logger.info(f"Done with {state}")
    logger.info("Done with states list!")
    return states_


def _all_birds() -> List[str]:
    """Combines all state and national lists."""
    logger.info("Working on master lists")
    birds = []
    birds += birdList
    for state in states.values():
        birds += state["birdList"]
    birds += screech_owls
    birds += goatsuckers
    birds = list(set(birds))
    logger.info("Done with master lists!")
    return birds


(  # pylint: disable=unbalanced-tuple-unpacking
    birdList,
    songBirds,
    sciListMaster,
    memeList,
) = _nats_lists()
states = _state_lists()
birdListMaster = _all_birds()
taxons = _taxons()
wikipedia_urls = _wiki_urls()
alpha_codes = _alpha_codes()
logger.info(f"National Lengths: {len(birdList)}, {len(songBirds)}")
logger.info(f"Master Lengths: {len(birdListMaster)}, {len(sciListMaster)}")
logger.info("Done importing data!")
