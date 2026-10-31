"""
blast.core.service — Public API for the Streamlit UI.

Exactly seven functions. Each one delegates to the core modules and returns
plain Python dicts/lists. No Streamlit imports here, no business logic.

app.py imports these seven names and calls nothing else in blast/:
    ingest_repo, list_repos, simulate_bump,
    get_affected_files, get_fix_order, get_api_diff, get_bump_history
"""

from blast.core import apidiff, history
from blast.core.bump import get_bump_result
from blast.core.bump import simulate_bump as _simulate_bump
from blast.core.db import ensure_indexes, files_col
from blast.core.ingest import ingest_repo as _ingest_repo
from blast.core.ingest import list_repos as _list_repos


# ── 1. ingest_repo ─────────────────────────────────────────────────────────────

def ingest_repo(path: str) -> str:
    """
    Parse every .py file in `path` and store the import graph in MongoDB.

    Returns:
        repo_id string.
    """
    ensure_indexes()
    return _ingest_repo(path)


# ── 2. list_repos ──────────────────────────────────────────────────────────────

def list_repos() -> list[dict]:
    """
    Return all ingested repos as a list of dicts.

    Each dict has:
        repo_id:    stable hash identifier
        path:       first file path seen (proxy for repo location)
        file_count: number of files ingested
    """
    raw = _list_repos()

    # Enrich with a human-readable path hint from the files collection
    enriched = []
    for r in raw:
        sample = files_col().find_one(
            {"repo_id": r["repo_id"]},
            {"path": 1, "_id": 0}
        )
        enriched.append({
            "repo_id": r["repo_id"],
            "path": sample["path"] if sample else r["repo_id"],
            "file_count": r.get("file_count", 0),
        })
    return enriched


# ── 3. simulate_bump ───────────────────────────────────────────────────────────

def simulate_bump(repo_id: str, dep: str, version: str) -> dict:
    """
    Run a blast radius simulation and save a history record.

    Returns:
        dict with keys: bump_id, repo_id, dep, target_version, is_safe.
    """
    result = _simulate_bump(repo_id, dep, version)

    # Count non-SAFE files for the history record
    affected_count = sum(
        1 for f in result.affected if f["label"] != "SAFE"
    )
    history.save_run(
        repo_id=repo_id,
        dep=dep,
        target_version=version,
        is_safe=result.is_safe,
        affected_count=affected_count,
    )

    return {
        "bump_id": result.bump_id,
        "repo_id": result.repo_id,
        "dep": result.dep,
        "target_version": result.target_version,
        "is_safe": result.is_safe,
    }


# ── 4. get_affected_files ──────────────────────────────────────────────────────

def get_affected_files(bump_id: str) -> list[dict]:
    """
    Return the labelled file list for a completed bump simulation.

    Returns:
        List of dicts: [{"path": str, "label": "DIRECT"|"TRANSITIVE"|"SAFE"}]
    """
    doc = get_bump_result(bump_id)
    if doc is None:
        return []
    return doc.get("affected", [])


# ── 5. get_fix_order ───────────────────────────────────────────────────────────

def get_fix_order(bump_id: str) -> list[str]:
    """
    Return the topological fix order for a completed bump simulation.

    Returns:
        List of file paths, leaves first (safe to fix without breaking others).
    """
    doc = get_bump_result(bump_id)
    if doc is None:
        return []
    return doc.get("fix_order", [])


# ── 6. get_api_diff ────────────────────────────────────────────────────────────

def get_api_diff(dep: str, from_ver: str, to_ver: str) -> list[str]:
    """
    Return names removed between two versions of a dependency.

    Args:
        dep:      Package name (e.g. "fakehttp").
        from_ver: Old version string (e.g. "1.0").
        to_ver:   New version string (e.g. "2.0").

    Returns:
        Sorted list of removed names. Empty if versions are unknown.
    """
    return apidiff.diff_versions(dep, from_ver, to_ver)


# ── 7. get_bump_history ────────────────────────────────────────────────────────

def get_bump_history(repo_id: str, dep: str) -> list[dict]:
    """
    Return past bump runs for a repo + dependency, newest first.

    Returns:
        List of dicts: target_version, is_safe, affected_count, ran_at.
    """
    return history.get_history(repo_id, dep)
