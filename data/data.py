# Import modules for other files
import discord
from discord.ext import commands
import wikipedia
import redis
import os

# define database for one connection
database = redis.from_url(os.getenv("REDIS_URL"))

# Database Format Definitions

# prevJ - makes sure it sends a diff image
# prevB - makes sure it sends a diff bird
# prevS - makes sure it sends a diff song

# server format = {
# "ctx.channel.id" : ["bird", "answered", "songbird", "songanswered",
#                     "totalCorrect", "goatsucker", "goatsucker answered",
#                     "prevJ", "prevB", "prevS"]
# }

# user format = {
# user:[userid, #ofcorrect]
# }


class GenericError(commands.CommandError):
    def __init__(self, message=None):
        return super().__init__(message=message)

# Lists of birds, memes, and other info


birdList = []
sciBirdList = []
memeList = []
songBirds = []
sciSongBirds = []


def _main():
    global birdList
    global sciBirdList
    global memeList
    global songBirds
    global sciSongBirds

    # Converts txt file of birds into list
    birdList = []
    with open('data/birdList.txt', 'r') as fileIn:
        for line in fileIn:
            birdList.append(line.strip('\n'))
    print("birdList done!")

    # Converts txt file of scientific birds into list
    sciBirdList = []
    with open('data/scibirds.txt', 'r') as fileIn:
        for line in fileIn:
            sciBirdList.append(line.strip('\n'))
    print("sciBirdList done!")

    # Converts meme txt into list
    memeList = []
    with open('data/memes.txt', 'r') as fileIn:
        for line in fileIn:
            memeList.append(line.strip('\n'))
        print("memeList done!")

    # Converts txt file of songbirds into list
    songBirds = []
    with open('data/birdsongs.txt', 'r') as fileIn:
        for line in fileIn:
            songBirds.append(line.strip('\n'))
        print("songBirds done!")

    # Converts txt file of scientific songbirds into list
    sciSongBirds = []
    with open('data/scibirdsongs.txt', 'r') as fileIn:
        for line in fileIn:
            sciSongBirds.append(line.strip('\n'))
        print("sciSongBirds done!")


_main()
