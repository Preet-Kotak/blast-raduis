"""Check graph HTML output is valid and contains vis.js."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blast.core.graph_viz import build_graph_html

fake_affected = [
    {"path": "api/client.py",  "label": "DIRECT",     "via": None,            "usages": [{"line": 11, "name": "delete",    "snippet": "fakehttp.delete(url)"}]},
    {"path": "utils/retry.py", "label": "DIRECT",     "via": None,            "usages": [{"line": 10, "name": "HTTPError", "snippet": "fakehttp.HTTPError"}]},
    {"path": "main.py",        "label": "TRANSITIVE",  "via": "api/client.py", "usages": []},
    {"path": "api/auth.py",    "label": "TRANSITIVE",  "via": "api/client.py", "usages": []},
    {"path": "models/user.py", "label": "SAFE",         "via": None,            "usages": []},
]

html = build_graph_html(fake_affected, "fakehttp", "2.0")
print(f"HTML size: {len(html)} chars")

# Check for vis.js
has_visjs = "vis-network" in html or "visjs" in html or "vis.min.js" in html
print(f"Has vis.js:   {has_visjs}")
print(f"Has <canvas>: {'canvas' in html}")
print(f"Has nodes:    {'api/client.py' in html or 'client' in html}")
print(f"Has edges:    {'edges' in html}")

# Save for manual inspection
with open("graph_test_output.html", "w", encoding="utf-8") as f:
    f.write(html)
print("\nSaved to graph_test_output.html — open in browser to verify visually.")

# Print first 500 chars to see what CDN/script is used
import re
scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
print(f"\nScript sources found: {scripts}")
