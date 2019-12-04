import random
import os
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, request, url_for, render_template, redirect, session
from web.data import app, database, update_web_user, get_session_id
from functions import cleanup

bp = Blueprint('auth', __name__, url_prefix='/auth')
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
    redirect_uri = url_for('auth.authorize', _external=True)
    return oauth.discord.authorize_redirect(redirect_uri)


@bp.route('/authorize')
def authorize():
    token = oauth.discord.authorize_access_token()
    resp = oauth.discord.get('users/@me')
    profile = resp.json()
    # do something with the token and profile
    session_id = get_session_id()
    update_web_user(profile)
    database.hset(f"web.session:{session_id}", "user_id", str(profile["id"]))
    avatar_hash, avatar_url, username, discriminator = map(cleanup, database.hmget(f"web.user:{str(profile['id'])}",
                                                                      "avatar_hash", "avatar_url", "username", "discriminator"))
    return {"avatar_hash": avatar_hash, "avatar_url": avatar_url, "username": username, "discriminator": discriminator}
