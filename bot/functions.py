# functions.py | function definitions
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
import os
import pickle
import random
import string
import time
import urllib.parse
from functools import partial
from io import BytesIO
from mimetypes import guess_all_extensions, guess_extension

import aiohttp
import discord
import eyed3
from PIL import Image
from sentry_sdk import capture_exception

from bot.data import (GenericError, birdListMaster, database, logger,
                      sciBirdListMaster, sciSongBirdsMaster, screech_owls,
                      states, get_wiki_url)

# Macaulay URL definitions
TAXON_CODE_URL = "https://search.macaulaylibrary.org/api/v1/find/taxon?q={}"
CATALOG_URL = (
    "https://search.macaulaylibrary.org/catalog.json?searchField=species" +
    "&taxonCode={}&count={}&mediaType={}&sex={}&age={}&behavior={}&qua=3,4,5"
)
SCINAME_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&species={}"
COUNT = 20  # set this to include a margin of error in case some urls throw error code 476 due to still being processed

# Valid file types
valid_image_extensions = {"jpg", "png", "jpeg", "gif"}
valid_audio_extensions = {"mp3", "wav"}

async def channel_setup(ctx):
    """Sets up a new discord channel.
    
    `ctx` - Discord context object
    """
    logger.info("checking channel setup")
    if database.exists(f"channel:{ctx.channel.id}"):
        logger.info("channel data ok")
    else:
        database.hmset(
            f"channel:{ctx.channel.id}", {
                "bird": "",
                "answered": 1,
                "sBird": "",
                "sAnswered": 1,
                "goatsucker": "",
                "gsAnswered": 1,
                "prevJ": 20,
                "prevB": "",
                "prevS": "",
                "prevK": 20
            }
        )
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        logger.info("channel data added")
        await ctx.send("Ok, setup! I'm all ready to use!")

    if database.zscore("score:global", str(ctx.channel.id)) is not None:
        logger.info("channel score ok")
    else:
        database.zadd("score:global", {str(ctx.channel.id): 0})
        logger.info("channel score added")

async def user_setup(ctx):
    """Sets up a new discord user for score tracking.
    
    `ctx` - Discord context object
    """
    logger.info("checking user data")
    if database.zscore("users:global", str(ctx.author.id)) is not None:
        logger.info("user global ok")
    else:
        database.zadd("users:global", {str(ctx.author.id): 0})
        logger.info("user global added")
        await ctx.send("Welcome <@" + str(ctx.author.id) + ">!")

    #Add streak
    if (database.zscore("streak:global", str(ctx.author.id)) is
        not None) and (database.zscore("streak.max:global", str(ctx.author.id)) is not None):
        logger.info("user streak in already")
    else:
        database.zadd("streak:global", {str(ctx.author.id): 0})
        database.zadd("streak.max:global", {str(ctx.author.id): 0})
        logger.info("added streak")

    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"users.server:{ctx.guild.id}", str(ctx.author.id)) is not None:
            server_score = database.zscore(f"users.server:{ctx.guild.id}", str(ctx.author.id))
            global_score = database.zscore("users:global", str(ctx.author.id))
            if server_score is global_score:
                logger.info("user server ok")
            else:
                database.zadd(f"users.server:{ctx.guild.id}", {str(ctx.author.id): global_score})
        else:
            score = int(database.zscore("users:global", str(ctx.author.id)))
            database.zadd(f"users.server:{ctx.guild.id}", {str(ctx.author.id): score})
            logger.info("user server added")
    else:
        logger.info("dm context")

async def bird_setup(ctx, bird: str):
    """Sets up a new bird for incorrect tracking.
    
    `ctx` - Discord context object
    `bird` - bird to setup
    """
    logger.info("checking bird data")
    if database.zscore("incorrect:global", string.capwords(bird)) is not None:
        logger.info("bird global ok")
    else:
        database.zadd("incorrect:global", {string.capwords(bird): 0})
        logger.info("bird global added")

    if database.zscore(f"incorrect.user:{ctx.author.id}", string.capwords(bird)) is not None:
        logger.info("bird user ok")
    else:
        database.zadd(f"incorrect.user:{ctx.author.id}", {string.capwords(bird): 0})
        logger.info("bird user added")

    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"incorrect.server:{ctx.guild.id}", string.capwords(bird)) is not None:
            logger.info("bird server ok")
        else:
            database.zadd(f"incorrect.server:{ctx.guild.id}", {string.capwords(bird): 0})
            logger.info("bird server added")
    else:
        logger.info("dm context")

    if database.exists(f"session.data:{ctx.author.id}"):
        logger.info("session in session")
        if database.zscore(f"session.incorrect:{ctx.author.id}", string.capwords(bird)) is not None:
            logger.info("bird session ok")
        else:
            database.zadd(f"session.incorrect:{ctx.author.id}", {string.capwords(bird): 0})
            logger.info("bird session added")
    else:
        logger.info("no session")

def error_skip(ctx):
    """Skips the current bird.
    
    Passed to send_bird() as on_error to skip the bird when an error occurs to prevent error loops.
    """
    logger.info("ok")
    database.hset(f"channel:{ctx.channel.id}", "bird", "")
    database.hset(f"channel:{ctx.channel.id}", "answered", "1")

def error_skip_song(ctx):
    """Skips the current song.
    
    Passed to send_birdsong() as on_error to skip the bird when an error occurs to prevent error loops.
    """
    logger.info("ok")
    database.hset(f"channel:{ctx.channel.id}", "sBird", "")
    database.hset(f"channel:{ctx.channel.id}", "sAnswered", "1")

def error_skip_goat(ctx):
    """Skips the current goatsucker.
    
    Passed to send_bird() as on_error to skip the bird when an error occurs to prevent error loops.
    """
    logger.info("ok")
    database.hset(f"channel:{ctx.channel.id}", "goatsucker", "")
    database.hset(f"channel:{ctx.channel.id}", "gsAnswered", "1")

def check_state_role(ctx) -> list:
    """Returns a list of state roles a user has.
    
    `ctx` - Discord context object
    """
    logger.info("checking roles")
    user_states = []
    if ctx.guild is not None:
        logger.info("server context")
        user_role_names = [role.name.lower() for role in ctx.author.roles]
        for state in states:
            # gets similarities
            if set(user_role_names).intersection(set(states[state]["aliases"])):
                user_states.append(state)
    else:
        logger.info("dm context")
    logger.info(f"user roles: {user_states}")
    return user_states

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
            code = await get_taxon(bird, session)
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
                    taxon_code = await get_taxon(bird, session, retries)
                    return taxon_code
            taxon_code_data = await taxon_code_response.json()
            try:
                logger.info(f"raw data: {taxon_code_data}")
                taxon_code = taxon_code_data[0]["code"]
                logger.info(f"first item: {taxon_code_data[0]}")
                if len(taxon_code_data) > 1:
                    logger.info("entering check")
                    for item in taxon_code_data:
                        logger.info(f"checking: {item}")
                        if spellcheck(item["name"].split(" - ")[0], bird,
                                      4) or spellcheck(item["name"].split(" - ")[1], bird, 4):
                            logger.info("ok")
                            taxon_code = item["code"]
                            break
                        logger.info("fail")
            except IndexError:
                raise GenericError(f"No taxon code found for {bird}", code=111)
    logger.info(f"taxon code: {taxon_code}")
    return taxon_code

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

def session_increment(ctx, item: str, amount: int):
    """Increments the value of a database hash field by `amount`.

    `ctx` - Discord context object\n
    `item` - hash field to increment (see data.py for details,
    possible values include correct, incorrect, total)\n
    `amount` (int) - amount to increment by, usually 1
    """
    logger.info(f"incrementing {item} by {amount}")
    value = int(database.hget(f"session.data:{ctx.author.id}", item))
    value += int(amount)
    database.hset(f"session.data:{ctx.author.id}", item, str(value))

def incorrect_increment(ctx, bird: str, amount: int):
    """Increments the value of an incorrect bird by `amount`.

    `ctx` - Discord context object\n
    `bird` - bird that was incorrect\n
    `amount` (int) - amount to increment by, usually 1
    """
    logger.info(f"incrementing incorrect {bird} by {amount}")
    database.zincrby("incorrect:global", amount, string.capwords(str(bird)))
    database.zincrby(f"incorrect.user:{ctx.author.id}", amount, string.capwords(str(bird)))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"incorrect.server:{ctx.guild.id}", amount, string.capwords(str(bird)))
    else:
        logger.info("dm context")
    if database.exists(f"session.data:{ctx.author.id}"):
        logger.info("session in session")
        database.zincrby(f"session.incorrect:{ctx.author.id}", amount, string.capwords(str(bird)))
    else:
        logger.info("no session")

def score_increment(ctx, amount: int):
    """Increments the score of a user by `amount`.

    `ctx` - Discord context object\n
    `amount` (int) - amount to increment by, usually 1
    """
    logger.info(f"incrementing score by {amount}")
    database.zincrby("score:global", amount, str(ctx.channel.id))
    database.zincrby("users:global", amount, str(ctx.author.id))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"users.server:{ctx.guild.id}", amount, str(ctx.author.id))
    else:
        logger.info("dm context")
    if database.exists(f"race.data:{ctx.channel.id}"):
        logger.info("race in session")
        database.zincrby(f"race.scores:{ctx.channel.id}", amount, str(ctx.author.id))

def owner_check(ctx) -> bool:
    """Check to see if the user is the owner of the bot."""
    owners = set(str(os.getenv("ids")).split(","))
    return str(ctx.author.id) in owners

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
            fn = partial(_black_and_white, filename)
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
    taxon_code = await get_taxon(bird, session)
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
        urls = [data["mediaUrl"] for data in content]
        return urls

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


async def drone_attack(ctx):
    logger.info(ctx.command)
    if str(ctx.command) in ("help", "covid", "botinfo", "invite",
                            "list", "meme", "taxon", "wikipedia"
                            "leaderboard", "missed", "score",
                            "streak", "userscore", "remove", "set"):
        return True

    elif str(ctx.command) in ("bird", "song", "goatsucker"):
        images = os.listdir("bot/media/images/drone")
        path = f"bot/media/images/drone/{images[random.randint(0,len(images)-1)]}"
        BASE_MESSAGE = (
            "*Here you go!* \n**Use `b!{new_cmd}` again to get a new {media} of the same bird, " +
            "or `b!{skip_cmd}` to get a new bird. Use `b!{check_cmd} guess` to check your answer. " +
            "Use `b!{hint_cmd}` for a hint.**"
        )

        if str(ctx.command) == "bird":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="image", new_cmd="bird", skip_cmd="skip", check_cmd="check", hint_cmd="hint"
                ) +
                "\n*This is an image.*"
            )
        elif str(ctx.command) == "goatsucker":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="image", new_cmd="gs", skip_cmd="skipgoat", check_cmd="checkgoat", hint_cmd="hintgoat"
                )
            )
        elif str(ctx.command) == "bird":
            await ctx.send(
                BASE_MESSAGE.format(
                    media="song", new_cmd="song", skip_cmd="skipsong", check_cmd="checksong", hint_cmd="hintsong"
                )
            )

        file_obj = discord.File(path, filename=f"bird.jpg")
        await ctx.send(file=file_obj)

    elif str(ctx.command) in ("check", "checkgoat", "checksong"):
        args = ctx.message.content.split(" ")[1:]
        matches = difflib.get_close_matches(" ".join(args), birdListMaster + sciBirdListMaster, n=1)
        if "drone" in args:
            await ctx.send("SHHHHHH! Birds are **NOT** government drones! You'll blow our cover, and we'll need to get rid of you.")
        elif matches:
            await ctx.send("Correct! Good job!")
            url = get_wiki_url(matches[0])
            await ctx.send(url)
        else:
            await ctx.send("Sorry, the bird was actually **definitely a real bird.**")
            await ctx.send(("https://en.wikipedia.org/wiki/Bird" if random.randint(0,1) == 0 else "https://youtu.be/Fg_JcKSHUtQ"))

    elif str(ctx.command) in ("skip", "skipgoat", "skipsong"):
        await ctx.send("Ok, skipping **definitely a real bird.**")
        await ctx.send(("https://en.wikipedia.org/wiki/Bird" if random.randint(0,1) == 0 else "https://youtu.be/Fg_JcKSHUtQ"))

    elif str(ctx.command) in ("hint", "hintgoat", "hintsong"):
        await ctx.send("This is definitely a real bird, **NOT** a government drone.")

    elif str(ctx.command) in ("info"):
        await ctx.send("Birds are real. Don't believe what others may say. **BIRDS ARE VERY REAL!**")

    elif str(ctx.command) in ("race", "session"):
        await ctx.send("Races and sessions have been disabled today. We apologize for any inconvenience.")

    raise GenericError(code=666)


async def precache():
    """Downloads all images and songs.

    This function downloads all images and songs in the bird lists,
    including females and juveniles.

    This function is run with a task every 24 hours.
    """
    start = time.time()
    timeout = aiohttp.ClientTimeout(total=10 * 60)
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        logger.info("Starting cache")
        await asyncio.gather(*(download_media(bird, "images", session=session) for bird in sciBirdListMaster))
        logger.info("Starting females")
        await asyncio.gather(
            *(download_media(bird, "images", addOn="female", session=session) for bird in sciBirdListMaster)
        )
        logger.info("Starting juveniles")
        await asyncio.gather(
            *(download_media(bird, "images", addOn="juvenile", session=session) for bird in sciBirdListMaster)
        )
        logger.info("Starting songs")
        await asyncio.gather(*(download_media(bird, "songs", session=session) for bird in sciSongBirdsMaster))
    end = time.time()
    logger.info(f"Images Cached in {end-start} sec.")

async def backup_all():
    """Backs up the database to a file.
    
    This function serializes all data in the REDIS database
    into a file in the `backups` directory.

    This function is run with a task every 6 hours and sends the files
    to a specified discord channel.
    """
    logger.info("Starting Backup")
    logger.info("Creating Dump")
    keys = [key.decode("utf-8") for key in database.keys()]
    dump = map(database.dump, keys)
    logger.info("Finished Dump")
    logger.info("Writing To File")
    try:
        os.mkdir("backups")
        logger.info("Created backups directory")
    except FileExistsError:
        logger.info("Backups directory exists")
    with open("backups/dump.dump", 'wb') as f:
        with open("backups/keys.txt", 'w') as k:
            for item, key in zip(dump, keys):
                pickle.dump(item, f)
                k.write(f"{key}\n")
    logger.info("Backup Finished")

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
