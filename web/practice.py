import asyncio
import random
import string

import flask

from bot.core import spellcheck
from bot.data import birdList, get_wiki_url, songBirds
from bot.functions import (bird_setup, incorrect_increment, score_increment,
                           session_increment, streak_increment)
from web.config import FRONTEND_URL, database, get_session_id, logger
from web.functions import get_sciname, send_bird

bp = flask.Blueprint('practice', __name__, url_prefix='/practice')

@bp.after_request  # enable CORS
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = FRONTEND_URL
    header['Access-Control-Allow-Credentials'] = 'true'
    return response

def increment_bird_frequency(bird, user_id):
    bird_setup(user_id, bird)
    database.zincrby("frequency.bird:global", 1, string.capwords(bird))

@bp.route('/get', methods=['GET'])
def get_bird():
    logger.info("endpoint: get bird")
    session_id = get_session_id()
    media_type = flask.request.args.get("media", "images", str)
    addon = flask.request.args.get("addon", "", str)
    bw = bool(flask.request.args.get("bw", 0, int))
    logger.info(f"args: media: {media_type}; addon: {addon}; bw: {bw};")

    logger.info("bird: " + database.hget(f"web.session:{session_id}", "bird").decode("utf-8"))

    tempScore = int(database.hget(f"web.session:{session_id}", "tempScore"))
    if tempScore >= 10:
        logger.info("trial maxed")
        flask.abort(403, "Sign in to continue")

    if media_type != "images" and media_type != "songs":
        logger.error(f"invalid media type {media_type}")
        flask.abort(406, "Invalid media type")
        return

    answered = int(database.hget(f"web.session:{session_id}", "answered"))
    logger.info(f"answered: {answered}")
    # check to see if previous bird was answered
    if answered:  # if yes, give a new bird
        id_list = (songBirds if media_type == "songs" else birdList)
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
    bird_guess = flask.request.args.get("guess", "", str)

    session_id = get_session_id()
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    currentBird = database.hget(f"web.session:{session_id}", "bird").decode("utf-8")
    if currentBird == "":  # no bird
        logger.info("bird is blank")
        flask.abort(406, "Bird is blank")
    elif bird_guess == "":
        logger.info("empty guess")
        flask.abort(406, "Empty guess")
    else:  # if there is a bird, it checks answer
        logger.info("currentBird: " + str(currentBird.lower().replace("-", " ")))
        logger.info("args: " + str(bird_guess.lower().replace("-", " ")))

        sciBird = asyncio.run(get_sciname(currentBird))
        if spellcheck(bird_guess, currentBird) or spellcheck(bird_guess, sciBird):
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
                flask.abort(403, "Sign in to continue")
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
                bird_setup(user_id, currentBird)
                incorrect_increment(user_id, currentBird, 1)
                session_increment(user_id, "incorrect", 1)
                streak_increment(user_id, None) # reset streak

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
            streak_increment(user_id, None) # reset streak
        scibird = asyncio.run(get_sciname(currentBird))
        url = get_wiki_url(currentBird)  # sends wiki page
    else:
        logger.info("bird is blank")
        flask.abort(406, "Bird is blank")
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
        flask.abort(406, "Bird is blank")
