"""
Generate a self-contained fake Python repo for testing Blast Radius.

Usage:
    python scripts/generate_sample_repo.py <output_folder>

Example:
    python scripts/generate_sample_repo.py sample_repo

The generated repo has this import graph:
    main          → api.client
    api.client    → fakehttp          (DIRECT dep)
    api.auth      → api.client
    utils.retry   → fakehttp          (DIRECT dep)
    models.user   → (none)

Expected blast radius when bumping fakehttp to 2.0:
    DIRECT:     api/client.py, utils/retry.py
    TRANSITIVE: main.py, api/auth.py
    SAFE:       models/user.py
"""

import os
import sys


def write(path: str, content: str) -> None:
    """Write content to path, creating parent directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def generate(output_dir: str) -> None:
    """Create the fake repo tree under output_dir."""

    # requirements.txt — pins fakehttp at 1.0
    write(
        os.path.join(output_dir, "requirements.txt"),
        "fakehttp==1.0\n",
    )

    # main.py — entry point, imports api.client
    write(
        os.path.join(output_dir, "main.py"),
        """\
\"\"\"Entry point for the sample app.\"\"\"
from api import client


def run():
    response = client.fetch_data()
    print(response)


if __name__ == "__main__":
    run()
""",
    )

    # api/__init__.py
    write(os.path.join(output_dir, "api", "__init__.py"), "")

    # api/client.py — imports fakehttp directly (DIRECT)
    write(
        os.path.join(output_dir, "api", "client.py"),
        """\
\"\"\"HTTP client wrapper around fakehttp.\"\"\"
import fakehttp


def fetch_data(url: str = "http://example.com") -> dict:
    return fakehttp.get(url)


def create_session() -> fakehttp.Session:
    return fakehttp.Session()
""",
    )

    # api/auth.py — imports api.client (TRANSITIVE via client → fakehttp)
    write(
        os.path.join(output_dir, "api", "auth.py"),
        """\
\"\"\"Authentication helpers that use the HTTP client.\"\"\"
from api import client


def authenticate(token: str) -> bool:
    response = client.fetch_data(f"http://auth.example.com/verify?token={token}")
    return response.get("status") == 200
""",
    )

    # models/__init__.py
    write(os.path.join(output_dir, "models", "__init__.py"), "")

    # models/user.py — no external deps (SAFE)
    write(
        os.path.join(output_dir, "models", "user.py"),
        """\
\"\"\"User data model — no external dependencies.\"\"\"
from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    email: str

    def display_name(self) -> str:
        return f"{self.name} <{self.email}>"
""",
    )

    # utils/__init__.py
    write(os.path.join(output_dir, "utils", "__init__.py"), "")

    # utils/retry.py — imports fakehttp directly (DIRECT)
    write(
        os.path.join(output_dir, "utils", "retry.py"),
        """\
\"\"\"Retry wrapper that catches fakehttp.HTTPError.\"\"\"
import fakehttp


def get_with_retry(url: str, retries: int = 3) -> dict:
    \"\"\"Retry a GET request up to `retries` times on HTTPError.\"\"\"
    for attempt in range(retries):
        try:
            return fakehttp.get(url)
        except fakehttp.HTTPError as exc:
            if attempt == retries - 1:
                raise
            print(f"Retry {attempt + 1} after error: {exc}")
""",
    )

    print(f"Sample repo created at: {os.path.abspath(output_dir)}")
    print("Files generated:")
    for root, _, files in os.walk(output_dir):
        for fname in sorted(files):
            rel = os.path.relpath(os.path.join(root, fname), output_dir)
            print(f"  {rel}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_sample_repo.py <output_folder>")
        sys.exit(1)
    generate(sys.argv[1])
