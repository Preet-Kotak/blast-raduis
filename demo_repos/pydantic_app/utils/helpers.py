"""Generic helper utilities — no pydantic dependency."""
import hashlib
import re


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return re.sub(r'^-+|-+$', '', text)


def hash_password(password: str) -> str:
    """Simple password hashing (demo only — use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def paginate(items: list, page: int = 1, page_size: int = 20) -> dict:
    """Return a paginated slice of items."""
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }
