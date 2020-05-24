# core.py | core media fetching functions
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

import asyncio
import contextlib
import difflib
import functools
import os
import random
import shutil
import string
import time
import urllib
from io import BytesIO
from mimetypes import guess_all_extensions, guess_extension

import aiohttp
import discord
import eyed3
from PIL import Image
from sentry_sdk import capture_exception

from bot.data import (GenericError, database, logger, sciBirdListMaster,
                      sciSongBirdsMaster, screech_owls)

# Macaulay URL definitions
CATALOG_URL = (
    "https://search.macaulaylibrary.org/catalog.json?searchField=species" +
    "&taxonCode={}&count={}&mediaType={}&sex={}&age={}&behavior={}&qua=3,4,5"
)
SCINAME_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&species={}"
TAXON_CODE_URL = "https://search.macaulaylibrary.org/api/v1/find/taxon?q={}"
COUNT = 20  # set this to include a margin of error in case some urls throw error code 476 due to still being processed

# Valid file types
valid_image_extensions = {"jpg", "png", "jpeg", "gif"}
valid_audio_extensions = {"mp3", "wav"}

def cache(func=None):
    """Cache decorator based on functools.lru_cache.

    This does not have a max_size and does not evict items.
    In addition, results are only cached by the first provided argument.
    """
    def wrapper(func):
        sentinel = object()

        cache = {}
        hits = misses = 0
        cache_get = cache.get
        cache_len = cache.__len__

        async def wrapped(*args, **kwds):
            # Simple caching without ordering or size limit
            logger.info("checking cache")
            nonlocal hits, misses
            key = hash(args[0])
            result = cache_get(key, sentinel)
            if result is not sentinel:
                logger.info(f"{args[0]} found in cache!")
                hits += 1
                return result
            logger.info(f"did not find {args[0]} in cache")
            misses += 1
            result = await func(*args, **kwds)
            cache[key] = result
            return result

        def cache_info():
            """Report cache statistics"""
            return functools._CacheInfo(hits, misses, None, cache_len())

        wrapped.cache_info = cache_info
        return functools.update_wrapper(wrapped, func)

    if func:
        return wrapper(func)
    else:
        return wrapper

@cache()
async def get_sciname(bird: str, session=None, retries=0) -> str:
    """Returns the scientific name of a bird.

    Scientific names are found using the eBird API from the Cornell Lab of Ornithology,
    using `SCINAME_URL` to fetch data.
    Raises a `GenericError` if a scientific name is not found or an HTTP error occurs.

    `bird` (str) - common/scientific name of the bird you want to look up\n
    `session` (optional) - an aiohttp client session
    """
    logger.info(f"getting sciname for {bird}")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        try:
            code = (await get_taxon(bird, session))[0]
        except GenericError as e:
            if e.code == 111:
                code = bird
            else:
                raise

        sciname_url = SCINAME_URL.format(urllib.parse.quote(code))
        async with session.get(sciname_url) as sciname_response:
            if sciname_response.status != 200:
                if retries >= 3:
                    logger.info("Retried more than 3 times. Aborting...")
                    raise GenericError(
                        f"An http error code of {sciname_response.status} occured" +
                        f" while fetching {sciname_url} for {bird}",
                        code=201
                    )
                else:
                    logger.info(f"An HTTP error occurred; Retries: {retries}")
                    retries += 1
                    sciname = await get_sciname(bird, session, retries)
                    return sciname
            sciname_data = await sciname_response.json()
            try:
                sciname = sciname_data[0]["sciName"]
            except IndexError:
                raise GenericError(f"No sciname found for {code}", code=111)
    logger.info(f"sciname: {sciname}")
    return sciname

@cache()
async def get_taxon(bird: str, session=None, retries=0) -> str:
    """Returns the taxonomic code of a bird.

    Taxonomic codes are used by the Cornell Lab of Ornithology to identify species of birds.
    This function uses the Macaulay Library's internal API to fetch the taxon code
    from the common or scientific name, using `TAXON_CODE_URL`.
    Raises a `GenericError` if a code is not found or if an HTTP error occurs.

    `bird` (str) - common/scientific name of bird you want to look up\n
    `session` (optional) - an aiohttp client session
    """
    logger.info(f"getting taxon code for {bird}")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        taxon_code_url = TAXON_CODE_URL.format(urllib.parse.quote(bird.replace("-", " ").replace("'s", "")))
        async with session.get(taxon_code_url) as taxon_code_response:
            if taxon_code_response.status != 200:
                if retries >= 3:
                    logger.info("Retried more than 3 times. Aborting...")
                    raise GenericError(
                        f"An http error code of {taxon_code_response.status} occured" +
                        f" while fetching {taxon_code_url} for {bird}",
                        code=201
                    )
                else:
                    logger.info(f"An HTTP error occurred; Retries: {retries}")
                    retries += 1
                    taxon_code = (await get_taxon(bird, session, retries))[0]
                    return taxon_code
            taxon_code_data = await taxon_code_response.json()
            try:
                logger.info(f"raw data: {taxon_code_data}")
                taxon_code = taxon_code_data[0]["code"]
                item_name = taxon_code_data[0]["name"]
                logger.info(f"first item: {taxon_code_data[0]}")
                if len(taxon_code_data) > 1:
                    logger.info("entering check")
                    for item in taxon_code_data:
                        logger.info(f"checking: {item}")
                        if spellcheck(item["name"].split(" - ")[0], bird,
                                      4) or spellcheck(item["name"].split(" - ")[1], bird, 4):
                            logger.info("ok")
                            taxon_code = item["code"]
                            item_name = item["name"]
                            break
                        logger.info("fail")
            except IndexError:
                raise GenericError(f"No taxon code found for {bird}", code=111)
    logger.info(f"taxon code: {taxon_code}")
    logger.info(f"name: {item_name}")
    return (taxon_code, item_name)

async def valid_bird(bird: str, session=None):
    """Checks if a bird is valid.

    This checks first if Macaulay has a valid taxon code for the bird,
    then if Macaulay has valid media for the bird based on the requested
    media type. Media can be `p` for pictures, `a` for audio, or `v` for video.

    Returns a tuple: `(input bird, valid bool, reason, detected name (may be empty string))`.
    """
    bird = string.capwords(bird)
    logger.info(f"checking if {bird} is valid")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        try:
            name = (await get_taxon(bird, session))[1]
        except GenericError as e:
            if e.code in (111, 201):
                return (bird, False, "No taxon code found", "")
            raise e
        urls = await _get_urls(session, bird, "p")
        if len(urls) < 2:
            return (bird, False, "One or less images found", name)
        return (bird, True, "All checks passed", name)

def _black_and_white(input_image_path) -> BytesIO:
    """Returns a black and white version of an image.

    Output type is a file object (BytesIO).

    `input_image_path` - path to image (string) or file object
    """
    logger.info("black and white")
    with Image.open(input_image_path) as color_image:
        bw = color_image.convert('L')
        final_buffer = BytesIO()
        bw.save(final_buffer, "png")
    final_buffer.seek(0)
    return final_buffer

async def send_bird(ctx, bird: str, on_error=None, message=None, addOn="", bw=False):
    """Gets a bird picture and sends it to the user.

    `ctx` - Discord context object\n
    `bird` (str) - bird picture to send\n
    `on_error` (function)- function to run when an error occurs\n
    `message` (str) - text message to send before bird picture\n
    `addOn` (str) - string to append to search for female/juvenile birds\n
    `bw` (bool) - whether the image should be black and white (converts with `_black_and_white()`)
    """
    if bird == "":
        logger.error("error - bird is blank")
        await ctx.send("**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    # add special condition for screech owls
    # since screech owl is a genus and SciOly
    # doesn't specify a species
    if bird == "Screech Owl":
        logger.info("choosing specific Screech Owl")
        bird = random.choice(screech_owls)

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()

    try:
        response = await get_image(ctx, bird, addOn)
    except GenericError as e:
        await delete.delete()
        await ctx.send(f"**An error has occurred while fetching images.**\n*Please try again.*\n**Reason:** {e}")
        logger.exception(e)
        if on_error is not None:
            on_error(ctx)
        return

    filename = str(response[0])
    extension = str(response[1])
    statInfo = os.stat(filename)
    if statInfo.st_size > 4000000:  # another filesize check (4mb)
        await delete.delete()
        await ctx.send("**Oops! File too large :(**\n*Please try again.*")
    else:
        if bw:
            # prevent the black and white conversion from blocking
            loop = asyncio.get_running_loop()
            fn = functools.partial(_black_and_white, filename)
            file_stream = await loop.run_in_executor(None, fn)
        else:
            file_stream = filename

        if message is not None:
            await ctx.send(message)

        # change filename to avoid spoilers
        file_obj = discord.File(file_stream, filename=f"bird.{extension}")
        await ctx.send(file=file_obj)
        await delete.delete()

async def send_birdsong(ctx, bird: str, on_error=None, message=None):
    """Gets a bird sound and sends it to the user.

    `ctx` - Discord context object\n
    `bird` (str) - bird picture to send\n
    `on_error` (function) - function to run when an error occurs\n
    `message` (str) - text message to send before bird picture
    """
    if bird == "":
        logger.error("error - bird is blank")
        await ctx.send("**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()

    try:
        response = await get_song(ctx, bird)
    except GenericError as e:
        await delete.delete()
        await ctx.send(f"**An error has occurred while fetching songs.**\n*Please try again.*\n**Reason:** {e}")
        logger.exception(e)
        if on_error is not None:
            on_error(ctx)
        return

    filename = str(response[0])
    extension = str(response[1])

    # remove spoilers in tag metadata
    audioFile = eyed3.load(filename)
    if audioFile is not None and audioFile.tag is not None:
        audioFile.tag.remove(filename)

    statInfo = os.stat(filename)
    if statInfo.st_size > 4000000:  # another filesize check (4mb)
        await delete.delete()
        await ctx.send("**Oops! File too large :(**\n*Please try again.*")
    else:
        with open(filename, 'rb') as img:
            if message is not None:
                await ctx.send(message)
            # change filename to avoid spoilers
            await ctx.send(file=discord.File(img, filename="bird." + extension))
            await delete.delete()

async def get_image(ctx, bird, addOn=None):
    """Chooses an image from a list of images.

    This function chooses a valid image to pass to send_bird().
    Valid images are based on file extension and size. (8mb discord limit)

    Returns a list containing the file path and extension type.

    `ctx` - Discord context object\n
    `bird` (str) - bird to get image of\n
    `addOn` (str) - string to append to search for female/juvenile birds\n
    """

    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird
    images = await get_files(sciBird, "images", addOn)
    logger.info("images: " + str(images))
    prevJ = int(str(database.hget(f"channel:{ctx.channel.id}", "prevJ"))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if images:
        j = (prevJ + 1) % len(images)
        logger.info("prevJ: " + str(prevJ))
        logger.info("j: " + str(j))

        for x in range(0, len(images)):  # check file type and size
            y = (x + j) % len(images)
            image_link = images[y]
            extension = image_link.split('.')[-1]
            logger.info("extension: " + str(extension))
            statInfo = os.stat(image_link)
            logger.info("size: " + str(statInfo.st_size))
            if extension.lower() in valid_image_extensions and statInfo.st_size < 4000000:  # keep files less than 4mb
                logger.info("found one!")
                break
            elif y == prevJ:
                raise GenericError("No Valid Images Found", code=999)

        database.hset(f"channel:{ctx.channel.id}", "prevJ", str(j))
    else:
        raise GenericError("No Images Found", code=100)

    return [image_link, extension]

async def get_song(ctx, bird):
    """Chooses a song from a list of songs.

    This function chooses a valid song to pass to send_birdsong().
    Valid songs are based on file extension and size. (8mb discord limit)

    Returns a list containing the file path and extension type.

    `ctx` - Discord context object\n
    `bird` (str) - bird to get song of
    """

    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird
    songs = await get_files(sciBird, "songs")
    logger.info("songs: " + str(songs))
    prevK = int(str(database.hget(f"channel:{ctx.channel.id}", "prevK"))[2:-1])
    if songs:
        k = (prevK + 1) % len(songs)
        logger.info("prevK: " + str(prevK))
        logger.info("k: " + str(k))

        for x in range(0, len(songs)):  # check file type and size
            y = (x + k) % len(songs)
            song_link = songs[y]
            extension = song_link.split('.')[-1]
            logger.info("extension: " + str(extension))
            statInfo = os.stat(song_link)
            logger.info("size: " + str(statInfo.st_size))
            if extension.lower() in valid_audio_extensions and statInfo.st_size < 4000000:  # keep files less than 4mb
                logger.info("found one!")
                break
            elif y == prevK:
                raise GenericError("No Valid Songs Found", code=999)

        database.hset(f"channel:{ctx.channel.id}", "prevK", str(k))
    else:
        raise GenericError("No Songs Found", code=100)

    return [song_link, extension]

async def get_files(sciBird, media_type, addOn="", retries=0):
    """Returns a list of image/song filenames.

    This function also does cache management,
    looking for files in the cache for media and
    downloading images to the cache if not found.

    `sciBird` (str) - scientific name of bird\n
    `media_type` (str) - type of media (images/songs)\n
    `addOn` (str) - string to append to search for female/juvenile birds\n
    """
    logger.info(f"get_files retries: {retries}")
    directory = f"cache/{media_type}/{sciBird}{addOn}/"
    try:
        logger.info("trying")
        files_dir = os.listdir(directory)
        logger.info(directory)
        if not files_dir:
            raise GenericError("No Files", code=100)
        return [f"{directory}{path}" for path in files_dir]
    except (FileNotFoundError, GenericError):
        logger.info("fetching files")
        # if not found, fetch images
        logger.info("scibird: " + str(sciBird))
        filenames = await download_media(sciBird, media_type, addOn, directory)
        if not filenames:
            if retries < 3:
                retries += 1
                return await get_files(sciBird, media_type, addOn, retries)
            else:
                logger.info("More than 3 retries")
        return filenames

async def download_media(bird, media_type, addOn="", directory=None, session=None):
    """Returns a list of filenames downloaded from Macaulay Library.
    
    This function manages the download helpers to fetch images from Macaulay.

    `bird` (str) - scientific name of bird\n
    `media_type` (str) - type of media (images/songs)\n
    `addOn` (str) - string to append to search for female/juvenile birds\n
    `directory` (str) - relative path to bird directory\n
    `session` (aiohttp ClientSession)
    """
    if directory is None:
        directory = f"cache/{media_type}/{bird}{addOn}/"

    if addOn == "female":
        sex = "f"
    else:
        sex = ""

    if addOn == "juvenile":
        age = "j"
    else:
        age = ""

    if media_type == "images":
        media = "p"
    elif media_type == "songs":
        media = "a"

    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        urls = await _get_urls(session, bird, media, sex, age)
        if not os.path.exists(directory):
            os.makedirs(directory)
        paths = [f"{directory}{i}" for i in range(len(urls))]
        filenames = await asyncio.gather(*(_download_helper(path, url, session) for path, url in zip(paths, urls)))
        logger.info(f"downloaded {media_type} for {bird}")
        logger.info(f"returned filename count: {len(filenames)}")
        logger.info(f"actual filenames count: {len(os.listdir(directory))}")
        return filenames

async def _get_urls(session, bird, media_type, sex="", age="", sound_type="", retries=0):
    """Returns a list of urls to Macaulay Library media.

    The amount of urls returned is specified in `COUNT`. 
    Media URLs are fetched using Macaulay Library's internal JSON API, 
    with `CATALOG_URL`. Raises a `GenericError` if fails.\n
    Some urls may return an error code of 476 (because it is still being processed), 
    if so, ignore that url.

    `session` (aiohttp ClientSession)\n
    `bird` (str) - can be either common name or scientific name\n
    `media_type` (str) - either `p` for pictures, `a` for audio, or `v` for video\n
    `sex` (str) - `m`, `f`, or blank\n
    `age` (str) - `a` for adult, `j` for juvenile, `i` for immature (may not have many), or blank\n
    `sound_type` (str) - `s` for song, `c` for call, or blank\n
    """
    logger.info(f"getting file urls for {bird}")
    taxon_code = (await get_taxon(bird, session))[0]
    catalog_url = CATALOG_URL.format(taxon_code, COUNT, media_type, sex, age, sound_type)
    async with session.get(catalog_url) as catalog_response:
        if catalog_response.status != 200:
            if retries >= 3:
                logger.info("Retried more than 3 times. Aborting...")
                raise GenericError(
                    f"An http error code of {catalog_response.status} occured " +
                    f"while fetching {catalog_url} for a {'image'if media_type=='p' else 'song'} for {bird}",
                    code=201
                )
            else:
                retries += 1
                logger.info(f"An HTTP error occurred; Retries: {retries}")
                urls = await _get_urls(session, bird, media_type, sex, age, sound_type, retries)
                return urls
        catalog_data = await catalog_response.json()
        content = catalog_data["results"]["content"]

        logger.info("checking filesizes")
        urls = await asyncio.gather(*(_check_media_url(session, data["mediaUrl"]) for data in content))
        fails = urls.count(None)
        if None in urls:
            urls = set(urls)
            urls.remove(None)
            urls = list(urls)
        logger.info(f"filesize check fails: {fails}")
        return urls

async def _check_media_url(session, media_url):
    async with session.head(media_url) as header_check:
        media_size = header_check.headers.get("content-length")
        if header_check.status == 200 and media_size != None and int(media_size) < 4000000:
            return media_url
    return None

async def _download_helper(path, url, session):
    """Downloads media from the given URL.

    Returns the file path to the downloaded item.

    `path` (str) - path with filename of location to download, no extension\n
    `url` (str) - url to the item to be downloaded\n
    `session` (aiohttp ClientSession)
    """
    try:
        async with session.get(url) as response:
            # from https://stackoverflow.com/questions/29674905/convert-content-type-header-into-file-extension
            content_type = response.headers['content-type'].partition(';')[0].strip()
            if content_type.partition("/")[0] == "image":
                try:
                    ext = "." + \
                                                      (set(ext[1:] for ext in guess_all_extensions(
                        content_type)).intersection(valid_image_extensions)).pop()
                except KeyError:
                    raise GenericError(f"No valid extensions found. Extensions: {guess_all_extensions(content_type)}")

            elif content_type.partition("/")[0] == "audio":
                try:
                    ext = "." + (
                        set(ext[1:] for ext in guess_all_extensions(content_type)).intersection(valid_audio_extensions)
                    ).pop()
                except KeyError:
                    raise GenericError(f"No valid extensions found. Extensions: {guess_all_extensions(content_type)}")

            else:
                ext = guess_extension(content_type)
                if ext is None:
                    raise GenericError(f"No extensions found.")
            logger.info(f"download helper - detected extension: {ext} with content type {content_type}")
            filename = f"{path}{ext}"
            # from https://stackoverflow.com/questions/38358521/alternative-of-urllib-urlretrieve-in-python-3-5
            with open(filename, 'wb') as out_file:
                block_size = 1024 * 8
                while True:
                    block = await response.content.read(block_size)  # pylint: disable=no-member
                    if not block:
                        break
                    out_file.write(block)
            return filename
    except aiohttp.ClientError as e:
        logger.info(f"Client Error with url {url} and path {path}")
        capture_exception(e)
        raise

async def precache():
    """Downloads all images and songs.

    This function downloads all images and songs in the bird lists,
    including females and juveniles.

    This function is run with a task every 24 hours.
    """
    logger.info("clear cache")
    try:
        shutil.rmtree(r'cache/images/', ignore_errors=True)
        logger.info("Cleared image cache.")
    except FileNotFoundError:
        logger.info("Already cleared image cache.")

    try:
        shutil.rmtree(r'cache/songs/', ignore_errors=True)
        logger.info("Cleared songs cache.")
    except FileNotFoundError:
        logger.info("Already cleared songs cache.")

    output = dict()
    output["start"] = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=10 * 60)
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        logger.info("Starting cache")
        await asyncio.gather(*(download_media(bird, "images", session=session) for bird in sciBirdListMaster))
        output["plain"] = (time.perf_counter() - output["start"])
        logger.info("Starting females")
        await asyncio.gather(
            *(download_media(bird, "images", addOn="female", session=session) for bird in sciBirdListMaster)
        )
        output["female"] = (time.perf_counter() - output["start"]) - output["plain"]
        logger.info("Starting juveniles")
        await asyncio.gather(
            *(download_media(bird, "images", addOn="juvenile", session=session) for bird in sciBirdListMaster)
        )
        output["juvenile"] = (time.perf_counter()- output["start"]) - output["female"]
        logger.info("Starting songs")
        await asyncio.gather(*(download_media(bird, "songs", session=session) for bird in sciSongBirdsMaster))
        output["songs"] = (time.perf_counter() - output["start"]) - output["juvenile"]
    output["end"] = time.perf_counter()
    output["total"] = output['end'] - output['start']
    output["sciname_cache"] = get_sciname.cache_info()
    output["taxon_cache"] = get_taxon.cache_info()
    logger.info(f"Images Cached in {output['total']} sec.")
    logger.info(f"Cache Timing Output: {output}")
    return output

def spellcheck(worda, wordb, cutoff=3):
    """Checks if two words are close to each other.
    
    `worda` (str) - first word to compare
    `wordb` (str) - second word to compare
    `cutoff` (int) - allowed difference amount
    """
    worda = worda.lower().replace("-", " ").replace("'", "")
    wordb = wordb.lower().replace("-", " ").replace("'", "")
    shorterword = min(worda, wordb, key=len)
    if worda != wordb:
        if len(list(difflib.Differ().compare(worda, wordb))) - len(shorterword) >= cutoff:
            return False
    return True
