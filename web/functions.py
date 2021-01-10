# functions.py | media related functions
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

import asyncio
import random
from functools import partial

import eyed3
from flask import abort
from sentry_sdk import capture_exception

from bot.core import _black_and_white, get_files, get_sciname, valid_types
from bot.data import GenericError, birdList, database, logger, screech_owls
from bot.filters import Filter
from web.config import get_session_id


async def send_bird(bird: str, media_type: str, filters: Filter):
    if bird == "":
        logger.error("error - bird is blank")
        abort(406, "Bird is blank")

    if media_type not in ("images", "songs"):
        logger.error(f"invalid media type {media_type}")
        abort(406, "Invalid media type")

    # add special condition for screech owls
    # since screech owl is a genus and SciOly
    # doesn't specify a species
    if bird == "Screech Owl":
        logger.info("choosing specific Screech Owl")
        bird = random.choice(screech_owls)

    try:
        filename, ext = await get_media(bird, media_type, filters)
    except GenericError as e:
        logger.info(e)
        capture_exception(e)
        abort(503, str(e))

    if media_type == "images":
        if filters.bw:
            loop = asyncio.get_running_loop()
            file_stream = await loop.run_in_executor(
                None, partial(_black_and_white, filename)
            )
        else:
            file_stream = f"../{filename}"
    elif media_type == "songs":
        # remove spoilers in tag metadata
        audioFile = eyed3.load(filename)
        if audioFile is not None and audioFile.tag is not None:
            audioFile.tag.remove(filename)

        file_stream = f"../{filename}"

    return file_stream, ext


async def get_media(bird, media_type, filters):  # images or songs
    if bird not in birdList + screech_owls:
        raise GenericError("Invalid Bird", code=990)

    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird

    session_id = get_session_id()
    database_key = f"web.session:{session_id}"

    media = await get_files(sciBird, media_type, filters)
    logger.info(f"fetched {media_type}: {media}")
    prevJ = int(database.hget(database_key, "prevJ").decode("utf-8"))
    if media:
        j = (prevJ + 1) % len(media)
        logger.info("prevJ: " + str(prevJ))
        logger.info("j: " + str(j))

        for x in range(0, len(media)):  # check file type and size
            y = (x + j) % len(media)
            media_path = media[y]
            extension = media_path.split(".")[-1]
            logger.info("extension: " + str(extension))
            if (
                media_type in ("images", "songs")
                and extension.lower() in valid_types[media_type].values()
            ):
                logger.info("found one!")
                break
            if y == prevJ:
                raise GenericError(f"No Valid {media_type.title()} Found", code=999)

        database.hset(database_key, "prevJ", str(j))
    else:
        raise GenericError(f"No {media_type.title()} Found", code=100)

    return media_path, extension
