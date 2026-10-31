"""Presence and permission tracking."""
import discord
from discord.ext import commands
from utils import helpers


class PresenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_private_channel_create(self, channel):
        """Fired when a private channel is created — removed in discord.py 2.0."""
        print(f"Private channel created: {channel}")

    @commands.Cog.listener()
    async def on_private_channel_delete(self, channel):
        """Fired when a private channel is deleted — removed in discord.py 2.0."""
        print(f"Private channel deleted: {channel}")

    @commands.command()
    async def perms(self, ctx, member: discord.Member = None):
        """Show a member's permissions in this channel."""
        member = member or ctx.author
        # permissions_in is removed in discord.py 2.0
        # use channel.permissions_for(member) instead
        perms = member.permissions_in(ctx.channel)
        await ctx.send(helpers.format_permissions(perms))


async def handle_member_update(before, after):
    """Called from bot.py on_member_update."""
    if before.status != after.status:
        print(f"{after.display_name} changed status: {before.status} -> {after.status}")
