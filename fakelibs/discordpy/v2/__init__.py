"""
discord.py v2.0 — fake library for blast radius testing.

Reflects the real discord.py 2.0 public API surface.
Names from v1 that are removed here are the breaking changes.
"""

# ── Core client ───────────────────────────────────────────────────────────────

class Client:
    """Main discord client."""
    async def start(self, token): ...          # bot= arg removed
    async def run(self, token): ...
    async def close(self): ...
    # logout REMOVED — use close()
    async def change_presence(self, *, activity=None, status=None): ...  # afk= removed
    # request_offline_members REMOVED
    # fetch_user_profile REMOVED


class AutoShardedClient(Client):
    pass


# ── Bot subclass ───────────────────────────────────────────────────────────────

class Bot(Client):
    def add_cog(self, cog, *, override=False): ...
    def remove_cog(self, name): ...
    def add_command(self, command): ...
    def command(self, *args, **kwargs): ...
    async def setup_hook(self): ...            # NEW in 2.0


# ── Models ─────────────────────────────────────────────────────────────────────

class User:
    name: str
    id: int
    # avatar_url REMOVED — use user.avatar.url
    avatar: object                             # Asset object
    # permissions_in REMOVED

class Member(User):
    pass

class Message:
    content: str
    author: User
    # ack REMOVED

class Guild:
    name: str
    # ack REMOVED

class Thread:                                  # NEW in 2.0
    name: str

class TextChannel:
    name: str
    async def send(self, content=None, **kwargs): ...

class Embed:
    def __init__(self, *, title=None, description=None, colour=None, timestamp=None): ...
    def add_field(self, *, name, value, inline=True): ...

class Webhook:
    pass

class SyncWebhook:                             # NEW — replaces RequestsWebhookAdapter
    pass

# WebhookAdapter REMOVED
# AsyncWebhookAdapter REMOVED
# RequestsWebhookAdapter REMOVED


# ── Exceptions ─────────────────────────────────────────────────────────────────

class DiscordException(Exception): pass
class ClientException(DiscordException): pass
class HTTPException(DiscordException): pass
class Forbidden(HTTPException): pass
class NotFound(HTTPException): pass
# InvalidArgument REMOVED — raises TypeError instead


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


# ── Events ─────────────────────────────────────────────────────────────────────

on_ready = "on_ready"
on_message = "on_message"
on_member_join = "on_member_join"
on_member_update = "on_member_update"
on_presence_update = "on_presence_update"     # NEW — replaces member update for presence
# on_private_channel_create REMOVED
# on_private_channel_delete REMOVED


# ── Utils ──────────────────────────────────────────────────────────────────────

def utils_get(iterable, **attrs): ...
def utils_find(predicate, iterable): ...
def utcnow(): ...                              # NEW helper
