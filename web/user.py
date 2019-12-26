import random
import os
import re
import flask
import authlib

from sentry_sdk import capture_exception
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, request, url_for, render_template, redirect, session, abort
from web.data import app, database, logger, update_web_user, get_session_id, verify_session, FRONTEND_URL
from functions import cleanup

bp = Blueprint('user', __name__, url_prefix='/user')
oauth = OAuth(app)

url_regex = f"{re.escape(FRONTEND_URL)}/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))*"
regex = re.compile(url_regex)

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

@bp.after_request # enable CORS
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = FRONTEND_URL
    header['Access-Control-Allow-Credentials'] = 'true'
    return response

@bp.route('/login', methods=["GET"])
def login():
    logger.info("endpoint: login")
    redirect_after = request.args.get("redirect", FRONTEND_URL, str)
    if regex.fullmatch(redirect_after) is not None:
        session["redirect"] = redirect_after
    else:
        session["redirect"] = FRONTEND_URL
    redirect_uri = url_for('user.authorize', _external=True)
    return oauth.discord.authorize_redirect(redirect_uri)

@bp.route('/logout', methods=["GET"])
def logout():
    logger.info("endpoint: logout")
    redirect_after = request.args.get("redirect", FRONTEND_URL, str)
    if regex.fullmatch(redirect_after) is not None:
        redirect_url = redirect_after
    else:
        redirect_url = FRONTEND_URL

    session_id = get_session_id()
    user_id = verify_session(session_id)
    if type(user_id) is int:
        logger.info("deleting user data, session data")
        database.delete(f"web.user:{user_id}", f"web.session:{session_id}")
        session.clear()
    else:
        logger.info("deleting session data")
        database.delete(f"web.session:{session_id}")
        session.clear()
    return redirect(redirect_url)

@bp.route('/authorize')
def authorize():
    logger.info("endpoint: authorize")
    redirect_uri = session["redirect"]
    session.pop("redirect", None)

    token = oauth.discord.authorize_access_token()
    resp = oauth.discord.get('users/@me')
    profile = resp.json()
    # do something with the token and profile
    update_web_user(profile)
    avatar_hash, avatar_url, username, discriminator = map(cleanup, database.hmget(f"web.user:{str(profile['id'])}",
                                                                                   "avatar_hash", "avatar_url", "username", "discriminator"))
    return redirect(redirect_uri)

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
    logger.info(f"error with oauth login: {e}")
    capture_exception(e)
    return 'An error occurred with the login', 500