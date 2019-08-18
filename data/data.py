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


birdList = ["birdList"]
sciBirdList = ["sciBirdList"]
memeList = ["memeList"]
songBirds = ["songBirds"]
sciSongBirds = ["sciSongBirds"]


def _main():
    global birdList
    global sciBirdList
    global memeList
    global songBirds
    global sciSongBirds
    files = [birdList, sciBirdList, memeList, songBirds, sciSongBirds]

    # Converts txt file of data into lists
    for list in files:
        print(f"Working on {list[0]}")
        with open(f'data/{list[0]}.txt', 'r') as fileIn:
            for line in fileIn:
                list.append(line.strip('\n'))
        list.remove(str(list[0]))
        print("Done!")


_main()
