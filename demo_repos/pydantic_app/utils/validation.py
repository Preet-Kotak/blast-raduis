"""Shared validation utilities using pydantic v1."""
from pydantic import validate_arguments, ValidationError

# validate_arguments is removed in pydantic v2 — use validate_call instead


@validate_arguments
def check_unique_email(email: str, existing_users: list) -> None:
    """Raise if email is already taken.
    Uses validate_arguments to enforce type coercion on inputs.
    """
    taken = [u.email for u in existing_users if hasattr(u, 'email')]
    if email in taken:
        raise ValueError(f"Email {email} is already registered")


@validate_arguments
def check_item_name(name: str) -> None:
    """Raise if item name contains forbidden characters."""
    forbidden = ['<', '>', '&', '"']
    if any(c in name for c in forbidden):
        raise ValueError(f"Item name contains forbidden characters: {forbidden}")
