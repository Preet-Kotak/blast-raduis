"""End-to-end test: pydantic app blast radius against real PyPI versions."""
import os
import sys

os.environ.setdefault(
    "MONGO_URI",
    "mongodb://preetkotaktesting_db_user:aeiFEDj6PmjXQhZA@"
    "ac-xtkk8vl-shard-00-00.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-01.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-02.z4hea8z.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-cicqe3-shard-0&authSource=admin",
)

print("[1] DB connection...", flush=True)
from blast.core.db import files_col, edges_col, bumps_col
files_col().count_documents({})
print("    OK", flush=True)

print("[2] Generating pydantic_app...", flush=True)
from scripts.generate_pydantic_app import generate
if not os.path.exists("pydantic_app"):
    generate("pydantic_app")
print("    OK", flush=True)

print("[3] Ingesting...", flush=True)
from blast.core.ingest import ingest_repo
# Clear old data first
old_repo_id = None
sample = files_col().find_one({"path": {"$regex": "pydantic_app"}})
if sample:
    old_repo_id = sample.get("repo_id")
    files_col().delete_many({"repo_id": old_repo_id})
    edges_col().delete_many({"repo_id": old_repo_id})
    bumps_col().delete_many({"repo_id": old_repo_id})
    print(f"    Cleared old repo {old_repo_id}", flush=True)

repo_id = ingest_repo("pydantic_app")
print(f"    repo_id: {repo_id}", flush=True)

n_files = files_col().count_documents({"repo_id": repo_id})
n_edges = edges_col().count_documents({"repo_id": repo_id})
print(f"    {n_files} files, {n_edges} edges in MongoDB", flush=True)

print("[4] PyPI diff pydantic 1.10.0 -> 2.0.0 (uses cache)...", flush=True)
from blast.core.pypi_diff import diff_versions
removed = diff_versions("pydantic", "1.10.0", "2.0.0")
print(f"    {len(removed)} removed names: {removed[:8]}...", flush=True)

print("[5] Simulating bump...", flush=True)
from blast.core.bump import simulate_bump
result = simulate_bump(repo_id, "pydantic", "2.0.0")
print(f"    is_safe: {result.is_safe}", flush=True)

direct     = [f for f in result.affected if f["label"] == "DIRECT"]
transitive = [f for f in result.affected if f["label"] == "TRANSITIVE"]
safe       = [f for f in result.affected if f["label"] == "SAFE"]

print(f"\n{'='*60}")
print(f"BLAST RADIUS  pydantic 1.10.0 → 2.0.0")
print(f"{'='*60}")
print(f"\n🔴 DIRECT ({len(direct)})")
for f in direct:
    usages = f.get("usages", [])
    print(f"  {f['path']}")
    for u in usages:
        print(f"    line {u['line']:>3d}  {u['name']:<25s}  {u['snippet']}")

print(f"\n🟡 TRANSITIVE ({len(transitive)})")
for f in transitive:
    print(f"  {f['path']:<45s}  via {f.get('via','?')}")

print(f"\n🟢 SAFE ({len(safe)})")
print(f"  {', '.join(f['path'] for f in safe)}")

print(f"\n🔧 FIX ORDER")
for i, p in enumerate(result.fix_order, 1):
    print(f"  {i}. {p}")

assert not result.is_safe, "Expected unsafe bump"
assert len(direct) > 0, "Expected DIRECT files"
assert len(transitive) > 0, "Expected TRANSITIVE files"
print(f"\n{'='*60}")
print("All checks passed.")
