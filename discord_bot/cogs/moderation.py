"""Moderation commands: ban, kick, mute."""
import discord
from discord.ext import commands
from utils import helpers


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the server."""
        if member == ctx.author:
            # InvalidArgument is removed in discord.py 2.0 — becomes TypeError
            raise discord.InvalidArgument("You cannot ban yourself.")
        await member.ban(reason=reason)
        await ctx.send(helpers.format_action("ban", member, reason))

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a member from the server."""
        if not member:
            raise discord.InvalidArgument("Please specify a member to kick.")
        await member.kick(reason=reason)
        await ctx.send(helpers.format_action("kick", member, reason))

    @commands.command()
    async def mute(self, ctx, member: discord.Member):
        """Mute a member in the current channel."""
        overwrite = discord.PermissionOverwrite(send_messages=False)
        await ctx.channel.set_permissions(member, overwrite=overwrite)
        await ctx.send(f"Muted {member.display_name}.")
