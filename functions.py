# functions.py | function definitions
# Copyright (C) 2019  EraserBird, person_v1.32

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
from mimetypes import guess_all_extensions,guess_extension
import os
import urllib.parse
from random import randint

import aiohttp
import discord
import eyed3

from data.data import GenericError, database, birdList, sciBirdList, songBirds, sciSongBirds

TAXON_CODE_URL = "https://search.macaulaylibrary.org/api/v1/find/taxon?q={}"
CATALOG_URL = "https://search.macaulaylibrary.org/catalog.json?searchField=species&taxonCode={}&count={}&mediaType={}&sex={}&age={}&behavior={}&qua=3,4,5"
COUNT = 20  #set this to include a margin of error in case some urls throw error code 476 due to still being processed
# Valid file types
valid_extensions = {"jpg", "png", "jpeg"}


# sets up new channel
async def channel_setup(ctx):
    if database.exists(str(ctx.channel.id)):
        return
    else:
        # ['prevS', 'prevB', 'prevJ', 'goatsucker answered', 'goatsucker',
        #  'totalCorrect', 'songanswered', 'songbird', 'answered', 'bird']
        database.lpush(str(ctx.channel.id), "", "", "20", "1", "", "0", "1",
                       "", "1", "")
        # true = 1, false = 0, index 0 is last arg, prevJ is 20 to define as integer
        await ctx.send("Ok, setup! I'm all ready to use!")


# sets up new user
async def user_setup(ctx):
    if database.zscore("users", str(ctx.message.author.id)) is not None:
        return
    else:
        database.zadd("users", {str(ctx.message.author.id): 0})
        await ctx.send("Welcome <@" + str(ctx.message.author.id) + ">!")


# sets up new birds
async def bird_setup(bird):
    if database.zscore("incorrect", str(bird).title()) is not None:
        return
    else:
        database.zadd("incorrect", {str(bird).title(): 0})


# Function to run on error
def error_skip(ctx):
    print("ok")
    database.lset(str(ctx.channel.id), 0, "")
    database.lset(str(ctx.channel.id), 1, "1")


def error_skip_song(ctx):
    print("ok")
    database.lset(str(ctx.channel.id), 2, "")
    database.lset(str(ctx.channel.id), 3, "1")


def error_skip_goat(ctx):
    print("ok")
    database.lset(str(ctx.channel.id), 5, "")
    database.lset(str(ctx.channel.id), 6, "1")

# Function to send a bird picture:
# ctx - context for message (discord thing)
# bird - bird picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before bird picture (str)
# addOn - string to append to search for female/juvenile birds (str)
async def send_bird(ctx, bird, on_error=None, message=None, addOn=""):
    if bird == "":
        print("error - bird is blank")
        await ctx.send(
            "**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()

    try:
        response = await get_images(ctx, bird,addOn)
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
        with open(filename, 'rb') as img:
            await delete.delete()
            if message is not None:
                await ctx.send(message)
            # change filename to avoid spoilers
            await ctx.send(file=discord.File(img, filename="bird." + extension)
                           )


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
    #fix labeling issues in the library and on the list
    if bird == "Porphyrio martinicus":
        bird = "Porphyrio martinica"
    elif bird == "Strix acio":
        bird = "Screech Owl"
    print(f"getting image urls for {bird}")
    async with session.get(
        TAXON_CODE_URL.format(
            urllib.parse.quote(
                bird.replace("-"," ").replace("'s","")
            )
        )
    ) as taxon_code_response:
        if taxon_code_response.status!=200:
            raise GenericError(f"An http error code of {taxon_code_response.status} occured while fetching a {'image'if media_type=='p' else 'song'} for {bird}")
        taxon_code_data = await taxon_code_response.json()
        taxon_code = taxon_code_data[0]["code"]
    async with session.get(CATALOG_URL.format(taxon_code, COUNT, media_type, sex, age, sound_type)) as catalog_response:
        if catalog_response.status!=200:
            raise GenericError(f"An http error code of {catalog_response.status} occured while fetching a {'image'if media_type=='p' else 'song'} for {bird}")
        catalog_data = await catalog_response.json()
        content = catalog_data["results"]["content"]
        urls = [data["mediaUrl"] for data in content]
        return urls

async def _download_helper(path,url,session):
    response = await session.get(url)
    #from https://stackoverflow.com/questions/29674905/convert-content-type-header-into-file-extension
    content_type=response.headers['content-type'].partition(';')[0].strip()
    if content_type.partition("/")[0]=="image":
        ext = "."+(set(ext[1:] for ext in guess_all_extensions(content_type)) & valid_extensions).pop()
    else:
        ext = guess_extension(content_type)
    filename=f"{path}{ext}"
    #from https://stackoverflow.com/questions/38358521/alternative-of-urllib-urlretrieve-in-python-3-5    
    with contextlib.closing(response) as fp:
        with open(filename, 'wb') as out_file:                    
            block_size = 1024 * 8
            while True:
                block = await fp.content. read(block_size)  # pylint: disable=no-member
                if not block:
                    break
                out_file.write(block)
    return filename      
async def _download_images(bird, addOn):
    directory = f"downloads/images/{bird}{addOn}"
    if addOn == "female":
        sex = "f"
    else:
        sex = ""
    if addOn == "juvenile":
        age = "j"
    else:
        age = ""
    
    async with aiohttp.ClientSession() as session:
        urls = await _get_urls(session,bird, "p", sex, age)
        if not os.path.exists(directory):
            os.makedirs(directory)
        paths = [f"{directory}/{i}" for i in range(len(urls))]
        return await asyncio.gather(*(_download_helper(path,url,session) for path,url in zip(paths,urls)))


# function that gets bird images to run in pool (blocking prevention)
async def get_images(ctx, bird, addOn=None):
    # fetch scientific names of birds
    if bird in birdList:
        index = birdList.index(bird)
        sciBird = sciBirdList[index]
    else:
        sciBird = bird
    directory=f"downloads/{sciBird}{addOn}/"
    try:
        print("trying")
        images_dir = os.listdir(directory)
        print(f"downloads/{sciBird}{addOn}/")
        if not images_dir:
            raise GenericError("No Images")
        images = [f"{directory}{path}" for path in images_dir]
        print("images: " + str(images))
    except (FileNotFoundError, GenericError):
        print("fail")
        # if not found, fetch images
        print("scibird: " + str(sciBird))
        images = await _download_images(sciBird, addOn)
        print("images: " + str(images))

    prevJ = int(str(database.lindex(str(ctx.channel.id), 7))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if images:
        j = (prevJ + 1) % len(images)
        print("prevJ: " + str(prevJ))
        print("j: " + str(j))

        for x in range(j, len(images)):  # check file type and size
            image_link = images[x]
            extension = image_link.split('.')[-1]
            print("extension: " + str(extension))
            statInfo = os.stat(image_link)
            print("size: " + str(statInfo.st_size))
            if extension.lower(
            ) in valid_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
                print("found one!")
                break
            elif x == len(images) - 1:
                j = (j + 1) % (len(images))
                raise GenericError("No Valid Images Found")

        database.lset(str(ctx.channel.id), 7, str(j))
    else:
        raise GenericError("No Images Found")

    return [image_link, extension]


# sends a birdsong
async def send_birdsong(ctx, bird, on_error=None, message=None):
    if bird == "":
        print("error - bird is blank")
        await ctx.send(
            "**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()
    if bird in songBirds:
        index = songBirds.index(bird)
        sciBird = f"{sciSongBirds[index]} (bird)"
    else:
        sciBird = f"{bird} (bird)"

    # fetch sounds
    async with aiohttp.ClientSession() as session:
        query = urllib.parse.quote(sciBird)
        async with session.get(
                f"https://www.xeno-canto.org/api/2/recordings?query={query}%20q:A&page=1"
        ) as response:
            if response.status == 200:
                data = await response.json()
                recordings = data["recordings"]
                print("recordings: " + str(recordings))
                if not recordings:  # bird not found
                    # try with common name instead
                    query = urllib.parse.quote(bird)
                    async with session.get(
                            f"https://www.xeno-canto.org/api/2/recordings?query={query}%20q:A&page=1"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            recordings = data["recordings"]
                        else:
                            await delete.delete()
                            await ctx.send(
                                "**A GET error occurred when fetching the song.**\n*Please try again.*"
                            )
                            print("error:" + str(response.status))

                if recordings:
                    url = str(
                        f"https:{recordings[randint(0, len(recordings)-1)]['file']}"
                    )
                    print("url: " + url)
                    fileName = f"songs/{url.split('/')[3]}.mp3"
                    async with session.get(url) as songFile:
                        if songFile.status == 200:
                            if not os.path.exists("songs/"):
                                os.mkdir("songs/")
                            with open(fileName, 'wb') as fd:
                                while True:
                                    chunk = await songFile.content.read(128)
                                    if not chunk:
                                        break
                                    fd.write(chunk)

                            # remove spoilers in tag metadata
                            audioFile = eyed3.load(fileName)
                            audioFile.tag.remove(fileName)

                            # send song
                            if os.stat(fileName).st_size > 8000000:
                                await delete.delete()
                                await ctx.send(
                                    "**Oops! File too large :(**\n*Please try again.*"
                                )
                                return
                            await delete.delete()
                            if message is not None:
                                await ctx.send(message)
                            # change filename to avoid spoilers
                            with open(fileName, "rb") as song:
                                await ctx.send(file=discord.File(
                                    song, filename="bird.mp3"))
                        else:
                            await delete.delete()
                            await ctx.send(
                                "**A GET error occurred when fetching the song.**\n*Please try again.*"
                            )
                            print("error:" + str(songFile.status))
                else:
                    await delete.delete()
                    await ctx.send("Unable to get song - bird was not found.")

            else:
                await delete.delete()
                await ctx.send(
                    "**A GET error occurred when fetching the song.**\n*Please try again.*"
                )
                print("error:" + str(response.status))


# spellcheck - allows one letter off/extra
def spellcheck(worda, wordb):
    worda = worda.lower().replace("-", " ").replace("'", "")
    wordb = wordb.lower().replace("-", " ").replace("'", "")
    wrongcount = 0
    if worda != wordb:
        if len(worda) != len(wordb):
            list1=list(worda)
            list2=list(wordb)
            longerword = max(list1, list2, key=len)
            shorterword = min(list1, list2, key=len)
            if abs(len(longerword) - len(shorterword)) > 1:
                return False
            else:
                for i in range(len(shorterword)):
                    try:
                        if longerword[i] != shorterword[i]:
                            wrongcount += 1
                            del longerword[i]
                    except IndexError:
                        wrongcount = 100
        else:
            wrongcount = sum(x != y for x, y in zip(worda, wordb))
        return wrongcount <= 1
    else:
        return True
