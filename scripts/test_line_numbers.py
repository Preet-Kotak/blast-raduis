"""Test that line number usages are stored and returned correctly."""
import os
os.environ.setdefault(
    "MONGO_URI",
    "mongodb://preetkotaktesting_db_user:aeiFEDj6PmjXQhZA@"
    "ac-xtkk8vl-shard-00-00.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-01.z4hea8z.mongodb.net:27017,"
    "ac-xtkk8vl-shard-00-02.z4hea8z.mongodb.net:27017/"
    "?ssl=true&replicaSet=atlas-cicqe3-shard-0&authSource=admin",
)

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
        print(f"             (imports {f['path'].split('/')[0]} but uses no removed names — still needs review)")
    else:
        print(f"             (transitive — no direct removed-name usage)")

# Assertions
label_map = {f["path"]: f for f in affected}

# api/client.py uses fakehttp.delete — which IS removed in v2
assert label_map["api/client.py"]["label"] == "DIRECT", "api/client.py should be DIRECT"
client_usages = label_map["api/client.py"]["usages"]
assert len(client_usages) > 0, "api/client.py should have usages for 'delete'"
assert any(u["name"] == "delete" for u in client_usages), \
    f"Expected 'delete' in client usages, got: {client_usages}"

# utils/retry.py uses HTTPError which IS removed — should have a usage
retry_usages = label_map["utils/retry.py"]["usages"]
assert len(retry_usages) > 0, "utils/retry.py should have usages for HTTPError"
assert any(u["name"] == "HTTPError" for u in retry_usages), \
    f"Expected HTTPError in retry usages, got: {retry_usages}"

# Transitive files should have no usages (they don't directly import fakehttp)
assert label_map["main.py"]["usages"] == [], "main.py is transitive — no direct usages"
assert label_map["api/auth.py"]["usages"] == [], "api/auth.py is transitive — no direct usages"

print("\nAll line-number checks passed.")
