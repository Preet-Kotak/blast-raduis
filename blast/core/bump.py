"""
blast.core.bump — Blast radius simulation engine.

Given a repo and a dependency name, finds every file affected by a version bump:
  - DIRECT:     file imports the dep itself
  - TRANSITIVE: file imports something that (eventually) imports the dep
  - SAFE:       file has no path to the dep

Uses MongoDB $graphLookup to traverse the import graph, then Kahn's algorithm
to produce a bottom-up fix order.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from blast.core.db import bumps_col, edges_col, files_col
from blast.core.pypi_diff import diff_versions


@dataclass
class BumpResult:
    bump_id: str
    repo_id: str
    dep: str
    target_version: str
    affected: list[dict]          # [{"path": str, "label": str}, ...]
    fix_order: list[str]          # paths, leaves first
    is_safe: bool
    ran_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def simulate_bump(repo_id: str, dep: str, target_version: str) -> BumpResult:
    """
    Find all files in repo_id affected when `dep` bumps to `target_version`.

    Steps:
      1. Find the virtual dep node name (e.g. "fakehttp@1.0")
      2. $graphLookup backwards from that node through edges to find all
         files that can reach it
      3. Label each file DIRECT or TRANSITIVE
      4. Kahn topological sort → fix order
      5. Persist result to bumps collection
      6. Return BumpResult

    Args:
        repo_id:        Repo identifier from ingest_repo().
        dep:            Dependency name (e.g. "fakehttp").
        target_version: Version being bumped to (e.g. "2.0").

    Returns:
        BumpResult with affected files, fix order, and safety flag.
    """
    # ── 1. Find the dep node as it was pinned when ingested ────────────────
    dep_node = _find_dep_node(repo_id, dep)

    # ── 2. Find all files that can reach this dep node (reverse traversal) ─
    direct_files, transitive_map = _find_affected_files(repo_id, dep_node)
    # transitive_map: {path -> via_path} where via_path is the direct dep file it chains through

    # ── 2b. Get removed names so we can attach line hits ───────────────────
    # Use "1.0" as the from-version (what's currently pinned)
    pinned_edge = edges_col().find_one({"repo_id": repo_id, "dep": dep}, {"version": 1})
    from_ver = pinned_edge["version"] if pinned_edge else "1.0"
    removed_names = diff_versions(dep, from_ver, target_version)

    # ── 3. Build affected list ─────────────────────────────────────────────
    affected: list[dict] = []
    all_file_docs = list(files_col().find(
        {"repo_id": repo_id},
        {"_id": 0, "path": 1, "dep_usages": 1}
    ))

    direct_set = set(direct_files)
    transitive_set = set(transitive_map.keys()) - direct_set

    for doc in all_file_docs:
        path = doc["path"]
        dep_usages = doc.get("dep_usages", {})

        # Filter stored usages to only the removed names
        raw_usages = dep_usages.get(dep, [])
        risky_usages = [
            u for u in raw_usages if u.get("name") in removed_names
        ] if removed_names else raw_usages

        if path in direct_set:
            affected.append({"path": path, "label": "DIRECT",
                             "usages": risky_usages, "via": None})
        elif path in transitive_set:
            affected.append({"path": path, "label": "TRANSITIVE",
                             "usages": [], "via": transitive_map.get(path)})
        else:
            affected.append({"path": path, "label": "SAFE",
                             "usages": [], "via": None})

    # Sort: DIRECT first, then TRANSITIVE, then SAFE
    label_order = {"DIRECT": 0, "TRANSITIVE": 1, "SAFE": 2}
    affected.sort(key=lambda x: (label_order[x["label"]], x["path"]))

    # ── 4. Compute fix order (only for non-SAFE files) ─────────────────────
    unsafe_paths = {f["path"] for f in affected if f["label"] != "SAFE"}
    fix_order = _topological_fix_order(repo_id, unsafe_paths)

    is_safe = len(unsafe_paths) == 0

    # ── 5. Persist ─────────────────────────────────────────────────────────
    bump_id = str(uuid.uuid4())[:8]
    result = BumpResult(
        bump_id=bump_id,
        repo_id=repo_id,
        dep=dep,
        target_version=target_version,
        affected=affected,
        fix_order=fix_order,
        is_safe=is_safe,
    )
    bumps_col().insert_one({
        "_id": bump_id,
        "repo_id": repo_id,
        "dep": dep,
        "target_version": target_version,
        "affected": affected,
        "fix_order": fix_order,
        "is_safe": is_safe,
        "ran_at": result.ran_at,
    })

    return result


def get_bump_result(bump_id: str) -> dict | None:
    """Retrieve a previously stored bump result by ID."""
    return bumps_col().find_one({"_id": bump_id}, {"_id": 0})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _find_dep_node(repo_id: str, dep: str) -> str:
    """
    Return the virtual dep node string (e.g. "fakehttp@1.0") used in edges.
    Falls back to "dep@unknown" if not found.
    """
    edge = edges_col().find_one(
        {"repo_id": repo_id, "dep": dep},
        {"to": 1}
    )
    return edge["to"] if edge else f"{dep}@unknown"


def _find_affected_files(
    repo_id: str, dep_node: str
) -> tuple[list[str], dict[str, str]]:
    """
    Use $graphLookup to traverse the import graph BACKWARDS from dep_node.

    Returns:
        (direct_files, transitive_map)
        direct_files:    files with a direct edge to dep_node
        transitive_map:  {transitive_path -> nearest_direct_file it chains through}
    """
    # Direct files: edges where "to" == dep_node
    direct_edges = list(edges_col().find(
        {"repo_id": repo_id, "to": dep_node},
        {"from": 1, "_id": 0}
    ))
    direct_files = [e["from"] for e in direct_edges if "@" not in e["from"]]

    if not direct_files:
        return [], {}

    # $graphLookup backwards: for each direct file, find everything that
    # imports it (directly or transitively).
    pipeline = [
        {"$match": {"repo_id": repo_id, "to": dep_node}},
        {
            "$graphLookup": {
                "from": "edges",
                "startWith": "$from",
                "connectFromField": "from",
                "connectToField": "to",
                "as": "ancestors",
                "restrictSearchWithMatch": {"repo_id": repo_id},
                "maxDepth": 20,
            }
        },
        {
            "$project": {
                "direct": "$from",
                "ancestors": "$ancestors.from",
            }
        },
    ]

    # Build transitive_map: ancestor → the direct file it was reached from
    transitive_map: dict[str, str] = {}
    for doc in edges_col().aggregate(pipeline):
        direct = doc["direct"]
        if "@" in direct:
            continue
        for ancestor in doc.get("ancestors", []):
            if "@" not in ancestor and ancestor not in direct_files:
                # Only record first-seen (shortest chain wins)
                if ancestor not in transitive_map:
                    transitive_map[ancestor] = direct

    return direct_files, transitive_map


def _topological_fix_order(repo_id: str, paths: set[str]) -> list[str]:
    """
    Return a topological ordering of `paths` using Kahn's algorithm.

    The order is "leaves first" — files with no dependents in the affected
    set come first (they are safe to fix without breaking other files).

    Files not in the subgraph edges are appended at the end.
    """
    if not paths:
        return []

    # Build adjacency (from → to) restricted to the affected subgraph
    edges = list(edges_col().find(
        {"repo_id": repo_id, "from": {"$in": list(paths)}},
        {"from": 1, "to": 1, "_id": 0}
    ))

    # in-degree count and adjacency list within affected set
    in_degree: dict[str, int] = {p: 0 for p in paths}
    adj: dict[str, list[str]] = {p: [] for p in paths}

    for e in edges:
        src, dst = e["from"], e["to"]
        if src in paths and dst in paths:
            adj[src].append(dst)
            in_degree[dst] = in_degree.get(dst, 0) + 1

    # Kahn's: start with nodes that have no incoming edges (no dependents)
    queue = sorted(p for p, deg in in_degree.items() if deg == 0)
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbour in sorted(adj.get(node, [])):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    # Append any remaining (cycle fallback)
    remaining = [p for p in sorted(paths) if p not in order]
    return order + remaining
