# data.py | import data from lists
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

import logging
import logging.handlers
import os
import string
import sys

import redis
import sentry_sdk
from discord.ext import commands
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# define database for one connection
database = redis.from_url(os.getenv("REDIS_URL"))

def before_sentry_send(event, hint):
    """Fingerprint certain events before sending to Sentry."""
    if 'exc_info' in hint:
        error = hint['exc_info'][1]
        if isinstance(error, commands.CommandNotFound):
            event['fingerprint'] = ['command-not-found']
        elif isinstance(error, commands.CommandOnCooldown):
            event['fingerprint'] = ['command-cooldown']
    return event

# add sentry logging
sentry_sdk.init(
    release=f"Heroku Release {str(os.getenv('HEROKU_RELEASE_VERSION'))}:{str(os.getenv('HEROKU_SLUG_DESCRIPTION'))}",
    dsn=str(os.getenv("SENTRY_DISCORD_DSN")),
    integrations=[RedisIntegration(), AioHttpIntegration()],
    before_send=before_sentry_send
)

# Database Format Definitions

# prevJ - makes sure it sends a diff image
# prevB - makes sure it sends a diff bird (img)
# prevS - makes sure it sends a diff bird (sounds)
# prevK - makes sure it sends a diff sound

# server format = {
# channel:channel_id : { "bird", "answered", "sBird", "sAnswered",
#                     "goatsucker", "gsAnswered",
#                     "prevJ", "prevB", "prevS", "prevK" }
# }

# session format:
# session.data:user_id : {"start": 0, "stop": 0,
#                         "correct": 0, "incorrect": 0, "total": 0,
#                         "bw": bw, "state": state, "addon": addon}
# session.incorrect:user_id : [bird name, # incorrect]

# race format:
# race.data:ctx.channel.id : { 
#                    "start": 0
#                    "stop": 0,
#                    "limit": 10,
#                    "bw": bw,
#                    "state": state,
#                    "addon": addon,
#                    "media": media
# }
# race.scores:ctx.channel.id : [ctx.author.id, #correct]

# leaderboard format = {
#    users:global : [user id, # of correct]
#    users.server:server_id : [user id, # of correct]
# }

# streaks format = {
#    streak:global : [user id, current streak]
#    streak.max:global : [user id, max streak]
# }

# incorrect birds format = {
#    incorrect:global : [bird name, # incorrect]
#    incorrect.server:server_id : [bird name, # incorrect]
#    incorrect.user:user_id: : [bird name, # incorrect]
# }

# channel score format = {
#   score:global : [channel id, # of correct]
# }

# ban format:
#   banned:global : [user id, 0]

#  states = { state name:
#               {
#               aliases: [alias1, alias2...],
#               birdList: [bird1, bird2...],
#               sciBirdList: [etc.],
#               songBirds: [etc.],
#               sciSongBirds: [etc.]
#               }
#          }

# state birds are picked from state/[state]/birdList or songBirds
# sci lists are only for new, state specific birds
# either lists can be in any order


# setup logging
logger = logging.getLogger("bird-id")
logger.setLevel(logging.DEBUG)
os.makedirs("logs", exist_ok=True)

file_handler = logging.handlers.TimedRotatingFileHandler(
    "logs/log.txt", backupCount=4, when="midnight")
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

file_handler.setFormatter(logging.Formatter(
    "{asctime} - {filename:10} -  {levelname:8} - {message}", style="{"))
stream_handler.setFormatter(logging.Formatter(
    "{filename:10} -  {levelname:8} - {message}", style="{"))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# log uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(
        exc_type, exc_value, exc_traceback))


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
goatsuckers = ["Common Pauraque", "Chuck-will's-widow", "Whip-poor-will"]
sciGoat = ["Nyctidromus albicollis", "Antrostomus carolinensis", "Antrostomus vociferus"]

screech_owls = ["Whiskered Screech-Owl", "Western Screech-Owl", "Eastern Screech-Owl"]
sci_screech_owls = ["Megascops trichopsis", "Megascops kennicottii", "Megascops asio"]


def _wiki_urls():
    logger.info("Working on wiki urls")
    urls = {}
    with open(f'data/wikipedia.txt', 'r') as f:
        for line in f:
            bird = string.capwords(line.strip().split(',')[0].replace("-", " "))
            url = line.strip().split(',')[1]
            urls[bird] = url
    logger.info("Done with wiki urls")
    return urls


def get_wiki_url(bird):
    bird = string.capwords(bird.replace("-", " "))
    return wikipedia_urls[bird]


def _nats_lists():
    """Converts txt files of national bird data into lists."""
    filenames = ("birdList", "sciBirdList", "memeList",
                 "songBirds", "sciSongBirds")
    # Converts txt file of data into lists
    lists = []
    for filename in filenames:
        logger.info(f"Working on {filename}")
        with open(f'data/{filename}.txt', 'r') as f:
            lists.append([string.capwords(line.strip().replace("-", " ")) if filename is not "memeList"
                          else line.strip() for line in f])
        logger.info(f"Done with {filename}")
    logger.info("Done with nats list!")
    return lists


def _orders():
    """Converts txt files of order data into lists."""
    logger.info("Working on order lists")
    logger.info("Working on order master list")
    orders = {}
    with open('data/orders/orders.txt', 'r') as f:
        orders["orders"] = [line.strip().lower() for line in f]
    logger.info("Done with order master list")
    for filename in orders["orders"]:
        logger.info(f"Working on {filename}")
        with open(f'data/orders/{filename}.txt', 'r') as f:
            orders[filename] = [string.capwords(line.strip().replace("-", " ")) for line in f]
        logger.info(f"Done with {filename}")
    logger.info("Done with order lists!")
    return orders


def _state_lists():
    """Converts txt files of state data into lists."""
    filenames = ("birdList", "sciBirdList", "aliases",
                 "songBirds", "sciSongBirds")
    states = {}
    state_names = os.listdir("data/state")
    for state in state_names:
        states[state] = {}
        logger.info(f"Working on {state}")
        for filename in filenames:
            logger.info(f"Working on {filename}")
            with open(f'data/state/{state}/{filename}.txt', 'r') as f:
                states[state][filename] = [
                    string.capwords(line.strip().replace(
                        "-", " ")) if filename is not "aliases" else line.strip()
                    for line in f if line != "EMPTY"
                ]
            logger.info(f"Done with {filename}")
        logger.info(f"Done with {state}")
    logger.info("Done with states list!")
    return states


def _all_birds():
    """Combines all state and national lists."""
    lists = (birdList, sciBirdList, songBirds, sciSongBirds)
    list_names = ("birdList", "sciBirdList", "songBirds", "sciSongBirds")
    master_lists = []
    for bird_list in lists:
        birds = []
        birds += bird_list
        logger.info(f"Working on {list_names[lists.index(bird_list)]}")

        for state in states.values():
            birds += state[list_names[lists.index(bird_list)]]
        master_lists.append(list(set(birds)))
        logger.info(f"Done with {list_names[lists.index(bird_list)]}")
    master_lists[1] += sci_screech_owls
    master_lists[1] += sciGoat
    master_lists[0] += screech_owls
    master_lists[0] += goatsuckers
    logger.info("Done with master lists!")
    return master_lists


birdList, sciBirdList, memeList, songBirds, sciSongBirds = _nats_lists()
states = _state_lists()
birdListMaster, sciBirdListMaster, songBirdsMaster, sciSongBirdsMaster = _all_birds()
orders = _orders()
wikipedia_urls = _wiki_urls()
logger.info(
    f"National Lengths: {len(birdList)}, {len(sciBirdList)}, {len(songBirds)}, {len(sciSongBirds)}")
logger.info(
    f"Master Lengths: {len(birdListMaster)}, {len(sciBirdListMaster)}, {len(songBirdsMaster)}, {len(sciSongBirdsMaster)}"
)
logger.info("Done importing data!")
