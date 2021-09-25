# tools.py | helper FastAPI routes
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

import urllib.parse
from io import BytesIO

import aiohttp
from fastapi import APIRouter, HTTPException

from bot.core import _black_and_white
from web.data import logger
from web.functions import send_file

router = APIRouter(prefix="/tools", tags=["tools"])

valid_endpoints = "test.cdn.download.ams.birds.cornell.edu"
valid_content_types = ("image/png", "image/jpeg")


@router.get("/bw")
async def convert_bw(url: str):
    logger.info("endpoint: convert bw")
    logger.info(f"args: url: {url}")

    parsed_url = urllib.parse.urlparse(url)
    logger.info(f"parsed url: {parsed_url}")
    if parsed_url.netloc not in valid_endpoints:
        logger.info("invalid url")
        raise HTTPException(status_code=415, detail="invalid url")

    image, content_type = await _bw_helper(url)
    return send_file(image, media_type=content_type)


async def _bw_helper(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.info("invalid response")
                raise HTTPException(
                    status_code=response.status, detail="error fetching url"
                )
            if response.content_type not in valid_content_types:
                logger.info("invalid content type")
                raise HTTPException(status_code=415, detail="invalid content type")
            return (
                _black_and_white(BytesIO(await response.read())),
                response.content_type,
            )
