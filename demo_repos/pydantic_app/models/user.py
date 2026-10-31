"""User data models using pydantic v1."""
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
