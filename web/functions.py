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
import io
from functools import partial
from typing import Union

import eyed3
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sentry_sdk import capture_exception

from bot.core import _black_and_white, get_files, get_sciname
from bot.data import GenericError, birdList, database, logger, screech_owls
from bot.filters import Filter, MediaType
from web.data import get_session_id


def send_file(
    fp: Union[str, io.BufferedIOBase], **kwargs
) -> Union[FileResponse, StreamingResponse]:
    kwargs.setdefault("headers", {})
    kwargs["headers"]["Cache-Control"] = "no-cache"
    if isinstance(fp, str):
        return FileResponse(fp, **kwargs)
    return StreamingResponse(fp, **kwargs)


async def send_bird(
    request: Request, bird: str, media_type: MediaType, filters: Filter
):
    if bird == "":
        logger.error("error - bird is blank")
        raise HTTPException(status_code=404, detail="Bird is blank")

    if not isinstance(media_type, MediaType):
        logger.error(f"invalid media type {media_type}")
        raise HTTPException(status_code=422, detail="Invalid media type")

    # add special condition for screech owls
    # since screech owl is a genus and SciOly
    # doesn't specify a species
    if bird == "Screech Owl":
        logger.info("choosing specific Screech Owl")
        bird = random.choice(screech_owls)

    try:
        filename, ext, content_type = await get_media(
            request, bird, media_type, filters
        )
    except GenericError as e:
        logger.info(e)
        capture_exception(e)
        raise HTTPException(status_code=503, detail=str(e)) from e

    if media_type is MediaType.IMAGE:
        if filters.bw:
            loop = asyncio.get_running_loop()
            file_stream = await loop.run_in_executor(
                None, partial(_black_and_white, filename)
            )
        else:
            file_stream = filename
    elif media_type is MediaType.SONG:
        # remove spoilers in tag metadata
        audioFile = eyed3.load(filename)
        if audioFile is not None and audioFile.tag is not None:
            audioFile.tag.remove(filename)

        file_stream = filename

    return file_stream, ext, content_type


async def get_media(
    request: Request, bird: str, media_type: MediaType, filters: Filter
):  # images or songs
    if bird not in birdList + screech_owls:
        raise GenericError("Invalid Bird", code=990)

    if not isinstance(media_type, MediaType):
        logger.error(f"invalid media type {media_type}")
        raise HTTPException(status_code=422, detail="Invalid media type")

    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird

    session_id = get_session_id(request)
    database_key = f"web.session:{session_id}"

    media = await get_files(sciBird, media_type, filters)
    logger.info(f"fetched {media_type.name()}: {media}")
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
            if extension.lower() in media_type.types().values():
                logger.info("found one!")
                break
            if y == prevJ:
                raise GenericError(
                    f"No Valid {media_type.name().title()} Found", code=999
                )

        database.hset(database_key, "prevJ", str(j))
    else:
        raise GenericError(f"No {media_type.name().title()} Found", code=100)

    return media_path, extension, MediaType.content_type_lookup(extension)
