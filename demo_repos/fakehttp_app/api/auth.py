"""Authentication helpers that use the HTTP client."""
from api import client


def authenticate(token: str) -> bool:
    response = client.fetch_data(f"http://auth.example.com/verify?token={token}")
    return response.get("status") == 200
