"""Main bot entry point."""
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
