import random
import asyncio
from sentry_sdk import capture_exception

from flask import abort
from functools import partial
from io import BytesIO
from PIL import Image
from functions import get_sciname, get_files, valid_image_extensions, valid_audio_extensions, spellcheck
from web.data import logger, GenericError, database, birdList, get_session_id, screech_owls


def _black_and_white(input_image_path):
    logger.info("black and white")
    with Image.open(input_image_path) as color_image:
        bw = color_image.convert('L')
        final_buffer = BytesIO()
        bw.save(final_buffer, "png")
    final_buffer.seek(0)
    return final_buffer


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
            fn = partial(_black_and_white, filename)
            file_stream = await loop.run_in_executor(None, fn)
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
    logger.info(f"fetched {media_type}: {str(media)}")
    prevJ = int(str(database.hget(database_key, "prevJ"))[2:-1])
    if media:
        j = (prevJ + 1) % len(media)
        logger.debug("prevJ: " + str(prevJ))
        logger.debug("j: " + str(j))

        for x in range(0, len(media)):  # check file type and size
            y = (x + j) % len(media)
            media_path = media[y]
            extension = media_path.split('.')[-1]
            logger.debug("extension: " + str(extension))
            if (media_type == "images" and extension.lower() in valid_image_extensions) or \
                    (media_type == "songs" and extension.lower() in valid_audio_extensions):
                logger.info("found one!")
                break
            elif y == prevJ:
                j = (j + 1) % (len(media))
                raise GenericError(
                    f"No Valid {media_type.title()} Found", code=999)

        database.hset(database_key, "prevJ", str(j))
    else:
        raise GenericError(f"No {media_type.title()} Found", code=100)

    return media_path, extension
