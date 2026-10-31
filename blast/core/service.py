"""
blast.core.service — Public API for the Streamlit UI.

Exactly seven functions. Each one delegates to the core modules and returns
plain Python dicts/lists. No Streamlit imports here, no business logic.

app.py imports these seven names and calls nothing else in blast/:
    ingest_repo, list_repos, simulate_bump,
    get_affected_files, get_fix_order, get_api_diff, get_bump_history
"""

from blast.core import history
from blast.core import pypi_diff
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
        path:       absolute root path of the repo
        file_count: number of files ingested
    """
    raw = _list_repos()

    enriched = []
    for r in raw:
        # Use stored repo_root; fall back to relative path of first file
        sample = files_col().find_one(
            {"repo_id": r["repo_id"]},
            {"repo_root": 1, "path": 1, "_id": 0}
        )
        if sample and sample.get("repo_root"):
            display_path = sample["repo_root"]
        elif sample:
            # Old data without repo_root — show parent of first file as hint
            import os
            display_path = os.path.dirname(sample["path"]) or sample["path"]
        else:
            display_path = r["repo_id"]

        enriched.append({
            "repo_id": r["repo_id"],
            "path": display_path,
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
    Fetches real package data from PyPI; falls back to fakelibs.

    Args:
        dep:      Package name as on PyPI (e.g. "discord.py", "requests").
        from_ver: Old version string (e.g. "1.7.3").
        to_ver:   New version string (e.g. "2.0.0").

    Returns:
        Sorted list of removed names.
    """
    return pypi_diff.diff_versions(dep, from_ver, to_ver)


# ── 7. get_bump_history ────────────────────────────────────────────────────────

def get_bump_history(repo_id: str, dep: str) -> list[dict]:
    """
    Return past bump runs for a repo + dependency, newest first.

    Returns:
        List of dicts: target_version, is_safe, affected_count, ran_at.
    """
    return history.get_history(repo_id, dep)


# ── bonus: version discovery ───────────────────────────────────────────────────

def get_package_versions(dep: str) -> list[str]:
    """
    Return available versions for a package from PyPI, newest first.

    Args:
        dep: Package name as on PyPI.

    Returns:
        List of version strings, empty if package not found.
    """
    return pypi_diff.get_package_versions(dep)


# ── bonus: requirements dashboard ─────────────────────────────────────────────

def scan_requirements(repo_id: str, repo_path: str) -> list[dict]:
    """
    Read requirements.txt from repo_path, find latest stable version of each
    dep on PyPI, run blast radius for each one, and return a risk summary.

    Args:
        repo_id:   Repo identifier from ingest_repo().
        repo_path: Absolute path to the repo root (to find requirements.txt).

    Returns:
        List of dicts sorted by risk (HIGH first):
        [
          {
            "dep":          "pydantic",
            "current_ver":  "1.10.0",
            "latest_ver":   "2.14.2",
            "is_latest":    False,
            "affected":     9,
            "direct":       4,
            "transitive":   5,
            "risk":         "HIGH",   # HIGH / MEDIUM / SAFE
            "bump_id":      "abc123",
          }
        ]
    """
    import os
    from blast.core.ingest import _read_requirements
    from blast.core.pypi_diff import get_package_versions

    req_path = os.path.join(repo_path, "requirements.txt")
    if not os.path.exists(req_path):
        return []

    pinned = _read_requirements(repo_path)
    results = []

    for dep, current_ver in pinned.items():
        versions = get_package_versions(dep)
        if not versions:
            # Not on PyPI or network unavailable
            results.append({
                "dep": dep, "current_ver": current_ver,
                "latest_ver": "unknown", "is_latest": False,
                "affected": 0, "direct": 0, "transitive": 0,
                "risk": "UNKNOWN", "bump_id": None,
            })
            continue

        latest_ver = versions[0]
        is_latest  = current_ver == latest_ver

        if is_latest:
            results.append({
                "dep": dep, "current_ver": current_ver,
                "latest_ver": latest_ver, "is_latest": True,
                "affected": 0, "direct": 0, "transitive": 0,
                "risk": "UP TO DATE", "bump_id": None,
            })
            continue

        # Run blast radius to latest
        try:
            bump   = simulate_bump(repo_id, dep, latest_ver)
            aff    = get_affected_files(bump["bump_id"])
            direct = sum(1 for f in aff if f["label"] == "DIRECT")
            trans  = sum(1 for f in aff if f["label"] == "TRANSITIVE")
            total  = direct + trans

            if total == 0:
                risk = "SAFE"
            elif direct >= 3 or total >= 6:
                risk = "HIGH"
            elif direct >= 1:
                risk = "MEDIUM"
            else:
                risk = "LOW"

            results.append({
                "dep": dep, "current_ver": current_ver,
                "latest_ver": latest_ver, "is_latest": False,
                "affected": total, "direct": direct,
                "transitive": trans, "risk": risk,
                "bump_id": bump["bump_id"],
            })
        except Exception:
            results.append({
                "dep": dep, "current_ver": current_ver,
                "latest_ver": latest_ver, "is_latest": False,
                "affected": 0, "direct": 0, "transitive": 0,
                "risk": "ERROR", "bump_id": None,
            })

    # Sort: HIGH → MEDIUM → LOW → SAFE → UP TO DATE → UNKNOWN/ERROR
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "SAFE": 3, "UP TO DATE": 4, "UNKNOWN": 5, "ERROR": 6}
    results.sort(key=lambda x: order.get(x["risk"], 99))
    return results
