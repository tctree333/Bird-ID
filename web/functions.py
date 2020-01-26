import asyncio
import random
from functools import partial

from flask import abort
from sentry_sdk import capture_exception

from bot.functions import (
    get_files, get_sciname, spellcheck, valid_audio_extensions, valid_image_extensions, _black_and_white
)
from web.config import get_session_id
from bot.data import (GenericError, birdList, database, logger, screech_owls)

async def send_bird(bird: str, media_type: str, addOn: str = "", bw: bool = False):
    if bird == "":
        logger.error("error - bird is blank")
        abort(406, "Bird is blank")
        return

    if media_type != "images" and media_type != "songs":
        logger.error(f"invalid media type {media_type}")
        abort(406, "Invalid media type")
        return

    # add special condition for screech owls
    # since screech owl is a genus and SciOly
    # doesn't specify a species
    if bird == "Screech Owl":
        logger.info("choosing specific Screech Owl")
        bird = random.choice(screech_owls)

    try:
        filename, ext = await get_media(bird, media_type, addOn)
    except GenericError as e:
        logger.info(e)
        capture_exception(e)
        abort(503, str(e))
        return

    if media_type == "images":
        if bw:
            loop = asyncio.get_running_loop()
            file_stream = await loop.run_in_executor(None, partial(_black_and_white, filename))
        else:
            file_stream = f"../{filename}"
    elif media_type == "songs":
        file_stream = f"../{filename}"

    return file_stream, ext

async def get_media(bird, media_type, addOn=""):  # images or songs
    if bird not in birdList:
        raise GenericError("Invalid Bird", code=990)

    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird

    session_id = get_session_id()
    database_key = f"web.session:{session_id}"

    media = await get_files(sciBird, media_type, addOn)
    logger.info(f"fetched {media_type}: {media}")
    prevJ = int(database.hget(database_key, "prevJ").decode("utf-8"))
    if media:
        j = (prevJ + 1) % len(media)
        logger.info("prevJ: " + str(prevJ))
        logger.info("j: " + str(j))

        for x in range(0, len(media)):  # check file type and size
            y = (x + j) % len(media)
            media_path = media[y]
            extension = media_path.split('.')[-1]
            logger.info("extension: " + str(extension))
            if (media_type == "images" and extension.lower() in valid_image_extensions) or \
                    (media_type == "songs" and extension.lower() in valid_audio_extensions):
                logger.info("found one!")
                break
            elif y == prevJ:
                j = (j + 1) % (len(media))
                raise GenericError(f"No Valid {media_type.title()} Found", code=999)

        database.hset(database_key, "prevJ", str(j))
    else:
        raise GenericError(f"No {media_type.title()} Found", code=100)

    return media_path, extension
