"""
blast.core.db — MongoDB connection singleton and collection helpers.

Reads MONGO_URI from Streamlit secrets or the environment.
Raises ConnectionError if no URI is configured so callers can fall back
to demo mode cleanly.

Collections:
  files    — parsed file nodes (path, deps, local imports)
  edges    — directed import edges (from → to)
  bumps    — blast-radius simulation results
  history  — lightweight record of every bump run
"""

import os
from functools import lru_cache

from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure


# ── URI resolution ─────────────────────────────────────────────────────────────

def _get_uri() -> str:
    """
    Return the MongoDB URI from Streamlit secrets or the MONGO_URI env var.
    Raises ConnectionError if neither is set.
    """
    # Try Streamlit secrets first (works when running via `streamlit run`)
    try:
        import streamlit as st
        uri = st.secrets.get("MONGO_URI", "")
        if uri:
            return uri
    except Exception:
        pass

    # Fall back to environment variable (useful in tests / CLI)
    uri = os.environ.get("MONGO_URI", "")
    if uri:
        return uri

    raise ConnectionError(
        "MONGO_URI is not set. Add it to .streamlit/secrets.toml or set the "
        "MONGO_URI environment variable."
    )


# ── Client singleton ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _client() -> MongoClient:
    """
    Return a cached MongoClient. The connection is validated on first call.
    Raises ConnectionError if the server is unreachable.
    """
    uri = _get_uri()
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Trigger a real connection attempt so we fail fast
    try:
        client.admin.command("ping")
    except ConnectionFailure as exc:
        raise ConnectionError(f"Cannot reach MongoDB: {exc}") from exc
    return client


def _db():
    """Return the blast_radius database handle."""
    return _client()["blast_radius"]


# ── Collection helpers ─────────────────────────────────────────────────────────

def files_col() -> Collection:
    """Collection that stores parsed file nodes."""
    return _db()["files"]


def edges_col() -> Collection:
    """Collection that stores directed import edges."""
    return _db()["edges"]


def bumps_col() -> Collection:
    """Collection that stores blast-radius simulation results."""
    return _db()["bumps"]


def history_col() -> Collection:
    """Collection that stores lightweight bump run history."""
    return _db()["history"]


# ── Index creation ─────────────────────────────────────────────────────────────

def ensure_indexes() -> None:
    """
    Create indexes required for efficient graph queries.
    Safe to call multiple times — MongoDB ignores duplicate index requests.
    """
    # files: look up all files belonging to a repo
    files_col().create_index([("repo_id", ASCENDING)], background=True)

    # edges: look up all outgoing edges from a file within a repo
    edges_col().create_index(
        [("repo_id", ASCENDING), ("from", ASCENDING)], background=True
    )
    # edges: also needed for $graphLookup connectToField
    edges_col().create_index([("to", ASCENDING)], background=True)

    # history: look up run history for a repo + dependency pair
    history_col().create_index(
        [("repo_id", ASCENDING), ("dep", ASCENDING), ("ran_at", ASCENDING)],
        background=True,
    )
