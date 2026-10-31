"""Quick test — skips DB clear so it runs fast against existing data."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.service import ingest_repo, simulate_bump, get_affected_files, get_fix_order, get_api_diff
from blast.core.graph_viz import build_graph_html
from blast.core.migration_hints import get_unique_hints, get_hints_for_file
import json, ast

PASS = "PASS"; FAIL = "FAIL"
results = []

def test(name, fn):
    t = time.time()
    try:
        fn()
        results.append((PASS, name, f"{time.time()-t:.1f}s"))
        print(f"  {PASS}  {name}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL}  {name}: {e}")

# 1. Syntax
def t_syntax():
    for f in ["app.py", "blast/core/graph_viz.py", "blast/core/migration_hints.py"]:
        with open(f, encoding="utf-8") as fh: ast.parse(fh.read())
test("app.py + new modules syntax clean", t_syntax)

# 2. Fakehttp demo repo exists
def t_demo_repos():
    assert os.path.exists("demo_repos/fakehttp_app/main.py"), "fakehttp_app missing"
    assert os.path.exists("demo_repos/pydantic_app/config.py"), "pydantic_app missing"
test("demo_repos/ both present", t_demo_repos)

# 3. Fakehttp blast radius
rid = None; bid = None
def t_fakehttp():
    global rid, bid
    rid = ingest_repo("demo_repos/fakehttp_app")
    r = simulate_bump(rid, "fakehttp", "2.0")
    bid = r["bump_id"]
    assert not r["is_safe"]
    aff = get_affected_files(bid)
    labels = {f["path"]: f["label"] for f in aff}
    assert labels.get("api/client.py")  == "DIRECT"
    assert labels.get("main.py")        == "TRANSITIVE"
    assert labels.get("models/user.py") == "SAFE"
test("fakehttp blast radius correct labels", t_fakehttp)

# 4. Fix order DIRECT first
def t_fix_order():
    order = get_fix_order(bid)
    aff   = get_affected_files(bid)
    lmap  = {f["path"]: f["label"] for f in aff}
    direct_pos     = [i for i,p in enumerate(order) if lmap.get(p) == "DIRECT"]
    transitive_pos = [i for i,p in enumerate(order) if lmap.get(p) == "TRANSITIVE"]
    # After our UI fix, Step 1 = DIRECT, Step 2 = TRANSITIVE — both lists exist
    assert len(direct_pos) > 0,     "No DIRECT in fix_order"
    assert len(transitive_pos) > 0, "No TRANSITIVE in fix_order"
test("fix_order contains both DIRECT and TRANSITIVE", t_fix_order)

# 5. Graph HTML valid
def t_graph():
    aff = get_affected_files(bid)
    html = build_graph_html(aff, "fakehttp", "2.0")
    assert "lib/bindings/utils.js" not in html, "broken relative path still present"
    assert "vis-network" in html or "vis.min" in html, "vis.js missing"
    assert len(html) > 3000
test("graph HTML valid, lib/bindings patched", t_graph)

# 6. Migration hints
def t_hints():
    hints = get_unique_hints("pydantic", ["BaseSettings", "validator", "ConstrainedStr"])
    assert all("hint" in h for h in hints)
    assert hints[0]["hint"] != "Removed in this version — check the library's migration guide for a replacement."
test("migration hints specific for pydantic", t_hints)

# 7. JSON export structure
def t_json_export():
    aff   = get_affected_files(bid)
    order = get_fix_order(bid)
    rem   = get_api_diff("fakehttp", "1.0", "2.0")
    direct    = [f for f in aff if f["label"]=="DIRECT"]
    transitive= [f for f in aff if f["label"]=="TRANSITIVE"]
    fix_plan = {
        "dependency":    "fakehttp",
        "from_version":  "1.0",
        "to_version":    "2.0",
        "is_safe":       False,
        "removed_names": rem,
        "fix_steps": {
            "step_1_direct":     [{"file": f["path"], "risky_lines": f.get("usages",[])} for f in direct],
            "step_2_transitive": [{"file": f["path"], "via": f.get("via")} for f in transitive],
        }
    }
    j = json.dumps(fix_plan, indent=2)
    parsed = json.loads(j)
    assert parsed["dependency"] == "fakehttp"
    assert len(parsed["fix_steps"]["step_1_direct"]) >= 1
    assert len(parsed["fix_steps"]["step_2_transitive"]) >= 1
test("JSON fix plan structure valid", t_json_export)

# 8. Pydantic demo end-to-end
def t_pydantic():
    rid2 = ingest_repo("demo_repos/pydantic_app")
    r2   = simulate_bump(rid2, "pydantic", "2.0.1")
    assert not r2["is_safe"]
    aff2 = get_affected_files(r2["bump_id"])
    labels = {f["path"]: f["label"] for f in aff2}
    assert labels.get("config.py")        == "DIRECT"
    assert labels.get("utils/helpers.py") == "SAFE"
test("pydantic demo blast radius correct", t_pydantic)

print()
passed = sum(1 for r in results if r[0]==PASS)
failed = sum(1 for r in results if r[0]==FAIL)
print(f"{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {len(results)}")
print(f"{'='*50}")
if failed:
    sys.exit(1)
