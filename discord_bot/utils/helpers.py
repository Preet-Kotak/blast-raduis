"""Shared helper utilities — no direct discord.py dependency."""


def format_action(action: str, member, reason: str = None) -> str:
    """Format a moderation action message."""
    msg = f"{action.capitalize()}ned {member.display_name}"
    if reason:
        msg += f" for: {reason}"
    return msg


def format_permissions(perms) -> str:
    """Format a permissions object into a readable string."""
    active = [name for name, value in perms if value]
    return "Permissions: " + ", ".join(active) if active else "No permissions."


def get_welcome_channel(guild):
    """Find the welcome channel in a guild by name."""
    return next(
        (ch for ch in guild.text_channels if ch.name == "welcome"),
        None
    )
