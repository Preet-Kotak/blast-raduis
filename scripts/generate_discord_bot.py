"""
Generate a realistic Discord bot repo for blast radius testing.

Usage:
    python scripts/generate_discord_bot.py <output_folder>

Example:
    python scripts/generate_discord_bot.py discord_bot

The bot has this structure:
    bot.py              — entry point, creates Client, calls logout on shutdown
    cogs/
        moderation.py   — ban/kick commands, uses InvalidArgument
        welcome.py      — greets new members, uses avatar_url
        presence.py     — handles on_member_update, uses permissions_in
    utils/
        webhooks.py     — sends webhook alerts, uses WebhookAdapter
        helpers.py      — shared utilities, no direct discord usage

Import graph:
    bot               → discord (DIRECT: logout, request_offline_members)
    cogs/moderation   → discord (DIRECT: InvalidArgument)
    cogs/welcome      → discord (DIRECT: avatar_url usage pattern)
    cogs/presence     → discord (DIRECT: on_private_channel_create, permissions_in)
    utils/webhooks    → discord (DIRECT: WebhookAdapter, AsyncWebhookAdapter)
    utils/helpers     → (no discord — SAFE)
    bot               → cogs/moderation, cogs/welcome, cogs/presence, utils/webhooks
"""

import os
import sys


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate(out: str) -> None:
    # requirements.txt — pinned to discord.py 1.7
    write(os.path.join(out, "requirements.txt"),
        "discord.py==1.7.3\n"
        "python-dotenv==0.21.0\n"
    )

    # bot.py — entry point
    write(os.path.join(out, "bot.py"), """\
\"\"\"Main bot entry point.\"\"\"
import discord
from discord.ext import commands
from cogs import moderation, welcome, presence
from utils import webhooks

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await webhooks.notify_startup(bot)


@bot.event
async def on_member_update(before, after):
    # Handles presence updates — this event is split in discord.py 2.0
    await presence.handle_member_update(before, after)


async def shutdown():
    # Uses Client.logout — removed in discord.py 2.0, use close() instead
    await bot.logout()


async def setup():
    await bot.add_cog(moderation.ModerationCog(bot))
    await bot.add_cog(welcome.WelcomeCog(bot))
    await bot.add_cog(presence.PresenceCog(bot))
    # Also fetch offline members on startup (removed in 2.0)
    await bot.request_offline_members(*bot.guilds)


bot.run("TOKEN")
""")

    # cogs/__init__.py
    write(os.path.join(out, "cogs", "__init__.py"), "")

    # cogs/moderation.py — uses InvalidArgument
    write(os.path.join(out, "cogs", "moderation.py"), """\
\"\"\"Moderation commands: ban, kick, mute.\"\"\"
import discord
from discord.ext import commands
from utils import helpers


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        \"\"\"Ban a member from the server.\"\"\"
        if member == ctx.author:
            # InvalidArgument is removed in discord.py 2.0 — becomes TypeError
            raise discord.InvalidArgument("You cannot ban yourself.")
        await member.ban(reason=reason)
        await ctx.send(helpers.format_action("ban", member, reason))

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        \"\"\"Kick a member from the server.\"\"\"
        if not member:
            raise discord.InvalidArgument("Please specify a member to kick.")
        await member.kick(reason=reason)
        await ctx.send(helpers.format_action("kick", member, reason))

    @commands.command()
    async def mute(self, ctx, member: discord.Member):
        \"\"\"Mute a member in the current channel.\"\"\"
        overwrite = discord.PermissionOverwrite(send_messages=False)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send(f"Muted {member.display_name}.")
""")

    # cogs/welcome.py — uses avatar_url
    write(os.path.join(out, "cogs", "welcome.py"), """\
\"\"\"Welcome new members with an embed.\"\"\"
import discord
from discord.ext import commands
from utils import helpers


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        \"\"\"Send a welcome embed when a member joins.\"\"\"
        channel = helpers.get_welcome_channel(member.guild)
        if channel is None:
            return

        embed = discord.Embed(
            title=f"Welcome, {member.display_name}!",
            description=f"You are member #{member.guild.member_count}.",
            colour=discord.Colour.green(),
        )
        # avatar_url is removed in discord.py 2.0 — use member.avatar.url
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        \"\"\"Show a member's profile card.\"\"\"
        member = member or ctx.author
        embed = discord.Embed(title=member.display_name)
        # avatar_url removed in 2.0
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)
""")

    # cogs/presence.py — uses permissions_in and on_private_channel_create
    write(os.path.join(out, "cogs", "presence.py"), """\
\"\"\"Presence and permission tracking.\"\"\"
import discord
from discord.ext import commands
from utils import helpers


class PresenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_private_channel_create(self, channel):
        \"\"\"Fired when a private channel is created — removed in discord.py 2.0.\"\"\"
        print(f"Private channel created: {channel}")

    @commands.Cog.listener()
    async def on_private_channel_delete(self, channel):
        \"\"\"Fired when a private channel is deleted — removed in discord.py 2.0.\"\"\"
        print(f"Private channel deleted: {channel}")

    @commands.command()
    async def perms(self, ctx, member: discord.Member = None):
        \"\"\"Show a member's permissions in this channel.\"\"\"
        member = member or ctx.author
        # permissions_in is removed in discord.py 2.0
        # use channel.permissions_for(member) instead
        perms = member.permissions_in(ctx.channel)
        await ctx.send(helpers.format_permissions(perms))


async def handle_member_update(before, after):
    \"\"\"Called from bot.py on_member_update.\"\"\"
    if before.status != after.status:
        print(f"{after.display_name} changed status: {before.status} -> {after.status}")
""")

    # utils/__init__.py
    write(os.path.join(out, "utils", "__init__.py"), "")

    # utils/webhooks.py — uses WebhookAdapter, AsyncWebhookAdapter
    write(os.path.join(out, "utils", "webhooks.py"), """\
\"\"\"Webhook utilities for external notifications.\"\"\"
import discord
from discord import WebhookAdapter, AsyncWebhookAdapter

WEBHOOK_URL = "https://discord.com/api/webhooks/example"


async def notify_startup(bot):
    \"\"\"Send a startup notification via webhook.\"\"\"
    # WebhookAdapter and AsyncWebhookAdapter are removed in discord.py 2.0
    # Use discord.SyncWebhook or discord.Webhook.from_url() instead
    adapter = AsyncWebhookAdapter(bot.http._HTTPClient__session)
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=adapter)
    await webhook.send("Bot is online!")


async def send_alert(message: str):
    \"\"\"Send an alert webhook message.\"\"\"
    adapter = WebhookAdapter()
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=adapter)
    await webhook.send(f"ALERT: {message}")
""")

    # utils/helpers.py — no direct discord usage (SAFE)
    write(os.path.join(out, "utils", "helpers.py"), """\
\"\"\"Shared helper utilities — no direct discord.py dependency.\"\"\"


def format_action(action: str, member, reason: str = None) -> str:
    \"\"\"Format a moderation action message.\"\"\"
    msg = f"{action.capitalize()}ned {member.display_name}"
    if reason:
        msg += f" for: {reason}"
    return msg


def format_permissions(perms) -> str:
    \"\"\"Format a permissions object into a readable string.\"\"\"
    active = [name for name, value in perms if value]
    return "Permissions: " + ", ".join(active) if active else "No permissions."


def get_welcome_channel(guild):
    \"\"\"Find the welcome channel in a guild by name.\"\"\"
    return next(
        (ch for ch in guild.text_channels if ch.name == "welcome"),
        None
    )
""")

    print(f"Discord bot repo created at: {os.path.abspath(out)}")
    print("Files:")
    for root, _, files in os.walk(out):
        for fname in sorted(files):
            rel = os.path.relpath(os.path.join(root, fname), out)
            print(f"  {rel}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_discord_bot.py <output_folder>")
        sys.exit(1)
    generate(sys.argv[1])
