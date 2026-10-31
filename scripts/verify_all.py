"""Quick verify: graph fix + new modules + CLI syntax."""
import os, sys, ast, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Syntax check
for f in ["app.py", "blast/core/graph_viz.py", "blast/core/migration_hints.py", "cli.py"]:
    with open(f, encoding="utf-8") as fh: src = fh.read()
    ast.parse(src)
    print(f"syntax OK: {f}")

# 2. Graph — check lib/bindings is patched out
from blast.core.graph_viz import build_graph_html
html = build_graph_html([
    {"path": "api/client.py",  "label": "DIRECT",    "via": None,            "usages": [{"line":4,"name":"delete","snippet":"fakehttp.delete(url)"}]},
    {"path": "main.py",        "label": "TRANSITIVE", "via": "api/client.py", "usages": []},
    {"path": "models/user.py", "label": "SAFE",        "via": None,            "usages": []},
], "fakehttp", "2.0")
assert "lib/bindings/utils.js" not in html, "lib/bindings still present — graph will break in Streamlit"
assert "vis-network" in html or "vis.min" in html, "vis.js CDN not found"
assert "api/client.py" in html or "client" in html, "nodes not in HTML"
print(f"graph OK: {len(html)} chars, lib/bindings patched out")

# 3. Migration hints
from blast.core.migration_hints import get_unique_hints, get_hints_for_file
hints = get_unique_hints("pydantic", ["BaseSettings", "validator", "validate_arguments"])
assert all(h["hint"] != "Removed in this version — check the library's migration guide for a replacement." for h in hints[:2])
print(f"migration hints OK: {[h['name'] for h in hints]}")

print("\nAll checks passed.")
