# functions.py | function definitions
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

import aiohttp
import discord
import eyed3
import asyncio
import contextlib
import difflib
import os
import string
import urllib.parse
from PIL import Image
from io import BytesIO
from functools import partial
from mimetypes import guess_all_extensions, guess_extension


from data.data import (GenericError, logger, states, database,
                       sciBirdListMaster, sciSongBirdsMaster)

TAXON_CODE_URL = "https://search.macaulaylibrary.org/api/v1/find/taxon?q={}"
CATALOG_URL = ("https://search.macaulaylibrary.org/catalog.json?searchField=species" +
               "&taxonCode={}&count={}&mediaType={}&sex={}&age={}&behavior={}&qua=3,4,5")
SCINAME_URL = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&species={}"
COUNT = 20  # set this to include a margin of error in case some urls throw error code 476 due to still being processed

# Valid file types
valid_image_extensions = {"jpg", "png", "jpeg", "gif"}
valid_audio_extensions = {"mp3"}


# sets up new channel
async def channel_setup(ctx):
    logger.info("checking channel setup")
    if database.exists(f"channel:{str(ctx.channel.id)}"):
        logger.info("channel data ok")
    else:
        database.hmset(f"channel:{str(ctx.channel.id)}",
                       {"bird": "", "answered": 1, "sBird": "", "sAnswered": 1,
                        "goatsucker": "", "gsAnswered": 1,
                        "prevJ": 20, "prevB": "", "prevS": "", "prevK": 20})
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        logger.info("channel data added")
        await ctx.send("Ok, setup! I'm all ready to use!")

    if database.zscore("score:global", str(ctx.channel.id)) is not None:
        logger.info("channel score ok")
    else:
        database.zadd("score:global", {str(ctx.channel.id): 0})
        logger.info("channel score added")


# sets up new user
async def user_setup(ctx):
    logger.info("checking user data")
    if database.zscore("users:global", str(ctx.author.id)) is not None:
        logger.info("user global ok")
    else:
        database.zadd("users:global", {str(ctx.author.id): 0})
        logger.info("user global added")
        await ctx.send("Welcome <@" + str(ctx.author.id) + ">!")

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


# sets up new birds
async def bird_setup(ctx, bird):
    logger.info("checking bird data")
    if database.zscore("incorrect:global", string.capwords(str(bird))) is not None:
        logger.info("bird global ok")
    else:
        database.zadd("incorrect:global", {string.capwords(str(bird)): 0})
        logger.info("bird global added")

    if database.zscore(f"incorrect.user:{ctx.author.id}", string.capwords(str(bird))) is not None:
        logger.info("bird user ok")
    else:
        database.zadd(f"incorrect.user:{ctx.author.id}", {string.capwords(str(bird)): 0})
        logger.info("bird user added")

    if ctx.guild is not None:
        logger.info("no dm")
        if database.zscore(f"incorrect.server:{ctx.guild.id}", string.capwords(str(bird))) is not None:
            logger.info("bird server ok")
        else:
            database.zadd(f"incorrect.server:{ctx.guild.id}", {string.capwords(str(bird)): 0})
            logger.info("bird server added")
    else:
        logger.info("dm context")


# Function to run on error
def error_skip(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "bird", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "answered", "1")


def error_skip_song(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "sBird", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "sAnswered", "1")


def error_skip_goat(ctx):
    logger.info("ok")
    database.hset(f"channel:{str(ctx.channel.id)}", "goatsucker", "")
    database.hset(f"channel:{str(ctx.channel.id)}", "gsAnswered", "1")


def check_state_role(ctx):
    logger.info("checking roles")
    user_states = []
    if ctx.guild is not None:
        logger.info("server context")
        user_role_names = [role.name.lower() for role in ctx.author.roles]
        for state in list(states.keys()):
            # gets similarities
            if len(set(user_role_names).intersection(set(states[state]["aliases"]))) is not 0:
                user_states.append(state)
    else:
        logger.info("dm context")
    logger.info(f"user roles: {user_states}")
    return user_states


# fetch scientific name from common name or taxon code
async def get_sciname(bird, session=None):
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
                raise GenericError(f"An http error code of {sciname_response.status} occured" +
                                   f" while fetching {sciname_url} for {code}", code=201)
            sciname_data = await sciname_response.json()
            try:
                sciname = sciname_data[0]["sciName"]
            except IndexError:
                raise GenericError(f"No sciname found for {code}", code=111)
    logger.info(f"sciname: {sciname}")
    return sciname


# fetch taxonomic code from common/scientific name
async def get_taxon(bird, session=None):
    logger.info(f"getting taxon code for {bird}")
    async with contextlib.AsyncExitStack() as stack:
        if session is None:
            session = await stack.enter_async_context(aiohttp.ClientSession())
        taxon_code_url = TAXON_CODE_URL.format(
            urllib.parse.quote(
                bird.replace("-", " ").replace("'s", "")
            )
        )
        async with session.get(taxon_code_url) as taxon_code_response:
            if taxon_code_response.status != 200:
                raise GenericError(f"An http error code of {taxon_code_response.status} occured" +
                                   f" while fetching {taxon_code_url} for {bird}", code=201)
            taxon_code_data = await taxon_code_response.json()
            try:
                logger.info(f"raw data: {taxon_code_data}")
                taxon_code = taxon_code_data[0]["code"]
                logger.info(f"first item: {taxon_code_data[0]}")
                if len(taxon_code_data) > 1:
                    logger.info("entering check")
                    for item in taxon_code_data:
                        logger.info(f"checking: {item}")
                        if spellcheck(item["name"].split(" - ")[0], bird, 6
                                      ) or spellcheck(item["name"].split(" - ")[1], bird, 6):
                            logger.info("ok")
                            taxon_code = item["code"]
                            break
                        logger.info("fail")
            except IndexError:
                raise GenericError(f"No taxon code found for {bird}", code=111)
    logger.info(f"taxon code: {taxon_code}")
    return taxon_code


def _black_and_white(input_image_path):
    logger.info("black and white")
    with Image.open(input_image_path) as color_image:
        bw = color_image.convert('L')
        final_buffer = BytesIO()
        bw.save(final_buffer, "png")
    final_buffer.seek(0)
    return final_buffer


def session_increment(ctx, item, amount):
    logger.info(f"incrementing {item} by {amount}")
    value = int(database.hget(f"session.data:{ctx.author.id}", item))
    value += int(amount)
    database.hset(f"session.data:{ctx.author.id}", item, str(value))

def incorrect_increment(ctx, bird, amount):
    logger.info(f"incrementing incorrect {bird} by {amount}")
    database.zincrby("incorrect:global", amount, str(bird))
    database.zincrby(f"incorrect.user:{ctx.author.id}", amount, str(bird))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"incorrect.server:{ctx.guild.id}", amount, str(bird))
    else:
        logger.info("dm context")

def score_increment(ctx, amount):
    logger.info(f"incrementing score by {amount}")
    database.zincrby("score:global", amount, str(ctx.channel.id))
    database.zincrby("users:global", amount, str(ctx.author.id))
    if ctx.guild is not None:
        logger.info("no dm")
        database.zincrby(f"users.server:{ctx.guild.id}", amount, str(ctx.author.id))
    else:
        logger.info("dm context")

# Gets a bird picture and sends it to user:
# ctx - context for message (discord thing)
# bird - bird picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before bird picture (str)
# addOn - string to append to search for female/juvenile birds (str)
async def send_bird(ctx, bird, on_error=None, message=None, addOn="", bw=False):
    if bird == "":
        logger.error("error - bird is blank")
        await ctx.send(
            "**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()

    try:
        response = await get_image(ctx, bird, addOn)
    except GenericError as e:
        await delete.delete()
        await ctx.send(f"**An error has occurred while fetching images.**\n*Please try again.*\n**Reason:** {str(e)}")
        if on_error is not None:
            on_error(ctx)
        return

    filename = str(response[0])
    extension = str(response[1])
    statInfo = os.stat(filename)
    if statInfo.st_size > 8000000:  # another filesize check
        await delete.delete()
        await ctx.send("**Oops! File too large :(**\n*Please try again.*")
    else:
        if bw:
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


# Gets a bird sound and sends it to user:
# ctx - context for message (discord thing)
# bird - bird picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before bird picture (str)
async def send_birdsong(ctx, bird, on_error=None, message=None):
    if bird == "":
        logger.error("error - bird is blank")
        await ctx.send(
            "**There was an error fetching birds.**\n*Please try again.*")
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
        await ctx.send(f"**An error has occurred while fetching songs.**\n*Please try again.*\n**Reason:** {str(e)}")
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
    if statInfo.st_size > 8000000:  # another filesize check
        await delete.delete()
        await ctx.send("**Oops! File too large :(**\n*Please try again.*")
    else:
        with open(filename, 'rb') as img:
            if message is not None:
                await ctx.send(message)
            # change filename to avoid spoilers
            await ctx.send(file=discord.File(img, filename="bird." + extension)
                           )
            await delete.delete()


# Function that gets bird images to run in pool (blocking prevention)
# Chooses one image to send
async def get_image(ctx, bird, addOn=None):
    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird
    images = await get_files(sciBird, "images", addOn)
    logger.info("images: " + str(images))
    prevJ = int(
        str(database.hget(f"channel:{str(ctx.channel.id)}", "prevJ"))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if images:
        j = (prevJ + 1) % len(images)
        logger.debug("prevJ: " + str(prevJ))
        logger.debug("j: " + str(j))

        for x in range(j, len(images)):  # check file type and size
            image_link = images[x]
            extension = image_link.split('.')[-1]
            logger.debug("extension: " + str(extension))
            statInfo = os.stat(image_link)
            logger.debug("size: " + str(statInfo.st_size))
            if extension.lower(
            ) in valid_image_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
                logger.info("found one!")
                break
            elif x == len(images) - 1:
                j = (j + 1) % (len(images))
                raise GenericError("No Valid Images Found", code=999)

        database.hset(f"channel:{str(ctx.channel.id)}", "prevJ", str(j))
    else:
        raise GenericError("No Images Found", code=100)

    return [image_link, extension]


# Function that gets bird sounds to run in pool (blocking prevention)
# Chooses one sound to send
async def get_song(ctx, bird):
    # fetch scientific names of birds
    try:
        sciBird = await get_sciname(bird)
    except GenericError:
        sciBird = bird
    songs = await get_files(sciBird, "songs")
    logger.info("songs: " + str(songs))
    prevK = int(
        str(database.hget(f"channel:{str(ctx.channel.id)}", "prevK"))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if songs:
        k = (prevK + 1) % len(songs)
        logger.debug("prevK: " + str(prevK))
        logger.debug("k: " + str(k))

        for x in range(k, len(songs)):  # check file type and size
            song_link = songs[x]
            extension = song_link.split('.')[-1]
            logger.debug("extension: " + str(extension))
            statInfo = os.stat(song_link)
            logger.debug("size: " + str(statInfo.st_size))
            if extension.lower(
            ) in valid_audio_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
                logger.info("found one!")
                break
            elif x == len(songs) - 1:
                k = (k + 1) % (len(songs))
                raise GenericError("No Valid Songs Found", code=999)

        database.hset(f"channel:{str(ctx.channel.id)}", "prevK", str(k))
    else:
        raise GenericError("No Songs Found", code=100)

    return [song_link, extension]


# Manages cache
async def get_files(sciBird, media_type, addOn=""):
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
        return await download_media(sciBird, media_type, addOn, directory)


# Manages downloads
async def download_media(bird, media_type, addOn="", directory=None, session=None):
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
        logger.info(f"filenames: {filenames}")
        return filenames


# Gets urls for downloading
async def _get_urls(session, bird, media_type, sex="", age="", sound_type=""):
    """
    bird can be either common name or scientific name
    media_type is either p(for pictures), a(for audio) or v(for video)
    sex is m,f or blank
    age is a(for adult), j(for juvenile), i(for immature(may be very few pics)) or blank
    sound_type is s(for song),c(for call) or blank
    return is list of urls. some urls may return an error code of 476(because it is still being processed);
        if so, ignore that url.
    """
    logger.info(f"getting file urls for {bird}")
    taxon_code = await get_taxon(bird, session)
    catalog_url = CATALOG_URL.format(
        taxon_code, COUNT, media_type, sex, age, sound_type)
    async with session.get(catalog_url) as catalog_response:
        if catalog_response.status != 200:
            raise GenericError(f"An http error code of {catalog_response.status} occured " +
                               f"while fetching {catalog_url} for a {'image'if media_type=='p' else 'song'} for {bird}", code=201)
        catalog_data = await catalog_response.json()
        content = catalog_data["results"]["content"]
        urls = [data["mediaUrl"] for data in content]
        return urls


# Actually downloads the file
async def _download_helper(path, url, session):
    try:
        async with session.get(url) as response:
            # from https://stackoverflow.com/questions/29674905/convert-content-type-header-into-file-extension
            content_type = response.headers['content-type'].partition(';')[
                0].strip()
            if content_type.partition("/")[0] == "image":
                try:
                    ext = "." + \
                        (set(ext[1:] for ext in guess_all_extensions(
                            content_type)) & valid_image_extensions).pop()
                except KeyError:
                    raise GenericError(
                        f"No valid extensions found. Extensions: {guess_all_extensions(content_type)}")

            elif content_type.partition("/")[0] == "audio":
                try:
                    ext = "." + \
                        (set(ext[1:] for ext in guess_all_extensions(
                            content_type)) & valid_audio_extensions).pop()
                except KeyError:
                    raise GenericError(
                        f"No valid extensions found. Extensions: {guess_all_extensions(content_type)}")

            else:
                ext = guess_extension(content_type)

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
    except aiohttp.ClientError:
        logger.error(f"Client Error with url {url} and path {path}")
        raise


async def precache():
    timeout = aiohttp.ClientTimeout(total=10*60)
    conn = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        logger.info("Starting cache")
        await asyncio.gather(*(download_media(bird, "images", session=session) for bird in sciBirdListMaster))
        logger.info("Starting females")
        await asyncio.gather(*(download_media(bird, "images", addOn="female", session=session) for bird in sciBirdListMaster))
        logger.info("Starting juveniles")
        await asyncio.gather(*(download_media(bird, "images", addOn="juvenile", session=session) for bird in sciBirdListMaster))
        logger.info("Starting songs")
        await asyncio.gather(*(download_media(bird, "songs", session=session) for bird in sciSongBirdsMaster))
    logger.info("Images Cached")


# spellcheck - allows one letter off/extra
def spellcheck(worda, wordb, cutoff=4):
    worda = worda.lower().replace("-", " ").replace("'", "")
    wordb = wordb.lower().replace("-", " ").replace("'", "")
    shorterword = min(worda, wordb, key=len)
    wrongcount = 0
    if worda != wordb:
        if len(list(difflib.Differ().compare(worda, wordb)))-len(shorterword) >= cutoff:
            return False
    return True
