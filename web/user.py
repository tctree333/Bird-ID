# user.py | user related FastAPI routes
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

import os
import re

from authlib.common.errors import AuthlibBaseError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Cookie, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sentry_sdk import capture_exception

from web.config import FRONTEND_URL, app
from web.data import database, get_session_id, logger, update_web_user, verify_session

router = APIRouter(prefix="/user", tags=["user"])
oauth = OAuth()

REL_REGEX = r"/[^/](?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))*"
relative_url_regex = re.compile(REL_REGEX)

DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
oauth.register(
    name="discord",
    client_id=601917808137338900,
    client_secret=DISCORD_CLIENT_SECRET,
    access_token_url="https://discord.com/api/oauth2/token",
    access_token_params=None,
    authorize_url="https://discord.com/api/oauth2/authorize",
    authorize_params=None,
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify", "prompt": "consent"},
)
discord = oauth.discord


@router.get("/login")
async def login(
    request: Request,
    response: Response,
    redirect: str = "/",
):
    logger.info("endpoint: login")

    if relative_url_regex.fullmatch(redirect) is None:
        redirect = "/"
    response.set_cookie(
        key="redirect",
        value=redirect,
        max_age=180,
        samesite="lax",
        httponly=True,
        secure=True,
    )
    redirect_uri = request.url_for("authorize")
    return await oauth.discord.authorize_redirect(request, redirect_uri)


@router.get("/logout")
async def logout(request: Request, redirect: str = "/"):
    logger.info("endpoint: logout")

    if relative_url_regex.fullmatch(redirect) is not None:
        redirect_url = FRONTEND_URL + redirect
    else:
        redirect_url = FRONTEND_URL

    session_id = get_session_id(request)
    user_id = verify_session(session_id)

    if isinstance(user_id, int):
        logger.info("deleting user data, session data")
        database.delete(f"web.user:{user_id}", f"web.session:{session_id}")
    else:
        logger.info("deleting session data")
        database.delete(f"web.session:{session_id}")

    request.session.clear()
    return RedirectResponse(redirect_url)


@router.route("/authorize")
async def authorize(request: Request, redirect: str = Cookie("/")):
    logger.info("endpoint: authorize")

    token = await oauth.discord.authorize_access_token(request)
    resp = await oauth.discord.get("users/@me", token=token)
    profile_ = resp.json()

    await update_web_user(request, profile_)

    if relative_url_regex.fullmatch(redirect) is not None:
        redirection = FRONTEND_URL + redirect
    else:
        redirection = FRONTEND_URL + "/"

    request.session.pop("redirect", None)

    return RedirectResponse(redirection)


@router.route("/profile")
def profile(request: Request):
    logger.info("endpoint: profile")

    session_id = get_session_id(request)
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    if user_id == 0:
        logger.info("not logged in")
        raise HTTPException(status_code=403, detail="Sign in to continue")

    avatar_hash, avatar_url, username, discriminator = (
        stat.decode("utf-8")
        for stat in database.hmget(
            f"web.user:{user_id}",
            "avatar_hash",
            "avatar_url",
            "username",
            "discriminator",
        )
    )
    placings = int(database.zscore("users:global", str(user_id)))
    max_streak = int(database.zscore("streak.max:global", str(user_id)))
    missed_birds = [
        [stats[0].decode("utf-8"), int(stats[1])]
        for stats in database.zrevrangebyscore(
            f"incorrect.user:{user_id}", "+inf", "-inf", 0, 10, True
        )
    ]
    return {
        "avatar_hash": avatar_hash,
        "avatar_url": avatar_url,
        "username": username,
        "discriminator": discriminator,
        "rank": placings,
        "max_streak": max_streak,
        "missed": missed_birds,
    }



@app.exception_handler(AuthlibBaseError)
def handle_authlib_error(error: AuthlibBaseError):
    logger.info(f"error with oauth login: {error}")
    capture_exception(error)
    return JSONResponse(status_code=500, content={"detail": "An error occurred with the login"})
