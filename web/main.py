import random
import asyncio
import flask
import urllib.parse

from web.data import birdList, logger, app
from web.functions import get_media, get_sciname

from . import practice, auth
app.register_blueprint(practice.bp)
app.register_blueprint(auth.bp)

@app.route('/')
def api_index():
    logger.info("index page accessed")
    return "<h1>Hello!</h1><p>This is the index page for the Bird-ID internal API.<p>"


@app.route('/bird')
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


@app.route('/image/<string:bird>')
def bird_image(bird):
    path, ext = asyncio.run(get_media(bird, "images"))
    return flask.send_file(f"../{path}")


@app.route('/song/<string:bird>')
def bird_song(bird):
    path, ext = asyncio.run(get_media(bird, "songs"))
    return flask.send_file(f"../{path}")

