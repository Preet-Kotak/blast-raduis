"""
blast.core.history — Persist and retrieve bump run history.

Every time simulate_bump is called, the result is saved here so the UI
can warn "last time you tried this it was also unsafe."
"""

from datetime import datetime, timezone

from blast.core.db import history_col


def save_run(
    repo_id: str,
    dep: str,
    target_version: str,
    is_safe: bool,
    affected_count: int,
) -> None:
    """
    Persist a lightweight record of a bump simulation run.

    Args:
        repo_id:        Repo identifier.
        dep:            Dependency name (e.g. "fakehttp").
        target_version: Version bumped to.
        is_safe:        Whether the bump was safe.
        affected_count: Number of non-SAFE files affected.
    """
    history_col().insert_one({
        "repo_id": repo_id,
        "dep": dep,
        "target_version": target_version,
        "is_safe": is_safe,
        "affected_count": affected_count,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    })


def get_history(repo_id: str, dep: str) -> list[dict]:
    """
    Return all bump runs for a repo + dependency, newest first.

    Args:
        repo_id: Repo identifier.
        dep:     Dependency name.

    Returns:
        List of history dicts with keys:
        target_version, is_safe, affected_count, ran_at.
    """
    cursor = history_col().find(
        {"repo_id": repo_id, "dep": dep},
        {"_id": 0, "target_version": 1, "is_safe": 1, "affected_count": 1, "ran_at": 1},
    ).sort("ran_at", -1)
    return list(cursor)


def last_run_was_unsafe(repo_id: str, dep: str) -> bool:
    """
    Return True if the most recent bump run for this repo + dep was unsafe.

    Args:
        repo_id: Repo identifier.
        dep:     Dependency name.
    """
    history = get_history(repo_id, dep)
    if not history:
        return False
    return not history[0]["is_safe"]
