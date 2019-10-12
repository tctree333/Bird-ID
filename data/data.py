# data.py | import data from lists
# Copyright (C) 2019  EraserBird, person_v1.32, hmmm

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
from discord.ext import commands

# define database for one connection
database = redis.from_url(os.getenv("REDIS_URL"))

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

# leaderboard format = {
#    "users:global":[user id, # of correct]
#    "users.server:server_id":[user id, # of correct]
# }

# incorrect birds format = {
#    "incorrect:global":[bird name, # incorrect]
#    "incorrect.server:server_id":[bird name, # incorrect]
#    "incorrect.user:user_id:":[bird name, # incorrect]
# }

# channel score format = {
#   "score:global":[channel id, # of correct]
# }

# setup logging
logger = logging.getLogger("bird-id")
logger.setLevel(logging.DEBUG)
os.makedirs("logs", exist_ok=True)

file_handler = logging.handlers.TimedRotatingFileHandler("logs/log.txt", backupCount=4, when="midnight")
file_handler.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

file_handler.setFormatter(logging.Formatter("{asctime} - {filename:10} -  {levelname:8} - {message}", style="{"))
stream_handler.setFormatter(logging.Formatter("{filename:10} -  {levelname:8} - {message}", style="{"))

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# log uncaught exceptions

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

class GenericError(commands.CommandError):
    def __init__(self, message=None, code=0):
        self.code = code
        super().__init__(message=message)

# Error codes: (can add more if needed)
# 0 - no code
# 111 - Index Error
# 201 - HTTP Error
# 999 - Invalid
# 100 - Blank

# Lists of birds, memes, and other info
goatsuckers = ["Common Pauraque", "Chuck-will's-widow", "Whip-poor-will"]
sciGoat = ["Nyctidromus albicollis", "Antrostomus carolinensis", "Antrostomus vociferus"]

def _nats_lists():
    filenames = ("birdList", "sciBirdList", "memeList", "songBirds", "sciSongBirds")
    # Converts txt file of data into lists
    lists = []
    for filename in filenames:
        logger.info(f"Working on {filename}")
        with open(f'data/{filename}.txt', 'r') as f:
            lists.append([string.capwords(line.strip().replace("-", " ")) for line in f])
        logger.info(f"Done with {filename}")
    logger.info("Done with nats list!")
    return lists

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

def _state_lists():
    filenames = ("birdList", "sciBirdList", "aliases", "songBirds", "sciSongBirds")
    states = {}
    state_names = os.listdir("data/state")
    for state in state_names:
        states[state] = {}
        logger.info(f"Working on {state}")
        for filename in filenames:
            logger.info(f"Working on {filename}")
            with open(f'data/state/{state}/{filename}.txt', 'r') as f:
                states[state][filename] = [
                    string.capwords(line.strip().replace("-", " ")) if filename is not "aliases" else line.strip()
                    for line in f if line != "EMPTY"
                ]
            logger.info(f"Done with {filename}")
        logger.info(f"Done with {state}")
    logger.info("Done with states list!")
    return states

def _all_birds():
    lists = (birdList, sciBirdList, songBirds, sciSongBirds)
    list_names = ("birdList", "sciBirdList", "songBirds", "sciSongBirds")
    master_lists = []
    for bird_list in lists:
        birds = []
        birds += bird_list
        logger.info(f"Working on {list_names[lists.index(bird_list)]}")

        for state in states.values():
            birds += state[list_names[lists.index(bird_list)]]
        master_lists.append(birds)
        logger.info(f"Done with {list_names[lists.index(bird_list)]}")
    logger.info("Done with master lists!")
    return master_lists

birdList, sciBirdList, memeList, songBirds, sciSongBirds = _nats_lists()
states = _state_lists()
birdListMaster, sciBirdListMaster, songBirdsMaster, sciSongBirdsMaster = _all_birds()
logger.info(f"National Lengths: {len(birdList)}, {len(sciBirdList)}, {len(songBirds)}, {len(sciSongBirds)}")
logger.info(
    f"Master Lengths: {len(birdListMaster)}, {len(sciBirdListMaster)}, {len(songBirdsMaster)}, {len(sciSongBirdsMaster)}"
)
