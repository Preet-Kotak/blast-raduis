"""Smoke test for bump.py and apidiff.py. Run from blast-radius/ folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.ingest import ingest_repo
from blast.core.bump import simulate_bump
from blast.core.apidiff import diff_versions

print("=== Ingesting sample_repo ===")
repo_id = ingest_repo("sample_repo")
print(f"repo_id: {repo_id}")

print("\n=== Blast radius: fakehttp → 2.0 ===")
result = simulate_bump(repo_id, "fakehttp", "2.0")
print(f"bump_id : {result.bump_id}")
print(f"is_safe : {result.is_safe}  (expected: False)")
print(f"\nAffected files ({len(result.affected)}):")
for f in result.affected:
    print(f"  [{f['label']:<11s}] {f['path']}")

print(f"\nFix order ({len(result.fix_order)} files):")
for i, path in enumerate(result.fix_order, 1):
    print(f"  {i}. {path}")

label_map = {f["path"]: f["label"] for f in result.affected}
expected = {
    "api/client.py":  "DIRECT",
    "utils/retry.py": "DIRECT",
    "main.py":        "TRANSITIVE",
    "api/auth.py":    "TRANSITIVE",
    "models/user.py": "SAFE",
}
print("\n=== Label checks ===")
all_ok = True
for path, expected_label in expected.items():
    actual = label_map.get(path, "MISSING")
    ok = actual == expected_label
    print(f"  {'OK' if ok else 'FAIL'} {path:<30s} expected={expected_label}, got={actual}")
    if not ok:
        all_ok = False

print("\n=== API diff: fakehttp 1.0 → 2.0 ===")
removed = diff_versions("fakehttp", "1.0", "2.0")
print(f"Removed names: {removed}  (expected: ['HTTPError', 'delete'])")
assert removed == ["HTTPError", "delete"], f"Unexpected diff: {removed}"

print("\nAll checks passed." if all_ok else "\nSOME CHECKS FAILED.")
