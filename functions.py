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

from random import randint
from google_images_download import google_images_download
import aiohttp
import eyed3
import concurrent.futures
import asyncio
from data.data import *


# Initialize library
response = google_images_download.googleimagesdownload()

# Valid file types
valid_extensions = ["jpg", "png", "jpeg"]


# sets up new channel
async def channel_setup(ctx):
    if database.exists(str(ctx.channel.id)):
        return
    else:
        # ['prevS', 'prevB', 'prevJ', 'goatsucker answered', 'goatsucker',
        #  'totalCorrect', 'songanswered', 'songbird', 'answered', 'bird']
        database.lpush(str(ctx.channel.id), "", "", "20",
                       "1", "", "0", "1", "", "1", "")
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
    loop = asyncio.get_running_loop()
    if bird == "":
        print("error - bird is blank")
        await ctx.send("**There was an error fetching birds.**\n*Please try again.*")
        if on_error is not None:
            on_error(ctx)
        return

    delete = await ctx.send("**Fetching.** This may take a while.")
    # trigger "typing" discord message
    await ctx.trigger_typing()

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            response = await loop.run_in_executor(pool, download, ctx, bird, addOn)
        except GenericError:
            await delete.delete()
            await ctx.send("**An error has occurred while fetching images.**\n*Please try again.*")
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
            await ctx.send(file=discord.File(img, filename="bird."+extension))


# function that gets bird images to run in pool (blocking prevention)
def download(ctx, bird, addOn=None):
    # fetch scientific names of birds
    if bird in birdList:
        index = birdList.index(bird)
        sciBird = f"{sciBirdList[index]} (bird)"
    else:
        sciBird = f"{bird} (bird)"

    try:
        print("trying")
        images = os.listdir(f"downloads/{sciBird}{addOn}/")
        print(f"downloads/{sciBird}{addOn}/")
        if len(images) == 0:
            raise GenericError("No Images")
        for path in images:
            images[images.index(path)] = f"downloads/{sciBird}{addOn}/{path}"
        print("images: "+str(images))
    except (FileNotFoundError, GenericError):
        print("fail")
        # if not found, fetch images
        print("scibird: "+str(sciBird))
        arguments = {"keywords": sciBird +
                     str(addOn), "limit": 15, "print_urls": True}
        # passing the arguments to the function
        paths = response.download(arguments)
        print("paths: "+str(paths))
        paths = paths[0]
        images = [paths[i] for i in sorted(paths.keys())]
        images = images[0]
        print("images: "+str(images))

    prevJ = int(str(database.lindex(str(ctx.channel.id), 7))[2:-1])
    # Randomize start (choose beginning 4/5ths in case it fails checks)
    if len(images) != 0:
        j = (prevJ+1) % len(images)
        print("prevJ: "+str(prevJ))
        print("j: "+str(j))

        for x in range(j, len(images)):  # check file type and size
            image_link = images[x]
            extension = image_link.split('.')[-1]
            print("extension: "+str(extension))
            statInfo = os.stat(image_link)
            print("size: "+str(statInfo.st_size))
            if extension.lower() in valid_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
                print("found one!")
                break
            elif x == len(images)-1:
                j = (j+1) % (len(images))
                raise GenericError("No Valid Images Found")

        database.lset(str(ctx.channel.id), 7, str(j))
    else:
        raise GenericError("No Images Found")

    return [image_link, extension]


# sends a birdsong
async def send_birdsong(ctx, bird, on_error=None, message=None):
    if bird == "":
        print("error - bird is blank")
        await ctx.send("**There was an error fetching birds.**\n*Please try again.*")
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
        query = sciBird.replace(" ", "%20")
        async with session.get(f"https://www.xeno-canto.org/api/2/recordings?query={query}%20q:A&page=1") as response:
            if response.status == 200:
                json = await response.json()
                recordings = json["recordings"]
                print("recordings: "+str(recordings))
                if len(recordings) == 0:  # bird not found
                    # try with common name instead
                    query = bird.replace(" ", "%20")
                    async with session.get(f"https://www.xeno-canto.org/api/2/recordings?query={query}%20q:A&page=1") as response:
                        if response.status == 200:
                            json = await response.json()
                            recordings = json["recordings"]
                        else:
                            await delete.delete()
                            await ctx.send("**A GET error occurred when fetching the song.**\n*Please try again.*")
                            print("error:" + str(response.status))

                if len(recordings) != 0:
                    url = str(
                        f"https:{recordings[randint(0, len(recordings)-1)]['file']}")
                    print("url: "+url)
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
                                await ctx.send("**Oops! File too large :(**\n*Please try again.*")
                                return
                            await delete.delete()
                            if message is not None:
                                await ctx.send(message)
                            # change filename to avoid spoilers
                            with open(fileName, "rb") as song:
                                await ctx.send(file=discord.File(song, filename="bird.mp3"))
                        else:
                            await delete.delete()
                            await ctx.send("**A GET error occurred when fetching the song.**\n*Please try again.*")
                            print("error:" + str(songFile.status))
                else:
                    await delete.delete()
                    await ctx.send("Unable to get song - bird was not found.")

            else:
                await delete.delete()
                await ctx.send("**A GET error occurred when fetching the song.**\n*Please try again.*")
                print("error:" + str(response.status))


# spellcheck - allows one letter off/extra
def spellcheck(worda, wordb):
    worda = worda.lower().replace("-", " ").replace("'","")
    wordb = wordb.lower().replace("-", " ").replace("'","")
    wrongcount = 0
    longerword = []
    shorterword = []
    list1 = [char for char in worda]
    list2 = [char for char in wordb]
    if worda != wordb:
        if len(list1) > len(list2):
            longerword = list1
            shorterword = list2
        elif len(list1) < len(list2):
            longerword = list2
            shorterword = list1
        else:
            for i in range(len(list1)):
                if list1[i] != list2[i]:
                    wrongcount += 1
        if len(list1) != len(list2):
            if abs(len(longerword)-len(shorterword)) > 1:
                return False
            else:
                for i in range(len(shorterword)):
                    try:
                        if longerword[i] != shorterword[i]:
                            wrongcount += 1
                            del longerword[i]
                    except IndexError:
                        wrongcount = 100

        if wrongcount > 1:
            return False
        else:
            return True
    else:
        return True
