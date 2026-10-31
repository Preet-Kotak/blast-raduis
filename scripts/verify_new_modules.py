"""Verify new modules import and work correctly."""
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for f in ["app.py", "blast/core/graph_viz.py", "blast/core/migration_hints.py"]:
    with open(f, encoding="utf-8") as fh:
        src = fh.read()
    ast.parse(src)
    print(f"  syntax OK: {f}")

from blast.core.graph_viz import build_graph_html
from blast.core.migration_hints import get_hints_for_file, get_unique_hints
print("  imports OK: graph_viz, migration_hints")

hints = get_unique_hints("pydantic", ["BaseSettings", "validator", "ConstrainedStr"])
assert all("hint" in h for h in hints)
assert hints[0]["hint"] != "Removed in this version — check the library's migration guide for a replacement."
print(f"  hints OK: {[h['name'] for h in hints]}")

# Test graph builds without error
fake_affected = [
    {"path": "api/client.py",  "label": "DIRECT",     "via": None,            "usages": [{"line": 4, "name": "delete", "snippet": "fakehttp.delete(url)"}]},
    {"path": "main.py",        "label": "TRANSITIVE",  "via": "api/client.py", "usages": []},
    {"path": "models/user.py", "label": "SAFE",         "via": None,            "usages": []},
]
html = build_graph_html(fake_affected, "fakehttp", "2.0")
assert "<html>" in html or "<!DOCTYPE" in html.lower() or "pyvis" in html.lower() or "vis" in html
print(f"  graph_viz OK: generated {len(html)} chars of HTML")

print("\nAll new module checks passed.")
