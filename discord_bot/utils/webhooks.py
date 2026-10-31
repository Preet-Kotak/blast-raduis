"""Webhook utilities for external notifications."""
import discord
from discord import WebhookAdapter, AsyncWebhookAdapter

WEBHOOK_URL = "https://discord.com/api/webhooks/example"


async def notify_startup(bot):
    """Send a startup notification via webhook."""
    # WebhookAdapter and AsyncWebhookAdapter are removed in discord.py 2.0
    # Use discord.SyncWebhook or discord.Webhook.from_url() instead
    adapter = AsyncWebhookAdapter(bot.http._HTTPClient__session)
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=adapter)
    await webhook.send("Bot is online!")


async def send_alert(message: str):
    """Send an alert webhook message."""
    adapter = WebhookAdapter()
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=adapter)
    await webhook.send(f"ALERT: {message}")
