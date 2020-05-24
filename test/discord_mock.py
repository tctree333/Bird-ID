import random

import pytest

from bot.data import database


class Bot:
    def __init__(self, guilds=[]):
        self.guilds = guilds


class Channel:
    def __init__(self, channel_id=None):
        self.id = channel_id


class User:
    def __init__(self, user_id=None, username=None):
        self.id = user_id
        self.roles = []

class Member(User):
    def __init__(self, guild=None, nick=None, user_id=None, username=None):
        super().__init__(user_id, username)
        self.guild = guild
        self.nick = nick

class Guild:
    def __init__(self, guild_id=None):
        self.id = guild_id
        self.members = []

    def add_member(self, nick):
        self.members.append(Member(self, nick+"_MEMBER", random.randint(999999999999990000, 999999999999999999), nick))



class Message:
    def __init__(
        self,
        content=None,
        tts=False,
        embed=None,
        file=None,
        files=None,
        delete_after=None,
        nonce=None,
    ):
        self.content = content
        self.tts = tts
        self.embed = embed
        self.file = file
        self.files = files
        self.delete_after = delete_after
        self.nonce = nonce

    def __repr__(self):
        return str(
            {
                "content": self.content,
                "tts": self.tts,
                "embed": self.embed,
                "file": self.file,
                "files": self.files,
                "delete_after": self.delete_after,
                "nonce": self.nonce,
            }
        )

    async def delete(self):
        return

class Context:
    def __init__(self, bot=None):
        self.guild = None
        self.channel = Channel(random.randint(999999999999990000, 999999999999999999))
        self.author = User(random.randint(999999999999990000, 999999999999999999), "MOCK USER")
        self.last_message = Message()
        self.messages = []
        self.bot = bot

    def set_guild(self):
        self.guild = Guild(random.randint(999999999999990000, 999999999999999999))
        self.bot.guilds.append(self.guild)

    async def send(
        self,
        content=None,
        *,
        tts=False,
        embed=None,
        file=None,
        files=None,
        delete_after=None,
        nonce=None,
    ):
        message = Message(content, tts, embed, file, files, delete_after, nonce)
        self.last_message = message
        self.messages.append(message)

        return message

    async def trigger_typing(self):
        return
