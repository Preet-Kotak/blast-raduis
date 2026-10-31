"""User data model — no external dependencies."""
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str

    def display_name(self) -> str:
        return f"{self.name} <{self.email}>"
