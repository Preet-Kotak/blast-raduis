"""
Master test runner — runs all tests in sequence.
Run from blast-radius/ folder:
    python scripts/run_all_tests.py
"""
import os, sys, traceback, time

# ── Setup path and credentials ─────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load
load()

from blast.core.db import files_col, edges_col, bumps_col, history_col
from blast.core.ingest import ingest_repo
from blast.core.service import (
    list_repos, simulate_bump,
    get_affected_files, get_fix_order, get_api_diff, get_bump_history,
)
from blast.core.pypi_diff import diff_versions as pypi_diff_versions
from blast.core.apidiff import diff_versions as fake_diff_versions
from blast.core.parser import parse_file, find_name_usages

PASS = "PASS"
FAIL = "FAIL"
results = []

def test(name, fn):
    t = time.time()
    try:
        fn()
        elapsed = time.time() - t
        results.append((PASS, name, f"{elapsed:.1f}s", ""))
        print(f"  {PASS}  {name}  ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - t
        results.append((FAIL, name, f"{elapsed:.1f}s", str(e)))
        print(f"  {FAIL}  {name}  ({elapsed:.1f}s)")
        print(f"       {e}")

print()
print("=" * 65)
print("BLAST RADIUS — Full Test Suite")
print("=" * 65)

# ── Fresh DB state ─────────────────────────────────────────────────────────────
print("\n[Setup] Clearing DB...")
files_col().delete_many({})
edges_col().delete_many({})
bumps_col().delete_many({})
history_col().delete_many({})
print("  Done.\n")

# ─────────────────────────────────────────────────────────────────────────────
print("GROUP 1: Parser (pure, no DB)")
print("-" * 40)

def t_parse_fakehttp():
    from blast.core.parser import parse_file
    result = parse_file("sample_repo/api/client.py",
                        repo_root=os.path.abspath("sample_repo"))
    assert "fakehttp" in result.third_party_deps, f"Expected fakehttp, got {result.third_party_deps}"

def t_parse_safe_file():
    result = parse_file("sample_repo/models/user.py",
                        repo_root=os.path.abspath("sample_repo"))
    assert result.third_party_deps == [], f"Expected no deps, got {result.third_party_deps}"

def t_find_usages():
    usages = find_name_usages("sample_repo/api/client.py", ["delete", "HTTPError"])
    assert any(u["name"] == "delete" for u in usages), f"delete not found in usages: {usages}"

test("parse_file detects fakehttp dep", t_parse_fakehttp)
test("parse_file returns empty deps for safe file", t_parse_safe_file)
test("find_name_usages finds delete in api/client.py", t_find_usages)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 2: Ingest (fakehttp sample repo)")
print("-" * 40)

FAKE_REPO_ID = None

def t_ingest_fakehttp():
    global FAKE_REPO_ID
    FAKE_REPO_ID = ingest_repo("sample_repo")
    assert FAKE_REPO_ID, "No repo_id returned"
    count = files_col().count_documents({"repo_id": FAKE_REPO_ID})
    assert count == 8, f"Expected 8 files, got {count}"

def t_ingest_idempotent():
    ingest_repo("sample_repo")
    count = files_col().count_documents({"repo_id": FAKE_REPO_ID})
    assert count == 8, f"Duplicate files after 2nd ingest: {count}"
    edge_count = edges_col().count_documents({"repo_id": FAKE_REPO_ID})
    assert edge_count == 6, f"Duplicate edges after 2nd ingest: {edge_count}"

def t_repo_root_stored():
    doc = files_col().find_one({"repo_id": FAKE_REPO_ID}, {"repo_root": 1})
    assert doc and doc.get("repo_root"), "repo_root not stored"

test("ingest_repo stores 8 files + 6 edges", t_ingest_fakehttp)
test("ingest is idempotent (no duplicates on 2nd run)", t_ingest_idempotent)
test("repo_root is stored in file documents", t_repo_root_stored)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 3: Fakelib API diff")
print("-" * 40)

def t_fakehttp_diff():
    removed = fake_diff_versions("fakehttp", "1.0", "2.0")
    assert removed == ["HTTPError", "delete"], f"Wrong diff: {removed}"

def t_fakehttp_diff_no_removal():
    removed = fake_diff_versions("fakehttp", "1.0", "1.0")
    assert removed == [], f"Same version should have no removals: {removed}"

test("fakehttp 1.0→2.0 removes ['HTTPError', 'delete']", t_fakehttp_diff)
test("fakehttp 1.0→1.0 returns empty diff", t_fakehttp_diff_no_removal)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 4: Blast radius engine (fakehttp)")
print("-" * 40)

FAKE_BUMP_ID = None

def t_simulate_bump_unsafe():
    global FAKE_BUMP_ID
    result = simulate_bump(FAKE_REPO_ID, "fakehttp", "2.0")
    FAKE_BUMP_ID = result["bump_id"]
    assert not result["is_safe"], "Expected unsafe bump"

def t_affected_labels():
    affected = get_affected_files(FAKE_BUMP_ID)
    labels = {f["path"]: f["label"] for f in affected}
    assert labels["api/client.py"]  == "DIRECT",     f"api/client.py: {labels.get('api/client.py')}"
    assert labels["utils/retry.py"] == "DIRECT",     f"utils/retry.py: {labels.get('utils/retry.py')}"
    assert labels["main.py"]        == "TRANSITIVE", f"main.py: {labels.get('main.py')}"
    assert labels["api/auth.py"]    == "TRANSITIVE", f"api/auth.py: {labels.get('api/auth.py')}"
    assert labels["models/user.py"] == "SAFE",       f"models/user.py: {labels.get('models/user.py')}"

def t_transitive_via():
    affected = get_affected_files(FAKE_BUMP_ID)
    trans = {f["path"]: f.get("via") for f in affected if f["label"] == "TRANSITIVE"}
    assert trans.get("main.py"),     f"main.py missing via: {trans}"
    assert trans.get("api/auth.py"), f"api/auth.py missing via: {trans}"

def t_line_numbers():
    affected = get_affected_files(FAKE_BUMP_ID)
    fm = {f["path"]: f for f in affected}
    client = fm["api/client.py"]["usages"]
    retry  = fm["utils/retry.py"]["usages"]
    assert any(u["name"] == "delete"    for u in client), f"delete not found: {client}"
    assert any(u["name"] == "HTTPError" for u in retry),  f"HTTPError not found: {retry}"

def t_fix_order():
    order = get_fix_order(FAKE_BUMP_ID)
    assert len(order) == 4, f"Expected 4 files in fix order, got {len(order)}"

def t_history_saved():
    hist = get_bump_history(FAKE_REPO_ID, "fakehttp")
    assert len(hist) >= 1, "No history saved"
    assert not hist[0]["is_safe"]

test("simulate_bump returns is_safe=False", t_simulate_bump_unsafe)
test("DIRECT/TRANSITIVE/SAFE labels correct", t_affected_labels)
test("TRANSITIVE files have 'via' chain reason", t_transitive_via)
test("DIRECT files have line-level usages", t_line_numbers)
test("fix_order contains 4 files", t_fix_order)
test("history record saved", t_history_saved)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 5: Real PyPI diff (pydantic)")
print("-" * 40)

def t_pypi_versions():
    from blast.core.pypi_diff import get_package_versions
    versions = get_package_versions("pydantic")
    assert len(versions) > 10, f"Expected many versions, got {len(versions)}"
    # Check stable-only (no beta/rc)
    import re
    bad = [v for v in versions if re.search(r'(a|b|rc|dev)\d*', v)]
    assert not bad, f"Pre-release versions in list: {bad[:5]}"

def t_pypi_diff_pydantic():
    removed = pypi_diff_versions("pydantic", "1.10.0", "2.0.1")
    assert len(removed) >= 15, f"Expected many removals, got {len(removed)}: {removed}"
    assert "BaseSettings"       in removed, "BaseSettings should be removed"
    assert "ConstrainedStr"     in removed, "ConstrainedStr should be removed"
    assert "validate_arguments" in removed, "validate_arguments should be removed"

test("get_package_versions returns stable-only list", t_pypi_versions)
test("pydantic 1.10.0→2.0.1 finds real removals", t_pypi_diff_pydantic)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 6: Real blast radius (pydantic app)")
print("-" * 40)

PYDANTIC_REPO_ID = None
PYDANTIC_BUMP_ID = None

def t_ingest_pydantic():
    global PYDANTIC_REPO_ID
    PYDANTIC_REPO_ID = ingest_repo("pydantic_app")
    count = files_col().count_documents({"repo_id": PYDANTIC_REPO_ID})
    assert count == 14, f"Expected 14 files, got {count}"
    doc = files_col().find_one({"repo_id": PYDANTIC_REPO_ID}, {"repo_root": 1})
    assert doc and "pydantic_app" in doc.get("repo_root",""), "repo_root wrong"

def t_bump_pydantic():
    global PYDANTIC_BUMP_ID
    result = simulate_bump(PYDANTIC_REPO_ID, "pydantic", "2.0.1")
    PYDANTIC_BUMP_ID = result["bump_id"]
    assert not result["is_safe"], "Expected unsafe"

def t_pydantic_labels():
    affected = get_affected_files(PYDANTIC_BUMP_ID)
    labels = {f["path"]: f["label"] for f in affected}
    assert labels.get("config.py")        == "DIRECT"
    assert labels.get("models/user.py")   == "DIRECT"
    assert labels.get("models/item.py")   == "DIRECT"
    assert labels.get("utils/validation.py") == "DIRECT"
    assert labels.get("main.py")          == "TRANSITIVE"
    assert labels.get("utils/helpers.py") == "SAFE"

def t_pydantic_line_numbers():
    affected = get_affected_files(PYDANTIC_BUMP_ID)
    fm = {f["path"]: f for f in affected}
    config_usages = fm["config.py"]["usages"]
    assert any(u["name"] == "BaseSettings"   for u in config_usages)
    assert any(u["name"] == "parse_raw_as"   for u in config_usages)
    val_usages = fm["utils/validation.py"]["usages"]
    assert any(u["name"] == "validate_arguments" for u in val_usages)

def t_pydantic_history():
    hist = get_bump_history(PYDANTIC_REPO_ID, "pydantic")
    assert len(hist) >= 1

test("ingest pydantic_app (14 files, repo_root stored)", t_ingest_pydantic)
test("simulate_bump pydantic 1.10.0→2.0.1 is unsafe", t_bump_pydantic)
test("DIRECT/TRANSITIVE/SAFE labels correct", t_pydantic_labels)
test("line numbers: BaseSettings/parse_raw_as/validate_arguments found", t_pydantic_line_numbers)
test("pydantic bump history saved", t_pydantic_history)

# ─────────────────────────────────────────────────────────────────────────────
print("\nGROUP 7: list_repos shows correct paths")
print("-" * 40)

def t_list_repos():
    repos = list_repos()
    paths = [r["path"] for r in repos]
    assert any("pydantic_app" in p for p in paths), f"pydantic_app not in repos: {paths}"
    assert any("sample_repo"  in p for p in paths), f"sample_repo not in repos: {paths}"

def t_demo_mode_fallback():
    # app.py's demo stubs should be importable independently
    import ast
    with open("app.py", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)  # syntax check

test("list_repos returns full root paths", t_list_repos)
test("app.py parses without syntax errors", t_demo_mode_fallback)

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 65)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
print("=" * 65)
if failed:
    print("\nFailed tests:")
    for status, name, t, err in results:
        if status == FAIL:
            print(f"  FAIL  {name}")
            print(f"        {err}")
    sys.exit(1)
else:
    print("\nAll tests passed.")
    sys.exit(0)
