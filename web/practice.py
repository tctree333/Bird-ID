# practice.py | practice related FastAPI routes
# Copyright (C) 2019-2021  EraserBird, person_v1.32, hmmm

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

import random
import string

from fastapi import APIRouter, Request, HTTPException

from bot.core import spellcheck
from bot.data import birdList, get_wiki_url, songBirds
from bot.filters import Filter
from bot.functions import (
    bird_setup,
    incorrect_increment,
    score_increment,
    session_increment,
    streak_increment,
)
from web.data import database, get_session_id, logger
from web.config import NoCacheFileResponse
from web.functions import get_sciname, send_bird

router = APIRouter(prefix="/practice", tags=["practice"])


def increment_bird_frequency(bird, user_id):
    bird_setup(user_id, bird)
    database.zincrby("frequency.bird:global", 1, string.capwords(bird))


@router.get("/get")
async def get_bird(
    request: Request,
    media: str = "images",
    addon: str = "",
    bw: int = 0,
):
    logger.info("endpoint: get bird")
    session_id = get_session_id(request)
    media_type = media

    filters = Filter.parse(addon)
    if bool(bw):
        filters.bw = True
    logger.info(f"args: media: {media_type}; filters: {filters};")

    logger.info(
        "bird: " + database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    )

    tempScore = int(database.hget(f"web.session:{session_id}", "tempScore"))
    if tempScore >= 10:
        logger.info("trial maxed")
        raise HTTPException(status_code=403, detail="Sign in to continue")

    if media_type not in ("images", "songs"):
        logger.error(f"invalid media type {media_type}")
        raise HTTPException(status_code=406, detail="Invalid media type")

    answered = int(database.hget(f"web.session:{session_id}", "answered"))
    logger.info(f"answered: {answered}")
    # check to see if previous bird was answered
    if answered:  # if yes, give a new bird
        id_list = songBirds if media_type == "songs" else birdList
        currentBird = random.choice(id_list)
        user_id = int(database.hget(f"web.session:{session_id}", "user_id"))
        if user_id != 0:
            session_increment(user_id, "total", 1)
            increment_bird_frequency(currentBird, user_id)
        prevB = database.hget(f"web.session:{session_id}", "prevB").decode("utf-8")
        while currentBird == prevB and len(id_list) > 1:
            currentBird = random.choice(id_list)
        database.hset(f"web.session:{session_id}", "prevB", str(currentBird))
        database.hset(f"web.session:{session_id}", "bird", str(currentBird))
        database.hset(f"web.session:{session_id}", "media_type", str(media_type))
        logger.info("currentBird: " + str(currentBird))
        database.hset(f"web.session:{session_id}", "answered", "0")
        file_object, ext = await send_bird(request, currentBird, media_type, filters)
    else:  # if no, give the same bird
        file_object, ext = await send_bird(
            request,
            database.hget(f"web.session:{session_id}", "bird").decode("utf-8"),
            database.hget(f"web.session:{session_id}", "media_type").decode("utf-8"),
            filters,
        )

    logger.info(f"file_object: {file_object}")
    logger.info(f"extension: {ext}")
    return NoCacheFileResponse(path=file_object, filename=f"bird.{ext}")


@router.get("/check")
async def check_bird(request: Request, guess: str = ""):
    logger.info("endpoint: check bird")

    session_id = get_session_id(request)
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird == "":  # no bird
        logger.info("bird is blank")
        raise HTTPException(status_code=406, detail="Bird is blank")
    if guess == "":
        logger.info("empty guess")
        raise HTTPException(status_code=406, detail="Empty guess")

    # if there is a bird, it checks answer
    logger.info("currentBird: " + str(currentBird.lower().replace("-", " ")))
    logger.info("args: " + str(guess.lower().replace("-", " ")))

    sciBird = await get_sciname(currentBird)
    if spellcheck(guess, currentBird) or spellcheck(guess, sciBird):
        logger.info("correct")

        database.hset(f"web.session:{session_id}", "bird", "")
        database.hset(f"web.session:{session_id}", "answered", "1")

        tempScore = int(database.hget(f"web.session:{session_id}", "tempScore"))
        if user_id != 0:
            bird_setup(user_id, currentBird)
            score_increment(user_id, 1)
            session_increment(user_id, "correct", 1)
            streak_increment(user_id, 1)
        elif tempScore >= 10:
            logger.info("trial maxed")
            raise HTTPException(status_code=403, detail="Sign in to continue")
        else:
            database.hset(f"web.session:{session_id}", "tempScore", str(tempScore + 1))

        url = get_wiki_url(currentBird)
        return {
            "guess": guess,
            "answer": currentBird,
            "sciname": sciBird,
            "status": "correct",
            "wiki": url,
        }

    logger.info("incorrect")
    database.hset(f"web.session:{session_id}", "bird", "")
    database.hset(f"web.session:{session_id}", "answered", "1")
    database.zincrby("incorrect:global", 1, currentBird)

    if user_id != 0:
        bird_setup(user_id, currentBird)
        incorrect_increment(user_id, currentBird, 1)
        session_increment(user_id, "incorrect", 1)
        streak_increment(user_id, None)  # reset streak

    url = get_wiki_url(currentBird)
    return {
        "guess": guess,
        "answer": currentBird,
        "sciname": sciBird,
        "status": "incorrect",
        "wiki": url,
    }


@router.get("/skip")
async def skip_bird(request: Request):
    logger.info("endpoint: skip bird")
    session_id = get_session_id(request)
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird != "":  # check if there is bird
        database.hset(f"web.session:{session_id}", "bird", "")
        database.hset(f"web.session:{session_id}", "answered", "1")
        if user_id != 0:
            streak_increment(user_id, None)  # reset streak
        scibird = await get_sciname(currentBird)
        url = get_wiki_url(currentBird)  # sends wiki page
    else:
        logger.info("bird is blank")
        raise HTTPException(status_code=406, detail="Bird is blank")
    return {"answer": currentBird, "sciname": scibird, "wiki": url}


@router.get("/hint")
async def hint_bird(request: Request):
    logger.info("endpoint: hint bird")

    session_id = get_session_id(request)
    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird != "":  # check if there is bird
        return {"hint": currentBird[0]}

    logger.info("bird is blank")
    raise HTTPException(status_code=406, detail="Bird is blank")
