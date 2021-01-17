# config.py | FastAPI server config
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

import sentry_sdk
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from sentry_sdk.integrations.redis import RedisIntegration
from starlette.middleware.sessions import SessionMiddleware

sentry_sdk.init(
    release=f"{os.getenv('CURRENT_PLATFORM')} Release "
    + (
        f"{os.getenv('GIT_REV', '00000000')[:8]}"
        if os.getenv("CURRENT_PLATFORM") != "Heroku"
        else f"{os.getenv('HEROKU_RELEASE_VERSION')}:{os.getenv('HEROKU_SLUG_DESCRIPTION')}"
    ),
    dsn=os.getenv("SENTRY_API_DSN"),
    integrations=[RedisIntegration()],
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://api.example.com")
DATABASE_SESSION_EXPIRE = 172800  # 2 days

middleware = [
    Middleware(SentryAsgiMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_URL],
        allow_methods=["GET", "POST"],
        allow_credentials=True,
    ),
    Middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET_KEY"),
        same_site="sttrict",
        https_only=True,
    ),
]

app = FastAPI(middleware=middleware)

class NoCacheFileResponse(FileResponse):
    def __init__(self, path, **kwargs):
        kwargs["headers"] = {"Cache-Control": "no-cache"}
        super().__init__(path, **kwargs)
