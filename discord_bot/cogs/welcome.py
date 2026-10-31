"""Welcome new members with an embed."""
import discord
from discord.ext import commands
from utils import helpers


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send a welcome embed when a member joins."""
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
        """Show a member's profile card."""
        member = member or ctx.author
        embed = discord.Embed(title=member.display_name)
        # avatar_url removed in 2.0
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)
