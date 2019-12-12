import random
import os
import flask
import authlib

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, request, url_for, render_template, redirect, session, abort
from web.data import app, database, logger, update_web_user, get_session_id
from functions import cleanup

bp = Blueprint('user', __name__, url_prefix='/user')
oauth = OAuth(app)

DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
oauth.register(
    name='discord',
    client_id=601917808137338900,
    client_secret=DISCORD_CLIENT_SECRET,
    access_token_url='https://discordapp.com/api/oauth2/token',
    access_token_params=None,
    authorize_url='https://discordapp.com/api/oauth2/authorize',
    authorize_params=None,
    api_base_url='https://discordapp.com/api/',
    client_kwargs={'scope': 'identify', 'prompt': 'consent'},
)
discord = oauth.discord


@bp.route('/login')
def login():
    logger.info("endpoint: login")

    redirect_uri = url_for('user.authorize', _external=True)
    return oauth.discord.authorize_redirect(redirect_uri)


@bp.route('/authorize')
def authorize():
    logger.info("endpoint: authorize")

    token = oauth.discord.authorize_access_token()
    resp = oauth.discord.get('users/@me')
    profile = resp.json()
    # do something with the token and profile
    update_web_user(profile)
    avatar_hash, avatar_url, username, discriminator = map(cleanup, database.hmget(f"web.user:{str(profile['id'])}",
                                                                                   "avatar_hash", "avatar_url", "username", "discriminator"))
    return f"Successfully logged in as {flask.escape(username)}"

@bp.route('/profile')
def profile():
    logger.info("endpoint: profile")

    session_id = get_session_id()
    user_id = int(database.hget(f"web.session:{session_id}", "user_id"))

    if user_id is not 0:
        avatar_hash, avatar_url, username, discriminator = map(cleanup, database.hmget(f"web.user:{str(user_id)}",
                                                                                    "avatar_hash", "avatar_url", "username", "discriminator"))
        return {"avatar_hash": avatar_hash, "avatar_url": avatar_url, "username": username, "discriminator": discriminator}
    else:
        logger.info("not logged in")
        abort(403, "Sign in to continue")


@app.errorhandler(authlib.common.errors.AuthlibBaseError)
def handle_authlib_error(e):
    logger.error(f"error with oauth login: {e}")
    return 'An error occurred with the login', 500