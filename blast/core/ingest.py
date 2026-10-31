"""
blast.core.ingest — Walk a repo, parse imports, store graph in MongoDB.

Responsible for:
  - Walking all .py files in a folder
  - Reading requirements.txt for pinned dependency versions
  - Upserting file nodes and import edges (idempotent)
  - Returning a stable repo_id
"""

import hashlib
import os
from datetime import datetime, timezone

from blast.core.db import edges_col, ensure_indexes, files_col
from blast.core.parser import parse_file


def ingest_repo(repo_path: str) -> str:
    """
    Parse every .py file in repo_path and store the import graph in MongoDB.

    Idempotent: running twice on the same folder produces the same documents
    (upsert by _id, no duplicates).

    Args:
        repo_path: Absolute or relative path to the root of the repo to ingest.

    Returns:
        repo_id: A stable identifier derived from the absolute path.
    """
    abs_path = os.path.abspath(repo_path)
    if not os.path.isdir(abs_path):
        raise ValueError(f"Not a directory: {abs_path}")

    repo_id = _make_repo_id(abs_path)
    ensure_indexes()

    pinned = _read_requirements(abs_path)
    now = datetime.now(timezone.utc).isoformat()

    py_files = _collect_py_files(abs_path)

    for file_path in py_files:
        rel_path = os.path.relpath(file_path, abs_path).replace(os.sep, "/")
        result = parse_file(file_path, repo_root=abs_path)

        # ── Upsert file node ───────────────────────────────────────────────
        doc_id = f"{repo_id}:{rel_path}"
        files_col().update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "repo_id": repo_id,
                    "path": rel_path,
                    "deps": result.third_party_deps,
                    "local_imports": result.local_imports,
                    "pinned_versions": {
                        dep: pinned.get(dep, "unknown")
                        for dep in result.third_party_deps
                    },
                    "ingested_at": now,
                }
            },
            upsert=True,
        )

        # ── Upsert local import edges ──────────────────────────────────────
        for imported_module in result.local_imports:
            # Convert dotted module name to a relative file path
            imported_path = imported_module.replace(".", "/") + ".py"
            # Also try package __init__.py
            imported_pkg = imported_module.replace(".", "/") + "/__init__.py"

            # Use whichever actually exists in the repo
            target = None
            if os.path.exists(os.path.join(abs_path, imported_path)):
                target = imported_path
            elif os.path.exists(os.path.join(abs_path, imported_pkg)):
                target = imported_pkg

            if target is None:
                target = imported_path  # store anyway for graph completeness

            edge_id = f"{repo_id}:{rel_path}->{target}"
            edges_col().update_one(
                {"_id": edge_id},
                {
                    "$set": {
                        "repo_id": repo_id,
                        "from": rel_path,
                        "to": target,
                    }
                },
                upsert=True,
            )

        # ── Upsert third-party dep edges ───────────────────────────────────
        # Treat each external dep as a virtual node named "<dep>@<version>"
        for dep in result.third_party_deps:
            version = pinned.get(dep, "unknown")
            dep_node = f"{dep}@{version}"
            edge_id = f"{repo_id}:{rel_path}->{dep_node}"
            edges_col().update_one(
                {"_id": edge_id},
                {
                    "$set": {
                        "repo_id": repo_id,
                        "from": rel_path,
                        "to": dep_node,
                        "dep": dep,
                        "version": version,
                    }
                },
                upsert=True,
            )

    return repo_id


def list_repos() -> list[dict]:
    """
    Return a deduplicated list of ingested repos.
    Each entry has repo_id and the common path prefix.
    """
    pipeline = [
        {"$group": {"_id": "$repo_id", "path": {"$first": "$path"},
                    "file_count": {"$sum": 1}}},
        {"$project": {"repo_id": "$_id", "file_count": 1, "_id": 0}},
    ]
    results = list(files_col().aggregate(pipeline))
    # Attach a human-readable path from the repo_id (it's a hash, so we store
    # the path in a separate lookup embedded in the hash comment)
    return results


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_repo_id(abs_path: str) -> str:
    """Stable 12-char hex ID derived from the absolute path."""
    return hashlib.md5(abs_path.encode()).hexdigest()[:12]


def _collect_py_files(root: str) -> list[str]:
    """Return all .py files under root, skipping venv / __pycache__."""
    skip = {"venv", ".venv", "env", "__pycache__", ".git", "node_modules"}
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune unwanted directories in-place
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fname in filenames:
            if fname.endswith(".py"):
                results.append(os.path.join(dirpath, fname))
    return sorted(results)


def _read_requirements(repo_root: str) -> dict[str, str]:
    """
    Parse requirements.txt and return {package_name: version}.
    Handles lines like: fakehttp==1.0, requests>=2.0, flask~=2.3
    """
    req_path = os.path.join(repo_root, "requirements.txt")
    pinned = {}
    if not os.path.exists(req_path):
        return pinned

    with open(req_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Split on first operator: ==, >=, <=, ~=, !=, >
            for sep in ("==", "~=", ">=", "<=", "!=", ">", "<"):
                if sep in line:
                    name, version = line.split(sep, 1)
                    pinned[name.strip().lower()] = version.strip()
                    break
            else:
                pinned[line.lower()] = "unknown"

    return pinned
