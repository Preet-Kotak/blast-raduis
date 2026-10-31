"""Test the real PyPI diff against actual packages."""
import sys
sys.path.insert(0, ".")

from blast.core.pypi_diff import diff_versions, get_package_versions, _get_public_names

print("=" * 60)
print("PyPI Diff — real package test")
print("=" * 60)

# ── Test 1: requests 2.27.0 → 2.28.0 (minor, few removals expected) ──────────
print("\n[1] requests 2.27.0 → 2.28.0")
names_old = _get_public_names("requests", "2.27.0")
names_new = _get_public_names("requests", "2.28.0")
removed = sorted(names_old - names_new)
added   = sorted(names_new - names_old)
print(f"    Old names ({len(names_old)}): {sorted(names_old)[:10]}...")
print(f"    New names ({len(names_new)}): {sorted(names_new)[:10]}...")
print(f"    Removed: {removed}")
print(f"    Added:   {added}")

# ── Test 2: discord.py — check available versions ─────────────────────────────
print("\n[2] discord.py — available versions (first 10)")
versions = get_package_versions("discord.py")
print(f"    Found {len(versions)} versions")
print(f"    Latest: {versions[:10]}")

# ── Test 3: discord.py 1.7.3 → 2.0.0 ────────────────────────────────────────
print("\n[3] discord.py 1.7.3 → 2.0.0  (downloading — may take a moment...)")
removed_discord = diff_versions("discord.py", "1.7.3", "2.0.0")
print(f"    Removed names ({len(removed_discord)}): {removed_discord[:20]}")
assert isinstance(removed_discord, list), "Expected a list"

print("\n" + "=" * 60)
print("All PyPI diff tests passed.")
print("=" * 60)
