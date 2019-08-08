# Import modules
import discord
import os
import wikipedia
from random import randint
from discord.ext import tasks, commands
from google_images_download import google_images_download
import requests
import shutil
import eyed3
import redis

# Initialize library
response = google_images_download.googleimagesdownload()

# Initialize bot
bot = commands.Bot(command_prefix=['b!', 'b.', 'b#'],
                   case_insensitive=True,
                   description="BirdID - Your Very Own Ornithologist")

# Valid file types
valid_extensions = ["jpg", "png", "jpeg"]

# achievement values
achievement = [10, 25, 50, 100, 150, 200, 250, 400, 420, 500, 650, 690]

# Setup Variables
currentBird = ""
currentSongBird = ""

# define database
database = redis.from_url(os.getenv("REDIS_URL"))

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

# Converts txt file of birds into list
birdList = []
with open('birdList.txt', 'r') as fileIn:
    for line in fileIn:
        birdList.append(line.strip('\n'))
print("birdList done!")

# Converts txt file of scientific birds into list
sciBirdList = []
with open('scibirds.txt', 'r') as fileIn:
    for line in fileIn:
        sciBirdList.append(line.strip('\n'))
print("sciBirdList done!")

# Converts meme txt into list
memeList = []
with open('memes.txt', 'r') as fileIn:
    for line in fileIn:
        memeList.append(line.strip('\n'))
    print("memeList done!")

# Converts txt file of songbirds into list
songBirds = []
with open('birdsongs.txt', 'r') as fileIn:
    for line in fileIn:
        songBirds.append(line.strip('\n'))
    print("songBirds done!")

# Converts txt file of scientific songbirds into list
sciSongBirds = []
with open('scibirdsongs.txt', 'r') as fileIn:
    for line in fileIn:
        sciSongBirds.append(line.strip('\n'))
    print("sciSongBirds done!")

# Logging
@bot.event
async def on_ready():
    print("Logged in as:")
    print(bot.user.name)
    print(bot.user.id)
    print("_" * 50)
    # Change discord activity
    await bot.change_presence(activity=discord.Activity(type=3, name="birds"))

# task to clear downloads
@tasks.loop(hours=72.0)
async def clear_cache():
  print("clear cache")
  try:
    shutil.rmtree(r'downloads/')
    print("Cleared downloads cache.")
  except FileNotFoundError:
    print("Already cleared.")

######
# FUNCTIONS
######

# Command to set up database for channels
async def setup(ctx):
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

# Function to run on error
def error_skip(ctx):
    database.lset(str(ctx.channel.id), 1, "1")
    database.lset(str(ctx.channel.id), 0, "")

# Function to send a bird picture:
# ctx - context for message (discord thing)
# bird - bird picture to send (str)
# on_error - function to run when an error occurs (function)
# message - text message to send before bird picture (str)
# addOn - string to append to search for female/juvenile birds (str)
async def send_bird(ctx, bird, on_error=None, message=None, addOn=""):
    if bird is "":
        print("error - bird is blank")
        await ctx.send("There was an error fetching birds. Please try again.")
        database.lset(str(ctx.channel.id), 0, "")
        database.lset(str(ctx.channel.id), 1, "0")
        if on_error is not None:
            on_error(ctx)
        return

    await ctx.send("**Fetching.** This may take a while.", delete_after=10.0)
    # trigger "typing" discord message
    await ctx.trigger_typing()

    # fetch scientific names of birds
    if bird in birdList:
        index = birdList.index(bird)
        sciBird = sciBirdList[index]
    else:
        sciBird = bird

    try:
        print("trying")
        images = os.listdir("downloads/"+sciBird+addOn+"/")
        print("downloads/"+sciBird+addOn+"/")
        for path in images:
            images[images.index(path)] = "downloads/"+sciBird+addOn+"/"+path
        print("images: "+str(images))
    except FileNotFoundError:
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
    j = randint(0, int(round(len(images)*(4/5))))
    while j == prevJ:
        print("prevJ: "+str(prevJ))
        print("j: "+str(j))
        print("same photo, skipping")
        j = randint(0, int(round(len(images)*(4/5))))
    database.lset(str(ctx.channel.id), 7, str(j))

    for x in range(j, len(images)):  # check file type and size
        image_link = images[x]
        extension = image_link.split('.')[-1]
        print("extension: "+str(extension))
        statInfo = os.stat(image_link)
        if extension.lower() in valid_extensions and statInfo.st_size < 8000000:  # 8mb discord limit
            print("found one!")
            break
        print("size: "+str(statInfo.st_size))

    filename = str(image_link)
    statInfo = os.stat(filename)
    if statInfo.st_size > 8000000:  # another filesize check
        await ctx.send("Oops! File too large :(\nPlease try again.")
    else:
        with open(filename, 'rb') as img:
            if message is not None:
                await ctx.send(message)
            # change filename to avoid spoilers
            await ctx.send(file=discord.File(img, filename="bird."+extension))

# sends a birdsong
async def send_birdsong(ctx, bird, message=None):
    await ctx.send("**Fetching.** This may take a while.", delete_after=10.0)
    # trigger "typing" discord message
    await ctx.trigger_typing()
    if bird in songBirds:
        index = songBirds.index(bird)
        sciBird = sciSongBirds[index]
    else:
        sciBird = bird
    # fetch sounds
    query = sciBird.replace(" ", "%20")
    response = requests.get(
        "https://www.xeno-canto.org/api/2/recordings?query="+query+"%20q:A&page=1")

    if response.status_code == 200:
        recordings = response.json()["recordings"]
        print("recordings: "+str(recordings))
        if len(recordings) == 0:  # bird not found
            # try with common name instead
            query = bird.replace(" ", "%20")
            response = requests.get(
                "https://www.xeno-canto.org/api/2/recordings?query="+query+"%20q:A&page=1")
            if response.status_code == 200:
                recordings = response.json()["recordings"]
            else:
                await ctx.send("**A GET error occurred when fetching the song. Please try again.**")
                print("error:" + str(response.status_code))

        if len(recordings) != 0:
            url = str(
                "http:"+recordings[randint(0, len(recordings)-1)]["file"])

            songFile = requests.get(url)
            if songFile.status_code == 200:
                with open("birdsong.mp3", 'wb') as fd:
                    fd.write(songFile.content)

                # remove spoilers in tag metadata
                audioFile = eyed3.load("birdsong.mp3")
                audioFile.tag.remove("birdsong.mp3")

                # send song
                if message is not None:
                    await ctx.send(message)
                    # change filename to avoid spoilers
                    with open("birdsong.mp3", "rb") as song:
                      await ctx.send(file=discord.File(song, filename="bird.mp3"))
            else:
                await ctx.send("**A GET error occurred when fetching the song. Please try again.**")
                print("error:" + str(songFile.status_code))
        else:
            await ctx.send("Unable to get song - bird was not found.")

    else:
        await ctx.send("**A GET error occurred when fetching the song. Please try again.**")
        print("error:" + str(response.status_code))


# spellcheck - allows one letter off/extra
def spellcheck(worda, wordb):
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
            if wrongcount > 1:
                return False
            else:
                return True
        if abs(len(longerword)-len(shorterword)) > 1:
            return False
        else:
            for i in range(len(shorterword)):
                try:
                    if longerword[i] != shorterword[i]:
                        wrongcount += 1
                        del longerword[i]
                except:
                    return False
            if wrongcount < 2:
                return True
            else:
                return False
    else:
        return True

######
# COMMANDS
######

# Bird command - no args
@bot.command(help='- Sends a random bird image for you to ID', aliases=["b"], usage="[female|juvenile]")  # help text
@commands.cooldown(1, 10.0, type=commands.BucketType.channel)  # 10 second cooldown
async def bird(ctx, add_on=""):
    print("bird")

    await setup(ctx)
    await user_setup(ctx)

    if not (add_on == "female" or add_on == "juvenile" or add_on == ""):
        await ctx.send("This command only takes female, juvenile, or nothing!")
        return

    print("bird: "+str(database.lindex(str(ctx.channel.id), 0))[2:-1])
    print("answered: "+str(int(database.lindex(str(ctx.channel.id), 1))))

    answered = int(database.lindex(str(ctx.channel.id), 1))
    # check to see if previous bird was answered
    if answered is True:  # if yes, give a new bird
        database.lset(str(ctx.channel.id), 1, "0")
        currentBird = birdList[randint(0, len(birdList)-1)]
        prevB = str(database.lindex(str(ctx.channel.id), 8))[2:-1]
        while currentBird == prevB:
            currentBird = birdList[randint(0, len(birdList)-1)]
        database.lset(str(ctx.channel.id), 8, str(currentBird))
        database.lset(str(ctx.channel.id), 0, str(currentBird))
        print("currentBird: "+str(currentBird))
        await send_bird(ctx, currentBird, error_skip, message="*Here you go!* \n**Use `o>bird` again to get a new picture of the same bird, or `o>skip` to get a new bird. Use `o>check guess` to check your answer. Use `o>hint` for a hint.**", addOn=add_on)
    else:  # if no, give the same bird
        await send_bird(ctx, str(database.lindex(str(ctx.channel.id), 0))[2:-1], error_skip, message="*Here you go!* \n**Use `o>bird` again to get a new picture of the same bird, or `o>skip` to get a new bird. Use `o>check guess` to check your answer.**", addOn=add_on)
        database.lset(str(ctx.channel.id), 1, "0")

# goatsucker command - no args
@bot.command(help='- Sends a random goatsucker to ID', aliases=["gs"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def goatsucker(ctx):
    print("goatsucker")

    await setup(ctx)
    await user_setup(ctx)

    goatsuckers = ["Common Pauraque", "Chuck-will's-widow", "Whip-poor-will"]
    answered = int(database.lindex(str(ctx.channel.id), 6))
    # check to see if previous bird was answered
    if answered is True:  # if yes, give a new bird
        database.lset(str(ctx.channel.id), 6, "0")
        currentBird = goatsuckers[randint(0, 2)]
        database.lset(str(ctx.channel.id), 5, str(currentBird))
        print("currentBird: "+str(currentBird))
        await send_bird(ctx, currentBird, message="*Here you go!* \n**Use `o>bird` again to get a new picture of the same goatsucker, or `o>skipgoat` to get a new bird. Use `o>checkgoat guess` to check your answer. Use `o>hint` for a hint.**")
    else:  # if no, give the same bird
        await send_bird(ctx, str(database.lindex(str(ctx.channel.id), 5))[2:-1], message="*Here you go!* \n**Use `o>bird` again to get a new picture of the same bird, or `o>skip` to get a new bird. Use `o>check guess` to check your answer.**")
        database.lset(str(ctx.channel.id), 6, "0")

# picks a random bird call to send
@bot.command(help="- Sends a bird call to ID", aliases=["s"])
@commands.cooldown(1, 10.0, type=commands.BucketType.channel)
async def song(ctx):
    print("song")

    await setup(ctx)
    await user_setup(ctx)

    songAnswered = int(database.lindex(str(ctx.channel.id), 3))
    # check to see if previous bird was answered
    if songAnswered is True:  # if yes, give a new bird
        v = randint(0, len(songBirds)-1)
        currentSongBird = songBirds[v]
        prevS = str(database.lindex(str(ctx.channel.id), 9))[2:-1]
        while currentSongBird == prevS:
            currentSongBird = songBirds[randint(0, len(songBirds)-1)]
        database.lset(str(ctx.channel.id), 9, str(currentBird))
        database.lset(str(ctx.channel.id), 2, str(currentSongBird))
        print("currentSongBird: "+str(currentSongBird))
        await send_birdsong(ctx, currentSongBird, message="*Here you go!* \n**Use `o>song` again to get a new sound of the same bird, or `o>skipsong` to get a new bird. Use `o>checksong guess` to check your answer. Use `o>hintsong` for a hint.**")
        database.lset(str(ctx.channel.id), 3, "0")
    else:
        await send_birdsong(ctx, str(database.lindex(str(ctx.channel.id), 2))[2:-1], message="*Here you go!* \n**Use `o>song` again to get a new sound of the same bird, or `o>skipsong` to get a new bird. Use `o>checksong guess` to check your answer. Use `o>hintsong` for a hint.**")
        database.lset(str(ctx.channel.id), 3, "0")

# Check command - argument is the guess
@bot.command(help='- Checks your answer.', usage="guess", aliases=["guess", "c"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def check(ctx, *, arg):
    print("check")
    global achievement

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
    if currentBird == "":  # no bird
        await ctx.send("You must ask for a bird first!")
    else:  # if there is a bird, it checks answer
        index = birdList.index(currentBird)
        sciBird = sciBirdList[index]
        database.lset(str(ctx.channel.id), 0, "")
        database.lset(str(ctx.channel.id), 1, "1")
        if spellcheck(arg.lower().replace("-", " "), currentBird.lower().replace("-", " ")) is True:
            await ctx.send("Correct! Good job!")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
            database.lset(str(ctx.channel.id), 4, str(
                int(database.lindex(str(ctx.channel.id), 4))+1))
            database.zincrby("users", 1, str(ctx.message.author.id))
            if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                number = str(
                    int(database.zscore("users", str(ctx.message.author.id))))
                await ctx.send("Wow! You have answered "+number+" birds correctly!")
                filename = 'achievements/' + number + ".PNG"
                with open(filename, 'rb') as img:
                    await ctx.send(file=discord.File(img, filename="award.png"))

        else:
            await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
        print("currentBird: "+str(currentBird.lower().replace("-", " ")))
        print("args: "+str(arg.lower().replace("-", " ")))

# Check command - argument is the guess
@bot.command(help='- Checks your goatsucker.', usage="guess", aliases=["cg"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def checkgoat(ctx, *, arg):
    print("checkgoat")
    global achievement

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
    if currentBird == "":  # no bird
        await ctx.send("You must ask for a bird first!")
    else:  # if there is a bird, it checks answer
        index = birdList.index(currentBird)
        sciBird = sciBirdList[index]
        database.lset(str(ctx.channel.id), 6, "1")
        database.lset(str(ctx.channel.id), 5, "")
        if spellcheck(arg.lower().replace("-", " "), currentBird.lower().replace("-", " ")) is True:
            await ctx.send("Correct! Good job!")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
            database.lset(str(ctx.channel.id), 4, str(
                int(database.lindex(str(ctx.channel.id), 4))+1))
            database.zincrby("users", 1, str(ctx.message.author.id))
            if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                number = str(
                    int(database.zscore("users", str(ctx.message.author.id))))
                await ctx.send("Wow! You have answered "+number+" birds correctly!")
                filename = 'achievements/' + number + ".PNG"
                with open(filename, 'rb') as img:
                    await ctx.send(file=discord.File(img, filename="award.png"))

        else:
            await ctx.send("Sorry, the bird was actually " + currentBird.lower() + ".")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
        print("currentBird: "+str(currentBird.lower().replace("-", " ")))
        print("args: "+str(arg.lower().replace("-", " ")))

# Check command - argument is the guess
@bot.command(help='- Checks the song', aliases=["songcheck", "cs", "sc"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def checksong(ctx, *, arg):
    print("checksong")
    global achievement

    await setup(ctx)
    await user_setup(ctx)

    currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
    if currentSongBird == "":  # no bird
        await ctx.send("You must ask for a bird call first!")
    else:  # if there is a bird, it checks answer
        index = songBirds.index(currentSongBird)
        sciBird = sciSongBirds[index]
        database.lset(str(ctx.channel.id), 2, "")
        database.lset(str(ctx.channel.id), 3, "1")
        if spellcheck(arg.lower().replace("-", " "), currentSongBird.lower().replace("-", " ")) is True:
            await ctx.send("Correct! Good job!")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
            database.lset(str(ctx.channel.id), 4, str(
                int(database.lindex(str(ctx.channel.id), 4))+1))
            database.zincrby("users", 1, str(ctx.message.author.id))
            if int(database.zscore("users", str(ctx.message.author.id))) in achievement:
                number = str(
                    int(database.zscore("users", str(ctx.message.author.id))))
                await ctx.send("Wow! You have answered "+number+" birds correctly!")
                filename = 'achievements/' + number + ".PNG"
                with open(filename, 'rb') as img:
                    await ctx.send(file=discord.File(img, filename="award.png"))

        else:
            await ctx.send("Sorry, the bird was actually " + currentSongBird.lower() + ".")
            page = wikipedia.page(sciBird)
            await ctx.send(page.url)
        print("currentBird: "+str(currentSongBird.lower().replace("-", " ")))
        print("args: "+str(arg.lower().replace("-", " ")))

# Skip command - no args
@bot.command(help="- Skip the current bird to get a new one", aliases=["sk"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def skip(ctx):
    print("skip")

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
    database.lset(str(ctx.channel.id), 0, "")
    database.lset(str(ctx.channel.id), 1, "1")
    if currentBird != "":  # check if there is bird
        birdPage = wikipedia.page(currentBird+"(bird)")
        await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
    else:
        await ctx.send("You need to ask for a bird first!")

# Skip command - no args
@bot.command(help="- Skip the current goatsucker to get a new one", aliases=["goatskip", "sg"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def skipgoat(ctx):
    print("skipgoat")

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
    database.lset(str(ctx.channel.id), 5, "")
    database.lset(str(ctx.channel.id), 6, "1")
    if currentBird != "":  # check if there is bird
        birdPage = wikipedia.page(currentBird+"(bird)")
        await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
    else:
        await ctx.send("You need to ask for a bird first!")

# Skip song command - no args
@bot.command(help="- Skip the current bird call to get a new one", aliases=["songskip", "ss"])
@commands.cooldown(1, 10.0, type=commands.BucketType.channel)
async def skipsong(ctx):
    print("skipsong")

    await setup(ctx)
    await user_setup(ctx)

    database.lset(str(ctx.channel.id), 3, "1")
    currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
    if currentSongBird != "":  # check if there is bird
        birdPage = wikipedia.page(currentSongBird+"(bird)")
        await ctx.send("Ok, skipping " + birdPage.url)  # sends wiki page
    else:
        await ctx.send("You need to ask for a bird first!")

# give hint
@bot.command(help="- Gives first letter of current bird", aliases=["h"])
@commands.cooldown(1, 3.0, type=commands.BucketType.channel)
async def hint(ctx):
    print("hint")

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 0))[2:-1]
    if currentBird != "":  # check if there is bird
        await ctx.send("The first letter is " + currentBird[0])
    else:
        await ctx.send("You need to ask for a bird first!")

# give hint for goat
@bot.command(help="- Gives first letter of current goatsucker", aliases=["goathint", "hg", "gh"])
@commands.cooldown(1, 3.0, type=commands.BucketType.channel)
async def hintgoat(ctx):
    print("hintgoat")

    await setup(ctx)
    await user_setup(ctx)

    currentBird = str(database.lindex(str(ctx.channel.id), 5))[2:-1]
    if currentBird != "":  # check if there is bird
        await ctx.send("The first letter is " + currentBird[0])
    else:
        await ctx.send("You need to ask for a bird first!")

# give hint for song
@bot.command(help="- Gives first letter of current bird call", aliases=["songhint", "hs", "sh"])
@commands.cooldown(1, 3.0, type=commands.BucketType.channel)
async def hintsong(ctx):
    print("hintsong")

    await setup(ctx)
    await user_setup(ctx)

    currentSongBird = str(database.lindex(str(ctx.channel.id), 2))[2:-1]
    if currentSongBird != "":  # check if there is bird
        await ctx.send("The first letter is " + currentSongBird[0])
    else:
        await ctx.send("You need to ask for a bird first!")

# Gives call+image of 1 bird
@bot.command(help="- Gives an image and call of a bird", aliases=['i'])
@commands.cooldown(1, 10.0, type=commands.BucketType.channel)
async def info(ctx, *, arg):
    print("info")

    await setup(ctx)
    await user_setup(ctx)

    bird = arg
    print("info")
    await ctx.send("Please wait a moment.")
    await send_bird(ctx, str(bird), message="Here's the image!")
    await send_birdsong(ctx, str(bird),  "Here's the call!")

# Wiki command - argument is the wiki page
@bot.command(help="- Fetch the wikipedia page for any given argument")
@commands.cooldown(1, 8.0, type=commands.BucketType.channel)
async def wiki(ctx, *, arg):
    print("wiki")

    await setup(ctx)
    await user_setup(ctx)

    try:
        page = wikipedia.page(arg)
        await ctx.send(page.url)
    except wikipedia.exceptions.DisambiguationError:
        await ctx.send("Sorry, that page was not found.")
    except wikipedia.exceptions.PageError:
        await ctx.send("Sorry, that page was not found.")

# returns total number of correct answers so far
@bot.command(help="- total correct answers")
@commands.cooldown(1, 8.0, type=commands.BucketType.channel)
async def score(ctx):
    print("score")

    await setup(ctx)
    await user_setup(ctx)

    totalCorrect = int(database.lindex(str(ctx.channel.id), 4))
    await ctx.send("Wow, looks like a total of " + str(totalCorrect) + " birds have been answered correctly in this channel! Good job everyone!")

# meme command - sends a random bird video/gif
@bot.command(help="- sends a funny bird video!")
@commands.cooldown(1, 300.0, type=commands.BucketType.channel)
async def meme(ctx):
    print("meme")

    await setup(ctx)
    await user_setup(ctx)

    x = randint(0, len(memeList))
    await ctx.send(memeList[x])

# sends correct answers by a user
@bot.command(brief="- how many correct answers given by a user", help="- how many correct answers given by a user, mention someone to get their score, don't mention anyone to get your score", aliases=["us"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def userscore(ctx, user=None):
    print("user score")

    await setup(ctx)
    await user_setup(ctx)

    if user is not None:
        try:
            usera = int(user[1:len(user)-1].strip("@!"))
            print(usera)
        except ValueError:
            await ctx.send("Mention a user!")
            return
        if database.zscore("users", str(usera)) is not None:
            times = str(int(database.zscore("users", str(usera))))
            user = "<@"+str(usera)+">"
        else:
            await ctx.send("This user does not exist on our records!")
            return
    else:
        if database.zscore("users", str(ctx.message.author.id)) is not None:
            user = "<@"+str(ctx.message.author.id)+">"
            times = str(
                int(database.zscore("users", str(ctx.message.author.id))))
        else:
            await ctx.send("You haven't used this bot yet! (except for this)")
            return
    embed = discord.Embed(type="rich", colour=discord.Color.blurple())
    embed.set_author(name="Bird ID - An Ornithology Bot")
    embed.add_field(name="User Score:", value=user +
                    " has answered correctly " + times + " times.")
    await ctx.send(embed=embed)


@bot.command(brief="- Top scores", help="- Top scores, can be between 1 and 5, default is 3", aliases=["lb"])
@commands.cooldown(1, 5.0, type=commands.BucketType.channel)
async def leaderboard(ctx, placings=5):
    print("leaderboard")

    await setup(ctx)
    await user_setup(ctx)

    leaderboard_list = []
    if database.zcard("users") == 0:
        await ctx.send("There are no users in the database.")
        return
    if placings > 10 or placings < 1:
        await ctx.send("Not a valid number. Pick one between 1 and 10!")
        return
    if placings > database.zcard("users"):
        placings = database.zcard("users")

    leaderboard_list = database.zrevrangebyscore(
        "users", "+inf", "-inf", 0, placings, True)
    embed = discord.Embed(type="rich", colour=discord.Color.blurple())
    embed.set_author(name="Bird ID - An Ornithology Bot")
    leaderboard = ""

    for x in range(len(leaderboard_list)):
        leaderboard += str(x+1) + ". <@"+str(leaderboard_list[x][0])[
            2:-1] + "> - "+str(int(leaderboard_list[x][1]))+"\n"
    embed.add_field(name="Leaderboard", value=leaderboard, inline=False)

    if database.zscore("users", str(ctx.message.author.id)) is not None:
        placement = int(database.zrevrank(
            "users", str(ctx.message.author.id))) + 1
        embed.add_field(name="You:", value="You are #" +
                        str(placement)+" on the leaderboard.", inline=False)
    else:
        embed.add_field(
            name="You:", value="You haven't answered any correctly.")

    await ctx.send(embed=embed)

# Test command - for testing purposes only
@bot.command(help="- test command")
async def test(ctx):
    print("test")

    embed = discord.Embed(type="rich", colour=discord.Color.blurple())
    embed.set_author(name="Bird ID - An Ornithology Bot")
    embed.add_field(name="Test", value="whee")
    await ctx.send(embed=embed)

######
# ERROR CHECKING
######

# Custom Error Definitions
class LeaderBoardError(Exception):
    pass


# Command-specific error checking
@leaderboard.error
async def leader_error(ctx, error):
    print("leaderboard error")
    if isinstance(error, commands.BadArgument):
        await ctx.send('Not an integer!')
        raise LeaderBoardError


# Global error checking
@bot.event
async def on_command_error(ctx, error):
    print("Error: "+str(error))
    if isinstance(error, commands.CommandOnCooldown):  # send cooldown
        await ctx.send("**Cooldown.** Try again after "+str(round(error.retry_after))+" s.", delete_after=5.0)

    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, the command was not found.")

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("This command requires an argument!")

    elif isinstance(error, LeaderBoardError):
        return

    elif isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, redis.exceptions.ResponseError):
            if database.exists(str(ctx.channel.id)):
                await ctx.send("**An unexpected ResponseError has occurred.** \n*Please log this message in #feedback* \n**Error:** " + str(error))
            else:
                await setup(ctx)
                await ctx.send("Please run that command again.")
        else:
            print("uncaught command error")
            await ctx.send("**An uncaught error has occurred.** \n*Please log this message in #feedback.* \n**Error:**  " + str(error))
            raise error

    else:
        print("uncaught non-command")
        await ctx.send("**An uncaught non-command error has occurred.** \n*Please log this message in #feedback.* \n**Error:**  " + str(error))
        raise error


# Start the task
clear_cache.start()

# Actually run the bot
token = os.getenv("token")
bot.run(token)
