# main.py | main Flask routes and error handling
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

import asyncio
import random
import urllib.parse

import flask
from sentry_sdk import capture_exception

from bot.data import birdList
from bot.filters import Filter
from web import practice, user
from web.config import app
from web.data import logger
from web.functions import get_media, get_sciname

app.register_blueprint(practice.bp)
app.register_blueprint(user.bp)


@app.route("/")
def api_index():
    logger.info("index page accessed")
    return "<h1>Hello!</h1><p>This is the index page for the Bird-ID internal API.<p>"


@app.route("/bird")
def bird_info():
    logger.info("fetching random bird")
    content = {}
    bird = random.choice(birdList)
    logger.info(f"bird: {bird}")
    content["bird"] = bird
    content["sciName"] = asyncio.run(get_sciname(bird))
    content["imageURL"] = urllib.parse.quote(f"/image/{bird}")
    content["songURL"] = urllib.parse.quote(f"/song/{bird}")
    logger.info(f"{bird} sent!")
    return content


@app.route("/image/<string:bird>")
def bird_image(bird):
    path = asyncio.run(get_media(bird, "images", Filter()))
    return flask.send_file(f"../{path[0]}")


@app.route("/song/<string:bird>")
def bird_song(bird):
    path = asyncio.run(get_media(bird, "songs", Filter()))
    return flask.send_file(f"../{path[0]}")


@app.errorhandler(403)
def not_allowed(e):
    capture_exception(e)
    return flask.jsonify(error=str(e)), 403


@app.errorhandler(404)
def not_found(e):
    return flask.jsonify(error=str(e)), 404


@app.errorhandler(406)
def input_error(e):
    capture_exception(e)
    return flask.jsonify(error=str(e)), 406


@app.errorhandler(500)
def other_internal_error(e):
    capture_exception(e)
    return flask.jsonify(error=str(e)), 500


@app.errorhandler(503)
def internal_error(e):
    capture_exception(e)
    return flask.jsonify(error=str(e)), 503
