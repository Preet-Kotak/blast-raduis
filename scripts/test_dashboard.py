"""Test scan_requirements / risk dashboard."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts._mongo_uri import load; load()

from blast.core.service import ingest_repo, scan_requirements

print("Ingesting pydantic demo repo...")
repo_id = ingest_repo("demo_repos/pydantic_app")
print(f"repo_id: {repo_id}")

print("\nScanning requirements...")
results = scan_requirements(repo_id, os.path.abspath("demo_repos/pydantic_app"))

print(f"\n{'Dep':<15} {'Current':<12} {'Latest':<12} {'Affected':<10} {'Risk'}")
print("-" * 65)
for r in results:
    icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟠","SAFE":"🟢","UP TO DATE":"✅","UNKNOWN":"⚪","ERROR":"❌"}.get(r["risk"],"⚪")
    print(f"{r['dep']:<15} {r['current_ver']:<12} {r['latest_ver']:<12} {str(r['affected']):<10} {icon} {r['risk']}")

# Assertions
assert len(results) > 0, "No results returned"
risks = [r["risk"] for r in results]
assert any(r in risks for r in ["HIGH","MEDIUM","LOW","SAFE","UP TO DATE"]), f"No valid risk levels: {risks}"

# pydantic should be HIGH since it has many breaking changes
pydantic_r = next((r for r in results if r["dep"] == "pydantic"), None)
assert pydantic_r is not None, "pydantic not in results"
assert pydantic_r["risk"] in ("HIGH","MEDIUM"), f"pydantic risk should be HIGH/MEDIUM, got {pydantic_r['risk']}"

# Results should be sorted HIGH first
risk_order = {"HIGH":0,"MEDIUM":1,"LOW":2,"SAFE":3,"UP TO DATE":4,"UNKNOWN":5,"ERROR":6}
for i in range(len(results)-1):
    assert risk_order.get(results[i]["risk"],99) <= risk_order.get(results[i+1]["risk"],99), \
        f"Not sorted: {results[i]['risk']} before {results[i+1]['risk']}"

print("\nAll dashboard checks passed.")
