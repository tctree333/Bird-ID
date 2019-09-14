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
# ctx.channel.id : [bird, answered, songbird, songanswered,
#                     totalCorrect (NOT USED), goatsucker, goatsuckeranswered,
#                     prevJ, prevB, prevS, prevK]
# }

# user format = {
# "user":[userid, #ofcorrect]
# }

# incorrect birds format = {
# "incorrect":[bird name, #incorrect]
# }

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
    def __init__(self, message=None):
        super().__init__(message=message)


# Lists of birds, memes, and other info


goatsuckers = ["Common Pauraque", "Chuck-will's-widow", "Whip-poor-will"]
sciGoat = ["Nyctidromus albicollis",
           "Antrostomus carolinensis", "Antrostomus vociferus"]


def _main():
    filenames = ("birdList", "sciBirdList", "memeList",
                 "songBirds", "sciSongBirds")
    # Converts txt file of data into lists
    lists = []
    for filename in filenames:
        logger.info(f"Working on {filename}")
        with open(f'data/{filename}.txt', 'r') as f:
            lists.append([line.strip() for line in f])
        logger.info("Done!")
    return lists


# pylint disable: unbalanced-tuple-unpacking
birdList, sciBirdList, memeList, songBirds, sciSongBirds = _main()
