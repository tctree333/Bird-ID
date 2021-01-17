# tools.py | helper Flask routes
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
import urllib.parse
from io import BytesIO

import aiohttp
import flask

from bot.core import _black_and_white
from web.data import logger

bp = flask.Blueprint("tools", __name__, url_prefix="/tools")

valid_endpoints = "test.cdn.download.ams.birds.cornell.edu"
valid_content_types = ("image/png", "image/jpeg")


@bp.route("/bw", methods=["GET"])
def convert_bw():
    logger.info("endpoint: convert bw")
    url = flask.request.args.get("url", default=None, type=str)
    logger.info(f"args: url: {url}")

    if not url:
        logger.info("no url")
        flask.abort(415, "url not specified")

    parsed_url = urllib.parse.urlparse(url)
    logger.info(f"parsed url: {parsed_url}")
    if parsed_url.netloc not in valid_endpoints:
        logger.info("invalid url")
        flask.abort(415, "invalid url")

    image, content_type = asyncio.run(_bw_helper(url))
    return flask.send_file(image, mimetype=content_type)


async def _bw_helper(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.info("invalid response")
                flask.abort(response.status, "error fetching url")
            if response.content_type not in valid_content_types:
                logger.info("invalid content type")
                flask.abort(415, "invalid content type")
            return (
                _black_and_white(BytesIO(await response.read())),
                response.content_type,
            )
