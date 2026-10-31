"""
Blast Radius — Streamlit web app.

Imports seven functions from service.py. If the service layer isn't available
(missing MongoDB config or engine not yet built) the app falls back to demo
mode using synthetic data so the UI is always functional.
"""

import streamlit as st

# ── Service layer ──────────────────────────────────────────────────────────────
# Seven functions the UI calls. Replace the demo stubs below once service.py
# is implemented.
try:
    from blast.core.service import (
        ingest_repo,
        list_repos,
        simulate_bump,
        get_affected_files,
        get_fix_order,
        get_api_diff,
        get_bump_history,
    )
    DEMO_MODE = False
except Exception:
    DEMO_MODE = True

    # ── Demo stubs ─────────────────────────────────────────────────────────────
    def ingest_repo(path: str) -> str:
        return "demo-repo-001"

    def list_repos() -> list:
        return [{"repo_id": "demo-repo-001", "path": "/sample_repo"}]

    def simulate_bump(repo_id: str, dep: str, version: str) -> dict:
        return {
            "bump_id": "demo-bump-001",
            "repo_id": repo_id,
            "dep": dep,
            "target_version": version,
            "is_safe": False,
        }

    def get_affected_files(bump_id: str) -> list:
        return [
            {"path": "api/client.py",  "label": "DIRECT"},
            {"path": "utils/retry.py", "label": "DIRECT"},
            {"path": "main.py",        "label": "TRANSITIVE"},
            {"path": "api/auth.py",    "label": "TRANSITIVE"},
            {"path": "models/user.py", "label": "SAFE"},
        ]

    def get_fix_order(bump_id: str) -> list:
        return ["api/client.py", "utils/retry.py", "main.py", "api/auth.py"]

    def get_api_diff(dep: str, from_ver: str, to_ver: str) -> list:
        return ["delete", "HTTPError"]

    def get_bump_history(repo_id: str, dep: str) -> list:
        return [
            {"target_version": "2.0", "is_safe": False,
             "affected_count": 4, "ran_at": "2026-10-31T10:00:00Z"},
        ]


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Blast Radius",
    page_icon="💥",
    layout="wide",
)

st.title("💥 Blast Radius")
st.caption("How far does a dependency bump ripple through your codebase?")

if DEMO_MODE:
    st.warning(
        "⚠️ **Demo mode** — no MongoDB connection detected. "
        "Add `MONGO_URI` to `.streamlit/secrets.toml` to use real data.",
        icon="🔌",
    )

# ── Sidebar: Ingest ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Ingest a repo")
    repo_path = st.text_input("Repo folder path", placeholder="/path/to/your/repo")
    if st.button("Ingest", use_container_width=True):
        if repo_path:
            with st.spinner("Parsing imports…"):
                try:
                    rid = ingest_repo(repo_path)
                    st.success(f"Ingested — repo ID: `{rid}`")
                except Exception as exc:
                    st.error(f"Ingest failed: {exc}")
        else:
            st.warning("Enter a path first.")

    st.divider()
    st.header("Known repos")
    repos = list_repos()
    if repos:
        for r in repos:
            st.code(r["path"], language=None)
    else:
        st.caption("No repos ingested yet.")

# ── Main: Simulate bump ────────────────────────────────────────────────────────
st.header("Simulate a version bump")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    dep_name = st.text_input("Dependency", value="fakehttp")
with col2:
    target_ver = st.text_input("Target version", value="2.0")
with col3:
    repo_options = {r["path"]: r["repo_id"] for r in list_repos()}
    selected_path = st.selectbox("Repo", options=list(repo_options.keys()))

if st.button("Simulate bump 💥", type="primary", use_container_width=True):
    repo_id = repo_options.get(selected_path, "demo-repo-001")
    with st.spinner("Running blast radius…"):
        try:
            result = simulate_bump(repo_id, dep_name, target_ver)
            bump_id = result["bump_id"]

            affected = get_affected_files(bump_id)
            fix_order = get_fix_order(bump_id)
            removed_names = get_api_diff(dep_name, "1.0", target_ver)

            # ── Safety banner ─────────────────────────────────────────────────
            if result["is_safe"]:
                st.success("✅ SAFE TO BUMP — no files affected.")
            else:
                st.error(
                    f"🚨 **DO NOT BUMP YET** — {len([f for f in affected if f['label'] != 'SAFE'])} "
                    f"file(s) need updating before you can safely upgrade to {dep_name}=={target_ver}."
                )

            # ── Affected files table ──────────────────────────────────────────
            st.subheader("Affected files")
            label_colours = {"DIRECT": "🔴", "TRANSITIVE": "🟡", "SAFE": "🟢"}
            rows = [
                {"File": f["path"], "Impact": f"{label_colours.get(f['label'], '')} {f['label']}"}
                for f in affected
            ]
            st.table(rows)

            # ── Fix order ─────────────────────────────────────────────────────
            if fix_order:
                st.subheader("Fix order (bottom-up)")
                for i, path in enumerate(fix_order, 1):
                    st.markdown(f"`{i}.` `{path}`")

            # ── API diff ──────────────────────────────────────────────────────
            if removed_names:
                st.subheader(f"Names removed in {dep_name} {target_ver}")
                st.code(", ".join(removed_names), language=None)

            # ── History ───────────────────────────────────────────────────────
            history = get_bump_history(repo_id, dep_name)
            if len(history) > 1:
                prev = history[1]  # second-most-recent
                if not prev["is_safe"]:
                    st.warning(
                        f"⚠️ Last time you tried this bump ({prev['ran_at'][:10]}) "
                        f"it was also unsafe with {prev['affected_count']} affected file(s)."
                    )

        except Exception as exc:
            st.error(f"Simulation failed: {exc}")

# ── History panel ──────────────────────────────────────────────────────────────
with st.expander("📜 Bump history"):
    try:
        repo_id = repo_options.get(selected_path, "demo-repo-001")
        history = get_bump_history(repo_id, dep_name if "dep_name" in dir() else "fakehttp")
        if history:
            st.table(history)
        else:
            st.caption("No history yet. Run a simulation first.")
    except Exception:
        st.caption("History unavailable.")
