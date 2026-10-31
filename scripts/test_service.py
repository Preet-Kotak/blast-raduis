"""End-to-end smoke test for all 7 service functions. Run from blast-radius/ folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.service import (
    ingest_repo, list_repos, simulate_bump,
    get_affected_files, get_fix_order, get_api_diff, get_bump_history,
)

print("=" * 55)
print("Service layer end-to-end test")
print("=" * 55)

print("\n[1] ingest_repo('sample_repo')")
repo_id = ingest_repo("sample_repo")
print(f"    repo_id = {repo_id}")
assert repo_id

print("\n[2] list_repos()")
repos = list_repos()
print(f"    {repos}")
assert any(r["repo_id"] == repo_id for r in repos)

print("\n[3] simulate_bump")
bump = simulate_bump(repo_id, "fakehttp", "2.0")
print(f"    bump_id={bump['bump_id']}  is_safe={bump['is_safe']}")
assert not bump["is_safe"]

print("\n[4] get_affected_files")
affected = get_affected_files(bump["bump_id"])
labels = {f["path"]: f["label"] for f in affected}
for path, label in sorted(labels.items()):
    print(f"    [{label:<11s}] {path}")
assert labels.get("api/client.py")  == "DIRECT"
assert labels.get("utils/retry.py") == "DIRECT"
assert labels.get("main.py")        == "TRANSITIVE"
assert labels.get("models/user.py") == "SAFE"

print("\n[5] get_fix_order")
fix_order = get_fix_order(bump["bump_id"])
for i, p in enumerate(fix_order, 1):
    print(f"    {i}. {p}")
assert len(fix_order) == 4

print("\n[6] get_api_diff")
removed = get_api_diff("fakehttp", "1.0", "2.0")
print(f"    removed = {removed}")
assert removed == ["HTTPError", "delete"]

print("\n[7] get_bump_history")
hist = get_bump_history(repo_id, "fakehttp")
print(f"    {len(hist)} run(s)")
assert len(hist) >= 1

print("\n" + "=" * 55)
print("All 7 service functions passed.")
print("=" * 55)
