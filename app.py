"""
Blast Radius — Streamlit web app.

Imports seven functions from service.py. Falls back to demo mode with
synthetic data if MongoDB is not configured.
"""

import streamlit as st

# ── Service layer ──────────────────────────────────────────────────────────────
try:
    from blast.core.service import (
        ingest_repo,
        list_repos,
        simulate_bump,
        get_affected_files,
        get_fix_order,
        get_api_diff,
        get_bump_history,
        get_package_versions,
    )
    DEMO_MODE = False
except Exception:
    DEMO_MODE = True

    def ingest_repo(path: str) -> str:
        return "demo-repo-001"

    def list_repos() -> list:
        return [{"repo_id": "demo-repo-001", "path": "sample_repo"}]

    def simulate_bump(repo_id: str, dep: str, version: str) -> dict:
        return {"bump_id": "demo-bump-001", "repo_id": repo_id,
                "dep": dep, "target_version": version, "is_safe": False}

    def get_affected_files(bump_id: str) -> list:
        return [
            {"path": "api/client.py",  "label": "DIRECT", "via": None,
             "usages": [{"line": 11, "name": "delete",    "snippet": "return fakehttp.delete(url)"}]},
            {"path": "utils/retry.py", "label": "DIRECT", "via": None,
             "usages": [{"line": 10, "name": "HTTPError", "snippet": "except fakehttp.HTTPError as exc:"}]},
            {"path": "main.py",        "label": "TRANSITIVE", "via": "api/client.py",  "usages": []},
            {"path": "api/auth.py",    "label": "TRANSITIVE", "via": "api/client.py",  "usages": []},
            {"path": "models/user.py", "label": "SAFE",       "via": None,             "usages": []},
            {"path": "api/__init__.py","label": "SAFE",       "via": None,             "usages": []},
        ]

    def get_fix_order(bump_id: str) -> list:
        return ["api/client.py", "utils/retry.py", "main.py", "api/auth.py"]

    def get_api_diff(dep: str, from_ver: str, to_ver: str) -> list:
        return ["delete", "HTTPError"]

    def get_bump_history(repo_id: str, dep: str) -> list:
        return [{"target_version": "2.0", "is_safe": False,
                 "affected_count": 4, "ran_at": "2026-10-31T10:00:00Z"}]

    def get_package_versions(dep: str) -> list:
        return []


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Blast Radius", page_icon="💥", layout="wide")

st.title("💥 Blast Radius")
st.caption("How far does a dependency bump ripple through your codebase?")

if DEMO_MODE:
    st.warning(
        "⚠️ **Demo mode** — no MongoDB connection. "
        "Add `MONGO_URI` to `.streamlit/secrets.toml` to use real data.",
        icon="🔌",
    )

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Ingest a repo")
    repo_path = st.text_input("Repo folder path", placeholder="/path/to/repo")
    if st.button("Ingest", use_container_width=True):
        if repo_path:
            with st.spinner("Parsing imports…"):
                try:
                    rid = ingest_repo(repo_path)
                    st.success(f"Done — repo ID: `{rid}`")
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

# ── Simulate form ──────────────────────────────────────────────────────────────
st.header("Simulate a version bump")
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    dep_name = st.text_input("Dependency (PyPI name)", value="discord.py")
with col2:
    from_ver = st.text_input("Current version", value="1.7.3")
with col3:
    repo_options = {r["path"]: r["repo_id"] for r in list_repos()}
    selected_path = st.selectbox("Repo", options=list(repo_options.keys()))

# Version picker — fetch from PyPI
versions = get_package_versions(dep_name) if dep_name else []
if versions:
    target_ver = st.selectbox(
        f"Bump to version  ({len(versions)} available on PyPI)",
        options=versions,
        index=0,
    )
    st.caption(f"🔗 PyPI source — comparing real `{dep_name}` releases")
else:
    target_ver = st.text_input("Target version", value="2.0.0")

if st.button("Simulate bump 💥", type="primary", use_container_width=True):
    repo_id = repo_options.get(selected_path, "demo-repo-001")
    with st.spinner("Running blast radius…"):
        try:
            result    = simulate_bump(repo_id, dep_name, target_ver)
            bump_id   = result["bump_id"]
            affected  = get_affected_files(bump_id)
            fix_order = get_fix_order(bump_id)
            removed   = get_api_diff(dep_name, from_ver, target_ver)

            direct      = [f for f in affected if f["label"] == "DIRECT"]
            transitive  = [f for f in affected if f["label"] == "TRANSITIVE"]
            safe        = [f for f in affected if f["label"] == "SAFE"]
            unsafe_count = len(direct) + len(transitive)

            # ── Banner ────────────────────────────────────────────────────────
            if result["is_safe"]:
                st.success(
                    f"✅ **SAFE TO BUMP** — no files use {dep_name}. "
                    f"Go ahead with {dep_name}=={target_ver}."
                )
            else:
                st.error(
                    f"🚨 **DO NOT BUMP YET** — **{unsafe_count} file(s)** need "
                    f"fixing before upgrading to **{dep_name}=={target_ver}**."
                )

            # ── Removed API names pill ────────────────────────────────────────
            if removed:
                st.markdown(
                    "**Names removed in this version:** "
                    + "  ".join(f"`{n}`" for n in removed)
                )

            st.divider()

            # ── DIRECT ────────────────────────────────────────────────────────
            if direct:
                st.subheader(f"🔴 Direct — {len(direct)} file(s)")
                st.caption("These files import the dep and call removed names. Fix them first.")
                for f in direct:
                    usages = f.get("usages", [])
                    badge = f"**{len(usages)} risky line(s)**" if usages else "_no removed-name calls found_"
                    with st.expander(f"`{f['path']}`  ·  {badge}", expanded=True):
                        if usages:
                            for u in usages:
                                col_line, col_name, col_code = st.columns([1, 2, 7])
                                col_line.markdown(f"**line {u['line']}**")
                                col_name.markdown(f"`{u['name']}`")
                                col_code.code(u["snippet"], language="python")
                        else:
                            st.caption(
                                "Imports the dep but no removed-name calls detected. "
                                "Review manually."
                            )

            # ── TRANSITIVE ────────────────────────────────────────────────────
            if transitive:
                st.subheader(f"🟡 Transitive — {len(transitive)} file(s)")
                st.caption("These files don't use the dep directly but import something that does.")
                rows = []
                for f in transitive:
                    via = f.get("via") or "—"
                    rows.append({"File": f["path"], "Broken because it imports": via})
                st.table(rows)

            # ── SAFE ──────────────────────────────────────────────────────────
            safe_paths = [f["path"] for f in safe]
            if safe_paths:
                with st.expander(f"🟢 Safe — {len(safe_paths)} file(s) (no path to {dep_name})", expanded=False):
                    st.code("\n".join(safe_paths), language=None)

            st.divider()

            # ── Fix order ─────────────────────────────────────────────────────
            if fix_order:
                st.subheader("🔧 Fix order")
                st.caption("Bottom-up: fix leaves first so each file compiles before its dependants.")
                for i, path in enumerate(fix_order, 1):
                    st.markdown(f"**{i}.** `{path}`")

            # ── History warning ───────────────────────────────────────────────
            history = get_bump_history(repo_id, dep_name)
            if len(history) > 1 and not history[1]["is_safe"]:
                prev = history[1]
                st.warning(
                    f"⚠️ Last attempt on {prev['ran_at'][:10]} was also unsafe "
                    f"({prev['affected_count']} file(s) affected)."
                )

        except Exception as exc:
            st.error(f"Simulation failed: {exc}")
            raise

# ── History panel ──────────────────────────────────────────────────────────────
with st.expander("📜 Bump history"):
    try:
        _repo_id = repo_options.get(selected_path, "demo-repo-001")
        history = get_bump_history(_repo_id, dep_name)
        if history:
            st.table(history)
        else:
            st.caption("No history yet — run a simulation first.")
    except Exception:
        st.caption("History unavailable.")
