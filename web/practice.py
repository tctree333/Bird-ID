import random
import flask
import asyncio

from flask import request, Blueprint
from web.data import get_session_id, logger, database, birdList
from web.functions import send_bird

bp = Blueprint('practice', __name__, url_prefix='/practice')


@bp.route('/get', methods=['GET'])
def get_bird():
    logger.info("endpoint: get bird")
    session_id = get_session_id()
    media_type = request.args.get("media", "images", str)
    addon = request.args.get("addon", "", str)
    bw = bool(request.args.get("bw", 0, int))
    logger.info(f"args: media: {media_type}; addon: {addon}; bw: {bw};")
    file_object, ext = asyncio.run(
        send_bird_(session_id, media_type, addon, bw))
    logger.info(f"file_object: {file_object}")
    logger.info(f"extension: {ext}")
    return flask.send_file(file_object, attachment_filename=f"bird.{ext}")


@bp.route('/check', methods=['GET'])
def check_bird():
    logger.info("endpoint: check bird")
    bird_guess = request.args.get("guess", "", str)
    return {"bird_guess": bird_guess}


@bp.route('/skip', methods=['GET'])
def skip_bird():
    logger.info("endpoint: skip bird")
    return {"success": 200}


@bp.route('/hint', methods=['GET'])
def hint_bird():
    logger.info("endpoint: hint bird")
    return {"success": 200}


async def send_bird_(session_id: str, media_type: str, add_on: str = "", bw: bool = False):
    logger.info(
        "bird: " + str(database.hget(f"web.session:{session_id}", "bird"))[2:-1])

    answered = int(database.hget(f"web.session:{session_id}", "answered"))
    logger.info(f"answered: {answered}")
    # check to see if previous bird was answered
    if answered:  # if yes, give a new bird
        currentBird = random.choice(birdList)
        prevB = str(database.hget(f"web.session:{session_id}", "prevB"))[2:-1]
        while currentBird == prevB:
            currentBird = random.choice(birdList)
        database.hset(f"web.session:{session_id}", "prevB", str(currentBird))
        database.hset(f"web.session:{session_id}", "bird", str(currentBird))
        database.hset(f"web.session:{session_id}",
                      "media_type", str(media_type))
        logger.info("currentBird: " + str(currentBird))
        database.hset(f"web.session:{session_id}", "answered", "0")
        return await send_bird(currentBird, media_type, add_on, bw)
    else:  # if no, give the same bird
        return await send_bird(
            str(database.hget(f"web.session:{session_id}", "bird"))[2:-1],
            str(database.hget(f"web.session:{session_id}", "media_type"))[
                2:-1],
            add_on,
            bw
        )
