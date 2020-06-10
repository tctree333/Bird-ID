import asyncio
import urllib.parse
from io import BytesIO

import aiohttp
import flask

from bot.core import _black_and_white
from web.config import logger

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
