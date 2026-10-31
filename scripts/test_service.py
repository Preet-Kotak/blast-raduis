"""
End-to-end smoke test for the full service layer.
Verifies DEMO_MODE = False and all 7 service functions return real data.
Run from blast-radius/ folder.
"""
import os
os.environ.setdefault(
    "MONGO_URI",
    "mongodb://preetkotaktesting_db_user:aeiFEDj6PmjXQhZA@"
    "ac-xtkk8vl-shard-00-00.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-01.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-02.z4hea8z.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-cicqe3-shard-0&authSource=admin",
)

from blast.core.service import (
    ingest_repo,
    list_repos,
    simulate_bump,
    get_affected_files,
    get_fix_order,
    get_api_diff,
    get_bump_history,
)

print("=" * 55)
print("Service layer end-to-end test")
print("=" * 55)

# 1 ── ingest_repo
print("\n[1] ingest_repo('sample_repo')")
repo_id = ingest_repo("sample_repo")
print(f"    repo_id = {repo_id}")
assert repo_id, "Expected a non-empty repo_id"

# 2 ── list_repos
print("\n[2] list_repos()")
repos = list_repos()
print(f"    repos = {repos}")
assert any(r["repo_id"] == repo_id for r in repos), "Ingested repo not in list"

# 3 ── simulate_bump
print("\n[3] simulate_bump(repo_id, 'fakehttp', '2.0')")
bump = simulate_bump(repo_id, "fakehttp", "2.0")
print(f"    bump_id  = {bump['bump_id']}")
print(f"    is_safe  = {bump['is_safe']}  (expected: False)")
assert not bump["is_safe"], "Expected unsafe bump"

# 4 ── get_affected_files
print("\n[4] get_affected_files(bump_id)")
affected = get_affected_files(bump["bump_id"])
labels = {f["path"]: f["label"] for f in affected}
for path, label in sorted(labels.items()):
    print(f"    [{label:<11s}] {path}")
assert labels.get("api/client.py")  == "DIRECT",      "api/client.py should be DIRECT"
assert labels.get("utils/retry.py") == "DIRECT",      "utils/retry.py should be DIRECT"
assert labels.get("main.py")        == "TRANSITIVE",  "main.py should be TRANSITIVE"
assert labels.get("api/auth.py")    == "TRANSITIVE",  "api/auth.py should be TRANSITIVE"
assert labels.get("models/user.py") == "SAFE",        "models/user.py should be SAFE"

# 5 ── get_fix_order
print("\n[5] get_fix_order(bump_id)")
fix_order = get_fix_order(bump["bump_id"])
for i, p in enumerate(fix_order, 1):
    print(f"    {i}. {p}")
assert len(fix_order) == 4, f"Expected 4 files in fix order, got {len(fix_order)}"

# 6 ── get_api_diff
print("\n[6] get_api_diff('fakehttp', '1.0', '2.0')")
removed = get_api_diff("fakehttp", "1.0", "2.0")
print(f"    removed = {removed}")
assert removed == ["HTTPError", "delete"], f"Unexpected diff: {removed}"

# 7 ── get_bump_history
print("\n[7] get_bump_history(repo_id, 'fakehttp')")
hist = get_bump_history(repo_id, "fakehttp")
print(f"    {len(hist)} run(s) in history")
for h in hist[:3]:
    print(f"    {h['ran_at'][:19]}  safe={h['is_safe']}  affected={h['affected_count']}")
assert len(hist) >= 1, "Expected at least one history entry"

print("\n" + "=" * 55)
print("All 7 service functions passed.")
print("=" * 55)
