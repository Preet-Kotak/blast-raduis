"""Clear all data and re-ingest pydantic_app. Run from blast-radius/ folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.db import files_col, edges_col, bumps_col, history_col
from blast.core.service import ingest_repo, list_repos

print("Clearing all collections...")
files_col().delete_many({})
edges_col().delete_many({})
bumps_col().delete_many({})
history_col().delete_many({})
print("Done.")

print("\nRe-ingesting pydantic_app...")
repo_id = ingest_repo("pydantic_app")
print(f"repo_id: {repo_id}")

repos = list_repos()
print("\nlist_repos() now returns:")
for r in repos:
    print(f"  repo_id={r['repo_id']}  path={r['path']}  files={r['file_count']}")
