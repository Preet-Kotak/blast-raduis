"""Quick smoke test for parser + ingest. Run from blast-radius/ folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.ingest import ingest_repo
from blast.core.db import files_col, edges_col

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

print("\n=== Ingest run 2 (idempotency check) ===")
ingest_repo("sample_repo")
count2 = files_col().count_documents({"repo_id": repo_id})
edges2 = edges_col().count_documents({"repo_id": repo_id})
print(f"Files: {count2}  (was {len(files)}) — {'OK' if count2 == len(files) else 'DUPLICATE DETECTED'}")
print(f"Edges: {edges2}  (was {len(edges)}) — {'OK' if edges2 == len(edges) else 'DUPLICATE DETECTED'}")
assert count2 == len(files)
assert edges2 == len(edges)
print("\nAll checks passed.")
