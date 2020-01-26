import random
class Channel:
    def __init__(self, channel_id=None):
        self.id = channel_id


class Author:
    def __init__(self, user_id=None):
        self.id = user_id
        self.roles = []


class Guild:
    def __init__(self, guild_id=None):
        self.id = guild_id


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
    def __init__(self):
        self.guild = None
        self.channel = Channel(random.randint(999999999999990000, 999999999999999999))
        self.author = Author(random.randint(999999999999990000, 999999999999999999))
        self.last_message = Message()
        self.messages = []

    def set_guild(self):
        self.guild = Guild(random.randint(999999999999990000, 999999999999999999))

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


class Bot:
    def __init__(self):
        pass
