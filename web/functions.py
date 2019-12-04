from functions import get_sciname, get_files, valid_image_extensions, valid_audio_extensions
from web.data import logger, GenericError, database, birdList, get_session_id


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

    return [media_path, extension]
