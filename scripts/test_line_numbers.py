"""Test that line number usages are stored and returned correctly."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.service import ingest_repo, simulate_bump, get_affected_files, get_api_diff

print("Ingesting sample_repo...")
repo_id = ingest_repo("sample_repo")

print("Simulating bump fakehttp → 2.0...")
bump = simulate_bump(repo_id, "fakehttp", "2.0")
affected = get_affected_files(bump["bump_id"])
removed = get_api_diff("fakehttp", "1.0", "2.0")

print(f"\nRemoved names: {removed}")
print(f"\nAffected files with line numbers:")
print("-" * 60)
for f in affected:
    usages = f.get("usages", [])
    print(f"[{f['label']:<11s}] {f['path']}")
    if usages:
        for u in usages:
            print(f"             line {u['line']:>3d}  {u['name']:<12s}  {u['snippet']}")
    elif f["label"] == "DIRECT":
        print(f"             (imports dep — no removed-name calls)")

label_map = {f["path"]: f for f in affected}
assert label_map["api/client.py"]["label"] == "DIRECT"
client_usages = label_map["api/client.py"]["usages"]
assert len(client_usages) > 0, "api/client.py should have usages for 'delete'"
assert any(u["name"] == "delete" for u in client_usages)
retry_usages = label_map["utils/retry.py"]["usages"]
assert len(retry_usages) > 0
assert any(u["name"] == "HTTPError" for u in retry_usages)

print("\nAll line-number checks passed.")
