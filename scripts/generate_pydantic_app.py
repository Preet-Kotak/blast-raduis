"""
Generate a realistic FastAPI + Pydantic v1 app for blast radius testing.

Usage:
    python scripts/generate_pydantic_app.py <output_folder>

The app simulates a real-world API codebase using pydantic v1 patterns
that break in pydantic v2 (validate_arguments, ConstrainedStr, BaseSettings,
validator, parse_raw_as, etc.)

Import graph:
    main          → routes/users, routes/items, config
    routes/users  → models/user, services/user_service
    routes/items  → models/item, services/item_service
    models/user   → pydantic (DIRECT: validator, ConstrainedStr, BaseSettings)
    models/item   → pydantic (DIRECT: ConstrainedStr, ConstrainedInt, validator)
    services/user_service  → models/user, utils/validation
    services/item_service  → models/item, utils/validation
    config        → pydantic (DIRECT: BaseSettings, parse_raw_as)
    utils/validation → pydantic (DIRECT: validate_arguments)
    utils/helpers → (no pydantic — SAFE)
"""

import os
import sys


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def generate(out: str) -> None:
    write(os.path.join(out, "requirements.txt"),
        "fastapi==0.95.0\n"
        "pydantic==1.10.0\n"
        "uvicorn==0.21.0\n"
    )

    # main.py — entry point
    write(os.path.join(out, "main.py"), """\
\"\"\"FastAPI application entry point.\"\"\"
from fastapi import FastAPI
from routes import users, items
from config import Settings

app = FastAPI(title="My API")
settings = Settings()

app.include_router(users.router, prefix="/users")
app.include_router(items.router, prefix="/items")


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.environment}
""")

    # config.py — uses BaseSettings and parse_raw_as
    write(os.path.join(out, "config.py"), """\
\"\"\"Application configuration using pydantic BaseSettings.\"\"\"
from pydantic import BaseSettings, parse_raw_as
from typing import List


class Settings(BaseSettings):
    \"\"\"
    App settings loaded from environment variables.
    BaseSettings is removed from pydantic v2 core —
    moved to pydantic-settings package.
    \"\"\"
    environment: str = "development"
    debug: bool = False
    allowed_hosts: List[str] = ["*"]
    secret_key: str = "dev-secret"
    database_url: str = "sqlite:///./test.db"

    class Config:
        env_file = ".env"


def load_settings_from_json(raw: str) -> Settings:
    \"\"\"Load settings from a raw JSON string.
    parse_raw_as is removed in pydantic v2 — use TypeAdapter instead.
    \"\"\"
    return parse_raw_as(Settings, raw)
""")

    # routes/__init__.py
    write(os.path.join(out, "routes", "__init__.py"), "")

    # routes/users.py
    write(os.path.join(out, "routes", "users.py"), """\
\"\"\"User API routes.\"\"\"
from fastapi import APIRouter, HTTPException
from models.user import UserCreate, UserResponse
from services import user_service

router = APIRouter(tags=["users"])


@router.post("/", response_model=UserResponse)
def create_user(payload: UserCreate):
    return user_service.create(payload)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
""")

    # routes/items.py
    write(os.path.join(out, "routes", "items.py"), """\
\"\"\"Item API routes.\"\"\"
from fastapi import APIRouter
from models.item import ItemCreate, ItemResponse
from services import item_service

router = APIRouter(tags=["items"])


@router.post("/", response_model=ItemResponse)
def create_item(payload: ItemCreate):
    return item_service.create(payload)


@router.get("/")
def list_items():
    return item_service.list_all()
""")

    # models/__init__.py
    write(os.path.join(out, "models", "__init__.py"), "")

    # models/user.py — uses validator, ConstrainedStr
    write(os.path.join(out, "models", "user.py"), """\
\"\"\"User data models using pydantic v1.\"\"\"
from pydantic import BaseModel, validator, ConstrainedStr
from typing import Optional
import re

# ConstrainedStr is removed in pydantic v2 — use Annotated[str, StringConstraints()]
Username = ConstrainedStr(min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
Email = ConstrainedStr(max_length=255)


class UserCreate(BaseModel):
    username: Username
    email: Email
    password: str
    full_name: Optional[str] = None

    # validator decorator is removed in pydantic v2 — use field_validator
    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain an uppercase letter")
        return v

    @validator("email")
    def email_format(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v.lower()


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]

    class Config:
        orm_mode = True
""")

    # models/item.py — uses ConstrainedStr, ConstrainedInt, validator
    write(os.path.join(out, "models", "item.py"), """\
\"\"\"Item data models using pydantic v1.\"\"\"
from pydantic import BaseModel, validator, ConstrainedStr, ConstrainedInt
from typing import Optional

# ConstrainedStr and ConstrainedInt removed in pydantic v2
ItemName = ConstrainedStr(min_length=1, max_length=100)
ItemPrice = ConstrainedInt(ge=0)


class ItemCreate(BaseModel):
    name: ItemName
    price: ItemPrice
    description: Optional[str] = None
    quantity: int = 0

    # validator removed in pydantic v2 — use field_validator
    @validator("quantity")
    def quantity_non_negative(cls, v):
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

    @validator("name")
    def name_stripped(cls, v):
        return v.strip()


class ItemResponse(BaseModel):
    id: int
    name: str
    price: int
    description: Optional[str]
    quantity: int

    class Config:
        orm_mode = True
""")

    # services/__init__.py
    write(os.path.join(out, "services", "__init__.py"), "")

    # services/user_service.py
    write(os.path.join(out, "services", "user_service.py"), """\
\"\"\"User business logic.\"\"\"
from models.user import UserCreate, UserResponse
from utils import validation

_store: dict = {}
_counter = 0


def create(payload: UserCreate) -> UserResponse:
    global _counter
    validation.check_unique_email(payload.email, list(_store.values()))
    _counter += 1
    user = UserResponse(
        id=_counter,
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
    )
    _store[_counter] = user
    return user


def get_by_id(user_id: int) -> UserResponse | None:
    return _store.get(user_id)
""")

    # services/item_service.py
    write(os.path.join(out, "services", "item_service.py"), """\
\"\"\"Item business logic.\"\"\"
from models.item import ItemCreate, ItemResponse
from utils import validation

_store: dict = {}
_counter = 0


def create(payload: ItemCreate) -> ItemResponse:
    global _counter
    validation.check_item_name(payload.name)
    _counter += 1
    item = ItemResponse(
        id=_counter,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        quantity=payload.quantity,
    )
    _store[_counter] = item
    return item


def list_all() -> list:
    return list(_store.values())
""")

    # utils/__init__.py
    write(os.path.join(out, "utils", "__init__.py"), "")

    # utils/validation.py — uses validate_arguments
    write(os.path.join(out, "utils", "validation.py"), """\
\"\"\"Shared validation utilities using pydantic v1.\"\"\"
from pydantic import validate_arguments, ValidationError

# validate_arguments is removed in pydantic v2 — use validate_call instead


@validate_arguments
def check_unique_email(email: str, existing_users: list) -> None:
    \"\"\"Raise if email is already taken.
    Uses validate_arguments to enforce type coercion on inputs.
    \"\"\"
    taken = [u.email for u in existing_users if hasattr(u, 'email')]
    if email in taken:
        raise ValueError(f"Email {email} is already registered")


@validate_arguments
def check_item_name(name: str) -> None:
    \"\"\"Raise if item name contains forbidden characters.\"\"\"
    forbidden = ['<', '>', '&', '"']
    if any(c in name for c in forbidden):
        raise ValueError(f"Item name contains forbidden characters: {forbidden}")
""")

    # utils/helpers.py — SAFE (no pydantic)
    write(os.path.join(out, "utils", "helpers.py"), """\
\"\"\"Generic helper utilities — no pydantic dependency.\"\"\"
import hashlib
import re


def slugify(text: str) -> str:
    \"\"\"Convert text to a URL-friendly slug.\"\"\"
    text = text.lower().strip()
    text = re.sub(r'[^\\w\\s-]', '', text)
    text = re.sub(r'[\\s_-]+', '-', text)
    return re.sub(r'^-+|-+$', '', text)


def hash_password(password: str) -> str:
    \"\"\"Simple password hashing (demo only — use bcrypt in production).\"\"\"
    return hashlib.sha256(password.encode()).hexdigest()


def paginate(items: list, page: int = 1, page_size: int = 20) -> dict:
    \"\"\"Return a paginated slice of items.\"\"\"
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(items),
    }
""")

    print(f"Pydantic v1 app created at: {os.path.abspath(out)}")
    print("Files:")
    for root, _, files in os.walk(out):
        for fname in sorted(files):
            rel = os.path.relpath(os.path.join(root, fname), out)
            print(f"  {rel}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_pydantic_app.py <output_folder>")
        sys.exit(1)
    generate(sys.argv[1])
