"""
discord.py v1.7 — fake library for blast radius testing.

Reflects the real discord.py 1.7 public API surface.
Names removed in v2.0 are marked with # REMOVED IN 2.0
"""

# ── Core client ───────────────────────────────────────────────────────────────

class Client:
    """Main discord client."""
    async def start(self, token, *, bot=True): ...          # REMOVED: bot= arg in 2.0
    async def run(self, token, *, bot=True): ...
    async def close(self): ...
    async def logout(self): ...                              # REMOVED IN 2.0 (use close)
    async def change_presence(self, *, activity=None, status=None, afk=False): ...  # REMOVED: afk= in 2.0
    async def request_offline_members(self, *guilds): ...   # REMOVED IN 2.0
    async def fetch_user_profile(self, user_id): ...        # REMOVED IN 2.0


class AutoShardedClient(Client):
    """Automatically sharded client."""
    pass


# ── Bot subclass ───────────────────────────────────────────────────────────────

class Bot(Client):
    """Commands bot."""
    def add_cog(self, cog): ...
    def remove_cog(self, name): ...
    def add_command(self, command): ...
    def command(self, *args, **kwargs): ...


# ── Models ─────────────────────────────────────────────────────────────────────

class User:
    """Represents a Discord user."""
    name: str
    id: int
    avatar_url: str                                          # REMOVED IN 2.0 (use avatar.url)
    async def permissions_in(self, channel): ...            # REMOVED IN 2.0

class Member(User):
    """Represents a guild member."""
    pass

class Message:
    """Represents a Discord message."""
    content: str
    author: User
    async def ack(self): ...                                # REMOVED IN 2.0

class Guild:
    """Represents a Discord guild/server."""
    name: str
    async def ack(self): ...                                # REMOVED IN 2.0

class TextChannel:
    """Represents a text channel."""
    name: str
    async def send(self, content=None, **kwargs): ...

class Embed:
    """Represents a Discord embed."""
    def __init__(self, *, title=None, description=None, colour=None, timestamp=None): ...
    def add_field(self, *, name, value, inline=True): ...

class Webhook:
    """Represents a webhook."""
    pass

class WebhookAdapter:                                        # REMOVED IN 2.0
    """Adapter for webhooks — removed in v2."""
    pass

class AsyncWebhookAdapter(WebhookAdapter):                  # REMOVED IN 2.0
    pass

class RequestsWebhookAdapter(WebhookAdapter):               # REMOVED IN 2.0
    pass


# ── Exceptions ─────────────────────────────────────────────────────────────────

class DiscordException(Exception): pass
class ClientException(DiscordException): pass
class HTTPException(DiscordException): pass
class Forbidden(HTTPException): pass
class NotFound(HTTPException): pass
class InvalidArgument(ClientException): pass                # REMOVED IN 2.0


# ── Enums / flags ──────────────────────────────────────────────────────────────

class Status:
    online = "online"
    offline = "offline"
    idle = "idle"
    dnd = "dnd"

class ActivityType:
    playing = 0
    streaming = 1
    listening = 2
    watching = 3

class Intents:
    @classmethod
    def all(cls): ...
    @classmethod
    def default(cls): ...


# ── Events (as constants for detection) ────────────────────────────────────────

on_ready = "on_ready"
on_message = "on_message"
on_member_join = "on_member_join"
on_private_channel_create = "on_private_channel_create"     # REMOVED IN 2.0
on_private_channel_delete = "on_private_channel_delete"     # REMOVED IN 2.0
on_member_update = "on_member_update"                        # CHANGED (presence split off)


# ── Utils ──────────────────────────────────────────────────────────────────────

def utils_get(iterable, **attrs): ...
def utils_find(predicate, iterable): ...
