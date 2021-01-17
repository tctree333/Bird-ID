# config.py | Flask server config
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
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    release=f"{os.getenv('CURRENT_PLATFORM')} Release "
    + (
        f"{os.getenv('GIT_REV', '00000000')[:8]}"
        if os.getenv("CURRENT_PLATFORM") != "Heroku"
        else f"{os.getenv('HEROKU_RELEASE_VERSION')}:{os.getenv('HEROKU_SLUG_DESCRIPTION')}"
    ),
    dsn=os.getenv("SENTRY_API_DSN"),
    integrations=[FlaskIntegration(), RedisIntegration()],
)
app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["SESSION_COOKIE_SECURE"] = True
app.secret_key = os.getenv("FLASK_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_SESSION_EXPIRE = 172800  # 2 days


@app.after_request  # enable CORS
def after_request(response):
    header = response.headers
    header["Access-Control-Allow-Origin"] = FRONTEND_URL
    header["Access-Control-Allow-Credentials"] = "true"
    return response
