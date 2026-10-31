"""Quick smoke test for parser + ingest. Run from blast-radius/ folder."""
import os
os.environ.setdefault(
    "MONGO_URI",
    "mongodb://preetkotaktesting_db_user:aeiFEDj6PmjXQhZA@"
    "ac-xtkk8vl-shard-00-00.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-01.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-02.z4hea8z.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-cicqe3-shard-0&authSource=admin",
)

from blast.core.ingest import ingest_repo
from blast.core.db import files_col, edges_col

# ── Run 1 ──────────────────────────────────────────────────────────────────────
print("=== Ingest run 1 ===")
repo_id = ingest_repo("sample_repo")
print(f"repo_id: {repo_id}")

files = list(files_col().find({"repo_id": repo_id}, {"_id": 0, "path": 1, "deps": 1, "local_imports": 1}))
print(f"Files stored: {len(files)}")
for f in sorted(files, key=lambda x: x["path"]):
    print(f"  {f['path']:<35s}  deps={f['deps']}  local={f['local_imports']}")

edges = list(edges_col().find({"repo_id": repo_id}, {"_id": 0, "from": 1, "to": 1}))
print(f"\nEdges stored: {len(edges)}")
for e in sorted(edges, key=lambda x: x["from"]):
    print(f"  {e['from']:<35s} -> {e['to']}")

# ── Run 2: idempotency ─────────────────────────────────────────────────────────
print("\n=== Ingest run 2 (idempotency check) ===")
ingest_repo("sample_repo")
count2 = files_col().count_documents({"repo_id": repo_id})
edges2 = edges_col().count_documents({"repo_id": repo_id})
print(f"Files: {count2}  (was {len(files)}) — {'OK' if count2 == len(files) else 'DUPLICATE DETECTED'}")
print(f"Edges: {edges2}  (was {len(edges)}) — {'OK' if edges2 == len(edges) else 'DUPLICATE DETECTED'}")

assert count2 == len(files), "Idempotency failed: duplicate file nodes"
assert edges2 == len(edges), "Idempotency failed: duplicate edges"
print("\nAll checks passed.")
