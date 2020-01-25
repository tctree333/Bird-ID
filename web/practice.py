import asyncio
import random

import flask
from flask import Blueprint, abort, request

from data.data import get_wiki_url, birdList
from web.config import (FRONTEND_URL, bird_setup, database, get_session_id, logger)
from web.functions import get_sciname, send_bird, spellcheck

bp = Blueprint('practice', __name__, url_prefix='/practice')

@bp.after_request  # enable CORS
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = FRONTEND_URL
    header['Access-Control-Allow-Credentials'] = 'true'
    return response

@bp.route('/get', methods=['GET'])
def get_bird():
    logger.info("endpoint: get bird")
    session_id = get_session_id()
    media_type = request.args.get("media", "images", str)
    addon = request.args.get("addon", "", str)
    bw = bool(request.args.get("bw", 0, int))
    logger.info(f"args: media: {media_type}; addon: {addon}; bw: {bw};")

    logger.info("bird: " + database.hget(f"web.session:{session_id}", "bird").decode("utf-8"))

    tempScore = int(database.hget(f"web.session:{session_id}", "tempScore"))
    if tempScore >= 10:
        logger.info("trial maxed")
        abort(403, "Sign in to continue")

    if media_type != "images" and media_type != "songs":
        logger.error(f"invalid media type {media_type}")
        abort(406, "Invalid media type")
        return

    answered = int(database.hget(f"web.session:{session_id}", "answered"))
    logger.info(f"answered: {answered}")
    # check to see if previous bird was answered
    if answered:  # if yes, give a new bird
        currentBird = random.choice(birdList)
        prevB = database.hget(f"web.session:{session_id}", "prevB").decode("utf-8")
        while currentBird == prevB and len(birdList) > 1:
            currentBird = random.choice(birdList)
        database.hset(f"web.session:{session_id}", "prevB", str(currentBird))
        database.hset(f"web.session:{session_id}", "bird", str(currentBird))
        database.hset(f"web.session:{session_id}", "media_type", str(media_type))
        logger.info("currentBird: " + str(currentBird))
        database.hset(f"web.session:{session_id}", "answered", "0")
        file_object, ext = asyncio.run(send_bird(currentBird, media_type, addon, bw))
    else:  # if no, give the same bird
        file_object, ext = asyncio.run(
            send_bird(
                database.hget(f"web.session:{session_id}", "bird").decode("utf-8"),
                str(database.hget(f"web.session:{session_id}", "media_type"))[2:-1], addon, bw
            )
        )

    logger.info(f"file_object: {file_object}")
    logger.info(f"extension: {ext}")
    return flask.send_file(file_object, attachment_filename=f"bird.{ext}")

@bp.route('/check', methods=['GET'])
def check_bird():
    logger.info("endpoint: check bird")
    bird_guess = request.args.get("guess", "", str)

    session_id = get_session_id()
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird == "":  # no bird
        logger.info("bird is blank")
        abort(406, "Bird is blank")
    elif bird_guess == "":
        logger.info("empty guess")
        abort(406, "Empty guess")
    else:  # if there is a bird, it checks answer
        logger.info("currentBird: " + str(currentBird.lower().replace("-", " ")))
        logger.info("args: " + str(bird_guess.lower().replace("-", " ")))

        bird_setup(user_id, currentBird)
        sciBird = asyncio.run(get_sciname(currentBird))
        if spellcheck(bird_guess, currentBird) or spellcheck(bird_guess, sciBird):
            logger.info("correct")

            database.hset(f"web.session:{session_id}", "bird", "")
            database.hset(f"web.session:{session_id}", "answered", "1")

            tempScore = int(database.hget(f"web.session:{session_id}", "tempScore"))
            if user_id != 0:
                database.zincrby("users:global", 1, str(user_id))
                database.zincrby("streak:global", 1, str(user_id))
                # check if streak is greater than max, if so, increases max
                if database.zscore("streak:global", str(user_id)) > database.zscore("streak.max:global", str(user_id)):
                    database.zadd("streak.max:global", {str(user_id): database.zscore("streak:global", str(user_id))})
            elif tempScore >= 10:
                logger.info("trial maxed")
                abort(403, "Sign in to continue")
            else:
                database.hset(f"web.session:{session_id}", "tempScore", str(tempScore + 1))

            url = get_wiki_url(currentBird)
            return {"guess": bird_guess, "answer": currentBird, "sciname": sciBird, "status": "correct", "wiki": url}

        else:
            logger.info("incorrect")

            database.hset(f"web.session:{session_id}", "bird", "")
            database.hset(f"web.session:{session_id}", "answered", "1")
            database.zincrby("incorrect:global", 1, currentBird)

            if user_id != 0:
                database.zadd("streak:global", {str(user_id): 0})
                database.zincrby(f"incorrect.user:{user_id}", 1, currentBird)

            url = get_wiki_url(currentBird)
            return {"guess": bird_guess, "answer": currentBird, "sciname": sciBird, "status": "incorrect", "wiki": url}

@bp.route('/skip', methods=['GET'])
def skip_bird():
    logger.info("endpoint: skip bird")
    session_id = get_session_id()
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird != "":  # check if there is bird
        database.hset(f"web.session:{session_id}", "bird", "")
        database.hset(f"web.session:{session_id}", "answered", "1")
        if user_id != 0:
            database.zadd("streak:global", {str(user_id): 0})  # end streak

        scibird = asyncio.run(get_sciname(currentBird))
        url = get_wiki_url(currentBird)  # sends wiki page
    else:
        logger.info("bird is blank")
        abort(406, "Bird is blank")
    return {"answer": currentBird, "sciname": scibird, "wiki": url}

@bp.route('/hint', methods=['GET'])
def hint_bird():
    logger.info("endpoint: hint bird")

    session_id = get_session_id()
    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird != "":  # check if there is bird
        return {"hint": currentBird[0]}
    else:
        logger.info("bird is blank")
        abort(406, "Bird is blank")
