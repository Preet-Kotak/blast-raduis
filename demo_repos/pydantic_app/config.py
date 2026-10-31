"""Application configuration using pydantic BaseSettings."""
from pydantic import BaseSettings, parse_raw_as
from typing import List


class Settings(BaseSettings):
    """
    App settings loaded from environment variables.
    BaseSettings is removed from pydantic v2 core —
    moved to pydantic-settings package.
    """
    environment: str = "development"
    debug: bool = False
    allowed_hosts: List[str] = ["*"]
    secret_key: str = "dev-secret"
    database_url: str = "sqlite:///./test.db"

    class Config:
        env_file = ".env"


def load_settings_from_json(raw: str) -> Settings:
    """Load settings from a raw JSON string.
    parse_raw_as is removed in pydantic v2 — use TypeAdapter instead.
    """
    return parse_raw_as(Settings, raw)
