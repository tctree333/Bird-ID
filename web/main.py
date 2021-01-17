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

import random
import urllib.parse

from fastapi.responses import HTMLResponse

from bot.data import birdList
from bot.filters import Filter
from web import practice, user
from web.config import app, NoCacheFileResponse
from web.data import logger
from web.functions import get_media, get_sciname

app.include_router(practice.router)
app.include_router(user.router)


@app.get("/", response_class=HTMLResponse)
def api_index():
    logger.info("index page accessed")
    return "<h1>Hello!</h1><p>This is the index page for the Bird-ID internal API.<p>"


@app.get("/bird")
async def bird_info():
    logger.info("fetching random bird")
    bird = random.choice(birdList)
    logger.info(f"bird: {bird}")
    content = {
        "bird": bird,
        "sciName": (await get_sciname(bird)),
        "imageURL": urllib.parse.quote(f"/image/{bird}"),
        "songURL": urllib.parse.quote(f"/song/{bird}"),
    }
    logger.info(f"{bird} sent!")
    return content


@app.get("/image/{bird}")
async def bird_image(bird: str):
    path = await get_media(bird, "images", Filter())
    return NoCacheFileResponse(path=f"../{path[0]}")


@app.get("/song/{bird}")
async def bird_song(bird: str):
    path = await get_media(bird, "songs", Filter())
    return NoCacheFileResponse(path=f"../{path[0]}")
