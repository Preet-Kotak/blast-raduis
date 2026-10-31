"""End-to-end test: real pydantic 1.10 → 2.0.1 blast radius via PyPI."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

print("[1] DB connection...", flush=True)
from blast.core.db import files_col, edges_col, bumps_col
files_col().count_documents({})
print("    OK", flush=True)

print("[2] Generating pydantic_app...", flush=True)
if not os.path.exists("pydantic_app"):
    from scripts.generate_pydantic_app import generate
    generate("pydantic_app")
print("    OK", flush=True)

print("[3] Ingesting...", flush=True)
from blast.core.ingest import ingest_repo
from blast.core.db import history_col

# Clear old pydantic_app data
sample = files_col().find_one({"repo_root": {"$regex": "pydantic_app"}})
if sample:
    rid = sample["repo_id"]
    files_col().delete_many({"repo_id": rid})
    edges_col().delete_many({"repo_id": rid})
    bumps_col().delete_many({"repo_id": rid})
    history_col().delete_many({"repo_id": rid})
    print(f"    Cleared old repo {rid}", flush=True)

repo_id = ingest_repo("pydantic_app")
print(f"    repo_id: {repo_id}", flush=True)
print(f"    files: {files_col().count_documents({'repo_id': repo_id})}", flush=True)
print(f"    edges: {edges_col().count_documents({'repo_id': repo_id})}", flush=True)

# Verify repo_root is stored
doc = files_col().find_one({"repo_id": repo_id}, {"repo_root": 1})
assert doc and doc.get("repo_root"), "repo_root not stored — list_repos will break"
print(f"    repo_root stored: {doc['repo_root']}", flush=True)

print("[4] PyPI diff pydantic 1.10.0 -> 2.0.1...", flush=True)
from blast.core.pypi_diff import diff_versions
removed = diff_versions("pydantic", "1.10.0", "2.0.1")
print(f"    {len(removed)} removed names", flush=True)
assert len(removed) > 10, f"Expected many removals, got: {removed}"

print("[5] Simulating bump...", flush=True)
from blast.core.service import simulate_bump as svc_simulate_bump, get_bump_history
svc_result = svc_simulate_bump(repo_id, "pydantic", "2.0.1")

from blast.core.bump import get_bump_result
bump_doc = get_bump_result(svc_result["bump_id"])

direct     = [f for f in bump_doc["affected"] if f["label"] == "DIRECT"]
transitive = [f for f in bump_doc["affected"] if f["label"] == "TRANSITIVE"]
safe       = [f for f in bump_doc["affected"] if f["label"] == "SAFE"]

print(f"\n{'='*60}")
print(f"BLAST RADIUS  pydantic 1.10.0 → 2.0.1")
print(f"{'='*60}")

print(f"\n🔴 DIRECT ({len(direct)})")
for f in direct:
    print(f"  {f['path']}")
    for u in f.get("usages", []):
        print(f"    line {u['line']:>3d}  {u['name']:<25s}  {u['snippet']}")

print(f"\n🟡 TRANSITIVE ({len(transitive)})")
for f in transitive:
    print(f"  {f['path']:<45s}  via {f.get('via','?')}")

print(f"\n🟢 SAFE ({len(safe)})")
print(f"  {', '.join(f['path'] for f in safe)}")

print(f"\n🔧 FIX ORDER")
for i, p in enumerate(bump_doc["fix_order"], 1):
    print(f"  {i}. {p}")

print(f"\n{'='*60}")
print("[6] Assertions...")
assert not svc_result["is_safe"],    "Expected unsafe bump"
assert len(direct) >= 3,      f"Expected >=3 DIRECT files, got {len(direct)}"
assert len(transitive) >= 3,  f"Expected >=3 TRANSITIVE files, got {len(transitive)}"
assert any(f["path"] == "utils/helpers.py" and f["label"] == "SAFE" for f in safe), \
    "utils/helpers.py should be SAFE"
direct_with_usages = [f for f in direct if f.get("usages")]
assert len(direct_with_usages) >= 2, "Expected line-level usages in DIRECT files"

print("[7] History check...")
hist = get_bump_history(repo_id, "pydantic")
assert len(hist) >= 1
print(f"    {len(hist)} run(s) in history — OK")

print("\nAll checks passed.")
