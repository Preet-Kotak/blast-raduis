"""Debug helper: inspect stored edges and files for a dep. Run from blast-radius/ folder."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.db import edges_col, files_col

dep = sys.argv[1] if len(sys.argv) > 1 else "pydantic"
print(f"Checking dep: {dep}")

edge = edges_col().find_one({"dep": dep})
print(f"Edge: {edge}")

f = files_col().find_one({"deps": dep})
if f:
    print(f"File: { {k:v for k,v in f.items() if k in ('path','deps','pinned_versions','repo_root')} }")
