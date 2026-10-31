"""
Blast Radius — Streamlit web app.

Shows how far a dependency bump ripples through a Python codebase.
One-click demos + test your own repo.
"""

import os
import streamlit as st
import streamlit.components.v1 as components

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
        scan_requirements,
    )
    from blast.core.graph_viz import build_graph_image
    from blast.core.migration_hints import get_hints_for_file, get_unique_hints
    DEMO_MODE = False
except Exception:
    DEMO_MODE = True

    def ingest_repo(path): return "demo-repo-001"
    def list_repos(): return [{"repo_id": "demo-repo-001", "path": "demo_repos/fakehttp_app", "file_count": 9}]
    def simulate_bump(repo_id, dep, version): return {"bump_id": "demo-bump-001", "repo_id": repo_id, "dep": dep, "target_version": version, "is_safe": False}
    def get_affected_files(bump_id): return [
        {"path": "api/client.py",  "label": "DIRECT",     "via": None,            "usages": [{"line": 11, "name": "delete",           "snippet": "return fakehttp.delete(url)"}]},
        {"path": "utils/retry.py", "label": "DIRECT",     "via": None,            "usages": [{"line": 10, "name": "HTTPError",         "snippet": "except fakehttp.HTTPError as exc:"}]},
        {"path": "main.py",        "label": "TRANSITIVE", "via": "api/client.py", "usages": []},
        {"path": "api/auth.py",    "label": "TRANSITIVE", "via": "api/client.py", "usages": []},
        {"path": "models/user.py", "label": "SAFE",        "via": None,            "usages": []},
        {"path": "api/__init__.py","label": "SAFE",        "via": None,            "usages": []},
    ]
    def get_fix_order(bump_id): return ["api/client.py", "utils/retry.py", "main.py", "api/auth.py"]
    def get_api_diff(dep, f, t): return ["delete", "HTTPError"]
    def get_bump_history(repo_id, dep): return [{"target_version": "2.0", "is_safe": False, "affected_count": 4, "ran_at": "2026-10-31T10:00:00Z"}]
    def get_package_versions(dep): return []
    def build_graph_image(affected, dep, ver, repo_id=""):
        import io, os
        import matplotlib.pyplot as plt
        import networkx as nx
        matplotlib_imported = False
        try:
            import matplotlib
            matplotlib.use("Agg")
            matplotlib_imported = True
        except:
            pass
        
        if not matplotlib_imported:
            return b""
        
        G = nx.DiGraph()
        dep_label = f"{dep}=={ver}"
        G.add_node(dep_label, node_type="DEP")
        for f in affected:
            G.add_node(f["path"], node_type=f["label"])
            if f["label"] == "DIRECT":
                G.add_edge(f["path"], dep_label)
            elif f["label"] == "TRANSITIVE" and f.get("via"):
                G.add_edge(f["path"], f["via"])
        
        fig, ax = plt.subplots(figsize=(14, 8), facecolor="#0f172a")
        pos = nx.spring_layout(G, seed=42, k=2.0)
        colors = {"DIRECT": "#ef4444", "TRANSITIVE": "#f59e0b", "SAFE": "#22c55e", "DEP": "#3b82f6"}
        node_colors = [colors.get(G.nodes[n].get("node_type"), "#64748b") for n in G.nodes()]
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1500, edgecolors="white", linewidths=2)
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#475569", width=1.5, arrows=True, arrowsize=15)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_color="#e2e8f0")
        ax.set_facecolor("#0f172a")
        ax.axis("off")
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    def get_hints_for_file(pkg, usages): return [{**u, "hint": "Check migration guide.", "first_occurrence": True} for u in usages]
    def get_unique_hints(pkg, names): return [{"name": n, "hint": "Check migration guide."} for n in names]
    def scan_requirements(repo_id, repo_path): return [
        {"dep": "pydantic",  "current_ver": "1.10.0", "latest_ver": "2.14.2", "is_latest": False, "affected": 9,  "direct": 4, "transitive": 5, "risk": "HIGH",      "bump_id": "demo-bump-001"},
        {"dep": "fastapi",   "current_ver": "0.95.0", "latest_ver": "0.115.0","is_latest": False, "affected": 2,  "direct": 1, "transitive": 1, "risk": "MEDIUM",    "bump_id": "demo-bump-002"},
        {"dep": "uvicorn",   "current_ver": "0.21.0", "latest_ver": "0.32.0", "is_latest": False, "affected": 0,  "direct": 0, "transitive": 0, "risk": "SAFE",      "bump_id": None},
        {"dep": "requests",  "current_ver": "2.28.0", "latest_ver": "2.28.0", "is_latest": True,  "affected": 0,  "direct": 0, "transitive": 0, "risk": "UP TO DATE","bump_id": None},
    ]


# ── Demo repo config ───────────────────────────────────────────────────────────
DEMOS = [
    {
        "key":        "fakehttp",
        "title":      "Fakehttp 1.0 → 2.0",
        "desc":       "A toy HTTP library with 2 removed names: `delete` and `HTTPError`. Clear, fast, educational.",
        "repo_path":  os.path.join(os.path.dirname(__file__), "demo_repos", "fakehttp_app"),
        "dep":        "fakehttp",
        "from_ver":   "1.0",
        "to_ver":     "2.0",
        "pypi":       False,
    },
    {
        "key":        "pydantic",
        "title":      "Pydantic 1.10 → 2.0.1",
        "desc":       "Real PyPI package. 27 removed names including `BaseSettings`, `validator`, `ConstrainedStr`. A FastAPI app breaks hard.",
        "repo_path":  os.path.join(os.path.dirname(__file__), "demo_repos", "pydantic_app"),
        "dep":        "pydantic",
        "from_ver":   "1.10.0",
        "to_ver":     "2.0.1",
        "pypi":       True,
    },
    {
        "key":        "discordpy",
        "title":      "Discord.py 1.7 → 2.0",
        "desc":       "Discord bot migration. Breaking changes in event handlers, intents, and cog structure.",
        "repo_path":  os.path.join(os.path.dirname(__file__), "discord_bot"),
        "dep":        "discord.py",
        "from_ver":   "1.7.3",
        "to_ver":     "2.0.0",
        "pypi":       True,
    },
    {
        "key":        "fastapi",
        "title":      "FastAPI 0.95 → 0.115",
        "desc":       "Web framework update with changes in dependency injection, middleware, and response handling.",
        "repo_path":  os.path.join(os.path.dirname(__file__), "demo_repos", "pydantic_app"),
        "dep":        "fastapi",
        "from_ver":   "0.95.0",
        "to_ver":     "0.115.0",
        "pypi":       True,
    },
]


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Blast Radius",
    page_icon="💥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Hide sidebar completely ─────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Ensure all cards have consistent sizing */
div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div > div {
    gap: 0.5rem;
}

.metric-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 0.5rem;
    border-left: 4px solid #3b82f6;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    min-height: 100%;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 12px -1px rgba(59, 130, 246, 0.2);
}

/* Equal height columns */
.equal-height-row {
    display: flex;
    flex-direction: row;
    gap: 1rem;
    margin-bottom: 1rem;
}

.equal-height-row > div {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.feature-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 0;
    border: 1px solid rgba(59, 130, 246, 0.2);
    box-shadow: 0 4px 20px -1px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.feature-card:hover {
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 8px 30px -1px rgba(59, 130, 246, 0.15);
    transform: translateY(-4px);
}

/* Demo cards with equal height */
.demo-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid rgba(59, 130, 246, 0.2);
    margin-bottom: 0;
    transition: all 0.3s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 180px;
}

.demo-card:hover {
    border-color: rgba(59, 130, 246, 0.5);
    box-shadow: 0 4px 20px -1px rgba(59, 130, 246, 0.2);
}

/* Test your repo card */
.test-your-repo-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
    border-radius: 20px;
    padding: 2.5rem;
    margin: 2rem 0;
    border: 2px solid #3b82f6;
    box-shadow: 0 0 40px -10px rgba(59, 130, 246, 0.4);
}

.hint-box {
    background: linear-gradient(90deg, #0f2537 0%, #1e3a5f 100%);
    border-left: 3px solid #3b82f6;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-top: 0.5rem;
}

.badge-direct     { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color:white; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:500; }
.badge-transitive { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color:white; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:500; }
.badge-safe       { background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); color:white; padding:4px 12px; border-radius:6px; font-size:0.85rem; font-weight:500; }

.hero-title {
    font-size: 4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
}

.hero-subtitle {
    font-size: 1.5rem;
    color: #94a3b8;
    font-weight: 400;
    margin-bottom: 2rem;
}

.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
    border-radius: 50%;
    color: white;
    font-weight: 600;
    margin-right: 12px;
    font-size: 0.9rem;
}

/* Stat boxes with equal size */
.stat-box {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    border: 1px solid rgba(59, 130, 246, 0.2);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 80px;
}

.icon-feature {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

/* Result boxes with equal height */
.result-box {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    border: 1px solid rgba(59, 130, 246, 0.2);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

/* Graph container */
.graph-container {
    background: #0f172a;
    border-radius: 16px;
    padding: 1rem;
    margin: 1rem 0;
    border: 1px solid rgba(59, 130, 246, 0.2);
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "result"       not in st.session_state: st.session_state.result       = None
if "affected"     not in st.session_state: st.session_state.affected     = []
if "fix_order"    not in st.session_state: st.session_state.fix_order    = []
if "removed"      not in st.session_state: st.session_state.removed      = []
if "dep_name"     not in st.session_state: st.session_state.dep_name     = ""
if "from_ver"     not in st.session_state: st.session_state.from_ver     = ""
if "repo_id"      not in st.session_state: st.session_state.repo_id      = ""
if "scan_results" not in st.session_state: st.session_state.scan_results = None
if "show_results" not in st.session_state: st.session_state.show_results = False


def run_simulation(repo_path, dep, from_ver, to_ver):
    """Ingest + simulate + store results in session state."""
    with st.spinner(f"Ingesting `{os.path.basename(repo_path)}`…"):
        repo_id = ingest_repo(repo_path)
    with st.spinner(f"Running blast radius for `{dep}` → `{to_ver}`…"):
        result    = simulate_bump(repo_id, dep, to_ver)
        affected  = get_affected_files(result["bump_id"])
        fix_order = get_fix_order(result["bump_id"])
        removed   = get_api_diff(dep, from_ver, to_ver)
    st.session_state.result    = result
    st.session_state.affected  = affected
    st.session_state.fix_order = fix_order
    st.session_state.removed   = removed
    st.session_state.dep_name  = dep
    st.session_state.from_ver  = from_ver
    st.session_state.repo_id   = repo_id
    st.session_state.show_results = True
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE - NO SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.result is None or not st.session_state.show_results:
    # ── Hero Section ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 3rem 0;'>
        <h1 class='hero-title'>💥 Blast Radius</h1>
        <p class='hero-subtitle'>How far does a dependency bump ripple through your codebase?</p>
    </div>
    """, unsafe_allow_html=True)

    if DEMO_MODE:
        st.warning("⚠️ **Demo mode** — MongoDB not connected. Add `MONGO_URI` to `.streamlit/secrets.toml`.", icon="🔌")

    # ── Quick Stats Row ────────────────────────────────────────────────────────
    st.markdown("<div class='equal-height-row'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""<div class="stat-box"><h3 style="margin:0; color:#3b82f6;">🔍</h3><p style="margin:0.5rem 0 0 0; color:#94a3b8; font-size:0.9rem;">AST Parsing</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="stat-box"><h3 style="margin:0; color:#8b5cf6;">📡</h3><p style="margin:0.5rem 0 0 0; color:#94a3b8; font-size:0.9rem;">PyPI Diffing</p></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="stat-box"><h3 style="margin:0; color:#ec4899;">📊</h3><p style="margin:0.5rem 0 0 0; color:#94a3b8; font-size:0.9rem;">Risk Analysis</p></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""<div class="stat-box"><h3 style="margin:0; color:#f59e0b;">🗺️</h3><p style="margin:0.5rem 0 0 0; color:#94a3b8; font-size:0.9rem;">Visual Graph</p></div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feature Cards ───────────────────────────────────────────────────────────
    st.markdown("### 🚀 How It Works")
    
    # Feature 1
    st.markdown("""
    <div class="feature-card" style="border-left: 4px solid #3b82f6;">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="font-size: 2rem;">🔍</div>
            <div style="flex: 1;">
                <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">1. Import Graph Analysis</h4>
                <p style="margin:0; color:#94a3b8; font-size:0.95rem; line-height:1.6;">
                    Parses every <code>.py</code> file using Python's <code>ast</code> module — <strong>no code execution needed</strong>. 
                    Builds a directed import graph stored in MongoDB, capturing which files depend on which packages.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Feature 2
    st.markdown("""
    <div class="feature-card" style="border-left: 4px solid #8b5cf6;">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="font-size: 2rem;">📡</div>
            <div style="flex: 1;">
                <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">2. Real PyPI Version Diffing</h4>
                <p style="margin:0; color:#94a3b8; font-size:0.95rem; line-height:1.6;">
                    Downloads actual package wheels from PyPI for any two versions. 
                    AST-parses the public API surface and finds exactly <strong>which names were removed</strong>.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Feature 3
    st.markdown("""
    <div class="feature-card" style="border-left: 4px solid #ec4899;">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="font-size: 2rem;">💥</div>
            <div style="flex: 1;">
                <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">3. Blast Radius Simulation</h4>
                <p style="margin:0; color:#94a3b8; font-size:0.95rem; line-height:1.6;">
                    Uses MongoDB <code>$graphLookup</code> to find <strong>every affected file</strong> — direct and transitive.
                    Shows exact line numbers, migration hints, and the order to fix files.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick Demos Section ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚡ Quick Demos")
    st.markdown("<p style='color:#94a3b8; margin-bottom:1.5rem;'>One-click demos with pre-loaded repositories — no setup required!</p>", unsafe_allow_html=True)

    # Row 1 of demos
    demo_col1, demo_col2 = st.columns(2)

    with demo_col1:
        demo = DEMOS[0]
        st.markdown(f"""
        <div class="demo-card">
            <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">🔴 {demo['title']}</h4>
            <p style="margin:0; color:#94a3b8; font-size:0.85rem; line-height:1.4;">{demo['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Run Demo", key=f"demo_{demo['key']}", use_container_width=True):
            if not os.path.exists(demo["repo_path"]):
                st.error(f"Demo repo not found: {demo['repo_path']}")
            else:
                run_simulation(demo["repo_path"], demo["dep"], demo["from_ver"], demo["to_ver"])

    with demo_col2:
        demo = DEMOS[1]
        st.markdown(f"""
        <div class="demo-card">
            <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">🐍 {demo['title']}</h4>
            <p style="margin:0; color:#94a3b8; font-size:0.85rem; line-height:1.4;">{demo['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Run Demo", key=f"demo_{demo['key']}", use_container_width=True):
            if not os.path.exists(demo["repo_path"]):
                st.error(f"Demo repo not found: {demo['repo_path']}")
            else:
                run_simulation(demo["repo_path"], demo["dep"], demo["from_ver"], demo["to_ver"])

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Row 2 of demos
    demo_col3, demo_col4 = st.columns(2)

    with demo_col3:
        demo = DEMOS[2]
        st.markdown(f"""
        <div class="demo-card">
            <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">🤖 {demo['title']}</h4>
            <p style="margin:0; color:#94a3b8; font-size:0.85rem; line-height:1.4;">{demo['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Run Demo", key=f"demo_{demo['key']}", use_container_width=True):
            if not os.path.exists(demo["repo_path"]):
                st.error(f"Demo repo not found: {demo['repo_path']}")
            else:
                run_simulation(demo["repo_path"], demo["dep"], demo["from_ver"], demo["to_ver"])

    with demo_col4:
        demo = DEMOS[3]
        st.markdown(f"""
        <div class="demo-card">
            <h4 style="margin:0 0 0.5rem 0; color:#e2e8f0;">⚡ {demo['title']}</h4>
            <p style="margin:0; color:#94a3b8; font-size:0.85rem; line-height:1.4;">{demo['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Run Demo", key=f"demo_{demo['key']}", use_container_width=True):
            if not os.path.exists(demo["repo_path"]):
                st.error(f"Demo repo not found: {demo['repo_path']}")
            else:
                run_simulation(demo["repo_path"], demo["dep"], demo["from_ver"], demo["to_ver"])

    # ── How Results Look Section ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 What You'll Get")
    
    st.markdown("<div class='equal-height-row'>", unsafe_allow_html=True)
    result_col1, result_col2, result_col3 = st.columns(3)
    with result_col1:
        st.markdown("""
        <div class="result-box" style='border-left:4px solid #3b82f6;'>
            <h4 style='margin:0 0 1rem 0; color:#e2e8f0;'>📋 Affected Files</h4>
            <ul style='color:#94a3b8; font-size:0.9rem; line-height:2; padding-left: 1.2rem; margin:0;'>
                <li><span class='badge-direct'>DIRECT</span> Imports removed names</li>
                <li><span class='badge-transitive'>TRANSITIVE</span> Depends on affected</li>
                <li><span class='badge-safe'>SAFE</span> No dependency path</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with result_col2:
        st.markdown("""
        <div class="result-box" style='border-left:4px solid #8b5cf6;'>
            <h4 style='margin:0 0 1rem 0; color:#e2e8f0;'>🗺️ Dependency Graph</h4>
            <ul style='color:#94a3b8; font-size:0.9rem; line-height:2; padding-left: 1.2rem; margin:0;'>
                <li>Visual blast radius</li>
                <li>Hierarchical layout</li>
                <li>Color-coded risk levels</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with result_col3:
        st.markdown("""
        <div class="result-box" style='border-left:4px solid #ec4899;'>
            <h4 style='margin:0 0 1rem 0; color:#e2e8f0;'>🔧 Fix Order</h4>
            <ul style='color:#94a3b8; font-size:0.9rem; line-height:2; padding-left: 1.2rem; margin:0;'>
                <li>Step-by-step guide</li>
                <li>Migration hints</li>
                <li>Downloadable plan</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Test Your Own Repo Section (just above footer) ──────────────────────────
    st.markdown("---")
    st.markdown("""
    <div class="test-your-repo-card">
        <h2 style="margin:0 0 1.5rem 0; color:#e2e8f0; text-align:center;">🧪 Test Your Own Repository</h2>
    </div>
    """, unsafe_allow_html=True)

    col_path, col_dep = st.columns(2)
    with col_path:
        repo_path_input = st.text_input(
            "📁 Repository Path",
            placeholder="C:/path/to/your/repo",
            help="Enter the full path to your Python repository"
        )
    with col_dep:
        dep_input = st.text_input(
            "📦 Dependency Name",
            placeholder="e.g., requests, pydantic, fastapi",
            help="Enter the PyPI package name"
        )

    col_ver1, col_ver2 = st.columns(2)
    with col_ver1:
        fver_input = st.text_input(
            "Current Version",
            placeholder="e.g., 2.27.0",
            help="The version you currently have installed"
        )
    with col_ver2:
        # Try to fetch available versions
        all_versions = get_package_versions(dep_input) if dep_input else []
        if all_versions:
            to_ver_input = st.selectbox(
                "Target Version",
                all_versions[:20],
                help="Select the version you want to upgrade to"
            )
            if len(all_versions) > 20:
                st.caption(f"Showing 20 of {len(all_versions)} available versions")
        else:
            to_ver_input = st.text_input(
                "Target Version",
                placeholder="e.g., 2.31.0",
                help="The version you want to upgrade to"
            )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("💥 Run Blast Radius Analysis", type="primary", use_container_width=True):
            if not repo_path_input:
                st.warning("⚠️ Please enter a repository path or GitHub URL")
            elif not dep_input:
                st.warning("⚠️ Please enter a dependency name")
            elif not to_ver_input:
                st.warning("⚠️ Please enter a target version")
            else:
                # Handle GitHub URLs
                actual_path = repo_path_input
                if repo_path_input.startswith("http"):
                    st.info("📥 Cloning GitHub repository...")
                    import subprocess
                    import hashlib
                    
                    try:
                        # Use a persistent cache directory
                        cache_dir = os.path.join(os.path.expanduser("~"), ".blast_radius_cache")
                        os.makedirs(cache_dir, exist_ok=True)
                        
                        # Hash the URL to create a unique directory name
                        url_hash = hashlib.md5(repo_path_input.encode()).hexdigest()[:8]
                        clone_path = os.path.join(cache_dir, url_hash)
                        
                        # Clone if not already cached
                        if not os.path.exists(clone_path):
                            subprocess.run(
                                ["git", "clone", repo_path_input, clone_path],
                                check=True,
                                capture_output=True,
                                timeout=30
                            )
                        else:
                            st.caption("✅ Using cached repository")
                        
                        actual_path = clone_path
                        run_simulation(actual_path, dep_input, fver_input or "unknown", to_ver_input)
                    except subprocess.TimeoutExpired:
                        st.error("❌ Clone timeout (>30s) - repo too large")
                    except subprocess.CalledProcessError as e:
                        st.error(f"❌ Failed to clone repo: {e.stderr.decode() if e.stderr else str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                elif not os.path.exists(repo_path_input):
                    st.error(f"❌ Repository not found: `{repo_path_input}`")
                else:
                    run_simulation(actual_path, dep_input, fver_input or "unknown", to_ver_input)

    # ── Footer ──────────────────────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0; border-top: 1px solid #334155;'>
        <p style='color:#64748b; font-size:0.85rem; margin:0;'>
            Built with ❤️ using Python AST, MongoDB, and Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)

else:
    result    = st.session_state.result
    affected  = st.session_state.affected
    fix_order = st.session_state.fix_order
    removed   = st.session_state.removed
    dep_name  = st.session_state.dep_name
    from_ver  = st.session_state.from_ver
    repo_id   = st.session_state.repo_id

    direct     = [f for f in affected if f["label"] == "DIRECT"]
    transitive = [f for f in affected if f["label"] == "TRANSITIVE"]
    safe       = [f for f in affected if f["label"] == "SAFE"]
    unsafe_count = len(direct) + len(transitive)

    # ── Header for results page ────────────────────────────────────────────────
    if st.button("", help="Click to go home"):
        st.session_state.result = None
        st.session_state.show_results = False
        st.rerun()
    
    st.markdown("""
    <div style='padding: 1rem 0 1.5rem 0; border-bottom: 1px solid #334155; margin-bottom: 1.5rem;'>
        <h1 style="margin:0; font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; cursor: pointer;">
            💥 Blast Radius
        </h1>
    </div>
    """, unsafe_allow_html=True)

    # ── Top action bar ─────────────────────────────────────────────────────────
    top_left, top_right = st.columns([6, 1])
    with top_left:
        st.markdown(
            f"**{dep_name}** `{from_ver}` → `{result['target_version']}`  ·  "
            f"repo: `{os.path.basename(st.session_state.get('repo_id',''))}`"
        )
    with top_right:
        if st.button("🔄 New simulation", use_container_width=True):
            for key in ["result","affected","fix_order","removed","dep_name","from_ver","repo_id","show_results"]:
                if key == "result":
                    st.session_state[key] = None
                elif key == "show_results":
                    st.session_state[key] = False
                elif key in ["affected", "fix_order", "removed"]:
                    st.session_state[key] = []
                else:
                    st.session_state[key] = ""
            st.rerun()

    # ── Banner ─────────────────────────────────────────────────────────────────
    if result["is_safe"]:
        st.success(f"✅ **SAFE TO BUMP** — no files affected by `{dep_name}=={result['target_version']}`.")
    else:
        st.error(
            f"🚨 **DO NOT BUMP YET** — **{unsafe_count} file(s)** need fixing before "
            f"upgrading to **{dep_name}=={result['target_version']}**."
        )

    # ── Summary metrics ────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 Direct",      len(direct))
    m2.metric("🟡 Transitive",  len(transitive))
    m3.metric("🟢 Safe",        len(safe))
    m4.metric("🔧 Files to fix", len(fix_order))

    # ── Removed API names ──────────────────────────────────────────────────────
    if removed:
        st.markdown(
            f"**Removed in `{dep_name}` {result['target_version']}:** " +
            "  ".join(f"`{n}`" for n in removed[:12]) +
            (f"  *+{len(removed)-12} more*" if len(removed) > 12 else "")
        )

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab_files, tab_order, tab_dash, tab_history = st.tabs(
        ["📋 Affected Files", "🔧 Fix Order", "📊 Risk Dashboard", "📜 History"]
    )

    # ── TAB 1: Affected files + Graph ──────────────────────────────────────────
    with tab_files:
        # Graph at the top of affected files
        if affected:
            st.subheader("🗺️ Import Graph")
            st.caption(
                "🔴 Direct  🟡 Transitive  🟢 Safe  🔵 Dependency node"
            )
            try:
                graph_img = build_graph_image(affected, dep_name, result["target_version"], repo_id)
                if graph_img:
                    st.image(graph_img, caption="Dependency blast radius — import dependency graph")
                else:
                    st.info("Graph unavailable in demo mode.")
            except Exception as e:
                st.warning(f"Graph generation failed: {str(e)}")
        # DIRECT
        if direct:
            st.subheader(f"🔴 Direct — {len(direct)} file(s)")
            st.caption("These files import the dependency and call removed names. Fix these first.")
            for f in direct:
                usages = get_hints_for_file(dep_name, f.get("usages", []))
                badge  = f"**{len(usages)} risky line(s)**" if usages else "_imports dep, no removed-name calls detected_"
                with st.expander(f"`{f['path']}`  ·  {badge}", expanded=True):
                    if usages:
                        for u in usages:
                            c_line, c_name, c_code = st.columns([1, 2, 5])
                            c_line.markdown(f"**line {u['line']}**")
                            c_name.markdown(f"`{u['name']}`")
                            c_code.code(u["snippet"], language="python")
                            if u.get("first_occurrence"):
                                st.markdown(
                                    f'<div class="hint-box">💡 <b>Fix:</b> {u["hint"]}</div>',
                                    unsafe_allow_html=True,
                                )
                    else:
                        st.caption("Imports the dep but no removed-name calls found. Review manually.")

        # TRANSITIVE
        if transitive:
            st.subheader(f"🟡 Transitive — {len(transitive)} file(s)")
            st.caption("These files don't use the dep directly but import something that does.")
            rows = [{"File": f["path"], "Broken because it imports": f.get("via") or "—"} for f in transitive]
            st.table(rows)

        # SAFE
        if safe:
            safe_paths = ", ".join(f"`{f['path']}`" for f in safe)
            with st.expander(f"🟢 Safe — {len(safe)} file(s) (no path to `{dep_name}`)", expanded=False):
                st.markdown(safe_paths)

    # ── TAB 2: Fix order ───────────────────────────────────────────────────────
    with tab_order:
        st.subheader("Fix order")
        st.caption(
            "Fix **DIRECT** files first — they are the root cause. "
            "Once they're updated, fix **TRANSITIVE** files that depend on them."
        )

        if fix_order:
            # ── JSON export ───────────────────────────────────────────────────
            import json
            fix_plan = {
                "dependency":      dep_name,
                "from_version":    from_ver,
                "to_version":      result["target_version"],
                "is_safe":         result["is_safe"],
                "removed_names":   removed,
                "fix_steps": {
                    "step_1_direct": [
                        {
                            "file": f["path"],
                            "risky_lines": [
                                {
                                    "line":    u["line"],
                                    "name":    u["name"],
                                    "snippet": u["snippet"],
                                    "fix":     get_unique_hints(dep_name, [u["name"]])[0]["hint"],
                                }
                                for u in f.get("usages", [])
                            ]
                        }
                        for f in direct
                    ],
                    "step_2_transitive": [
                        {"file": f["path"], "via": f.get("via")}
                        for f in transitive
                    ],
                }
            }
            json_str = json.dumps(fix_plan, indent=2)
            col_guide, col_json = st.columns([3, 1])
            with col_json:
                st.download_button(
                    label="⬇️ Download fix plan (.json)",
                    data=json_str,
                    file_name=f"blast_radius_{dep_name}_{result['target_version']}.json",
                    mime="application/json",
                    use_container_width=True,
                )
                st.code(json_str[:300] + "\n...", language="json")

            with col_guide:
                # Migration summary
                hints = get_unique_hints(dep_name, removed)
                if hints:
                    with st.expander(f"📖 Migration guide — `{dep_name}` {from_ver} → {result['target_version']}", expanded=True):
                        for h in hints:
                            st.markdown(f"- **`{h['name']}`** — {h['hint']}")

            st.markdown("---")

            # DIRECT first, then TRANSITIVE
            direct_order     = [p for p in fix_order if next((f for f in affected if f["path"]==p), {}).get("label") == "DIRECT"]
            transitive_order = [p for p in fix_order if next((f for f in affected if f["path"]==p), {}).get("label") == "TRANSITIVE"]

            if direct_order:
                st.markdown("#### 🔴 Step 1 — Fix these direct files (root cause)")
                for i, path in enumerate(direct_order, 1):
                    f_data = next((f for f in affected if f["path"] == path), {})
                    usages = f_data.get("usages", [])
                    st.markdown(f"**{i}.** `{path}`")
                    for u in usages[:3]:
                        hint = get_unique_hints(dep_name, [u["name"]])[0]["hint"]
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ line **{u['line']}** `{u['name']}` — *{hint}*")

            if transitive_order:
                st.markdown("#### 🟡 Step 2 — Update these transitive files (after step 1)")
                for i, path in enumerate(transitive_order, 1):
                    f_data = next((f for f in affected if f["path"] == path), {})
                    via = f_data.get("via", "?")
                    st.markdown(f"**{i}.** `{path}` — *imports `{via}` which was changed above*")
        else:
            st.success("Nothing to fix — bump is safe!")

    # ── TAB 3: Risk Dashboard ──────────────────────────────────────────────────
    with tab_dash:
        st.subheader("📊 Full requirements risk dashboard")
        st.caption(
            "Scans every dependency in `requirements.txt`, checks the latest stable "
            "version on PyPI, and runs blast radius for each one automatically."
        )

        # Find repo_path from stored repo_root
        repo_path_for_scan = None
        try:
            from blast.core.db import files_col
            doc = files_col().find_one({"repo_id": repo_id}, {"repo_root": 1})
            if doc:
                repo_path_for_scan = doc.get("repo_root")
        except Exception:
            pass

        # Also try demo repos
        if not repo_path_for_scan:
            for demo in DEMOS:
                if os.path.exists(demo["repo_path"]):
                    demo_rid = None
                    try:
                        from blast.core.db import files_col as fc
                        d = fc().find_one({"repo_root": demo["repo_path"]}, {"repo_id": 1})
                        if d:
                            demo_rid = d["repo_id"]
                    except Exception:
                        pass
                    if demo_rid == repo_id:
                        repo_path_for_scan = demo["repo_path"]
                        break

        if st.button("🔍 Scan all requirements", type="primary", use_container_width=False):
            if not repo_path_for_scan:
                st.warning("Cannot find repo path — try re-ingesting the repo.")
            else:
                req_file = os.path.join(repo_path_for_scan, "requirements.txt")
                if not os.path.exists(req_file):
                    st.warning(f"No `requirements.txt` found in `{repo_path_for_scan}`.")
                else:
                    with st.spinner("Scanning all dependencies against latest PyPI versions…"):
                        scan_results = scan_requirements(repo_id, repo_path_for_scan)
                    st.session_state["scan_results"] = scan_results


        scan_results = st.session_state.get("scan_results")
        if scan_results:
            risk_icons = {
                "HIGH":       "🔴",
                "MEDIUM":     "🟡",
                "LOW":        "🟠",
                "SAFE":       "🟢",
                "UP TO DATE": "✅",
                "UNKNOWN":    "⚪",
                "ERROR":      "❌",
            }
            # Summary counts
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("🔴 High risk",    sum(1 for r in scan_results if r["risk"]=="HIGH"))
            sc2.metric("🟡 Medium risk",  sum(1 for r in scan_results if r["risk"]=="MEDIUM"))
            sc3.metric("🟢 Safe to bump", sum(1 for r in scan_results if r["risk"] in ("SAFE","UP TO DATE")))
            sc4.metric("📦 Total deps",   len(scan_results))

            st.markdown("---")

            # Table
            for r in scan_results:
                icon  = risk_icons.get(r["risk"], "⚪")
                col_dep, col_cur, col_lat, col_aff, col_risk, col_btn = st.columns([2,1,1,1,1,2])
                col_dep.markdown(f"**`{r['dep']}`**")
                col_cur.markdown(f"`{r['current_ver']}`")
                col_lat.markdown(f"`{r['latest_ver']}`")
                col_aff.markdown(f"{r['affected']} files" if r["affected"] else "—")
                col_risk.markdown(f"{icon} **{r['risk']}**")
                if r.get("bump_id"):
                    if col_btn.button(f"View details", key=f"dash_{r['dep']}", use_container_width=True):
                        # Load this bump's results into main view
                        aff2  = get_affected_files(r["bump_id"])
                        ord2  = get_fix_order(r["bump_id"])
                        rem2  = get_api_diff(r["dep"], r["current_ver"], r["latest_ver"])
                        st.session_state.affected  = aff2
                        st.session_state.fix_order = ord2
                        st.session_state.removed   = rem2
                        st.session_state.dep_name  = r["dep"]
                        st.session_state.from_ver  = r["current_ver"]
                        st.session_state.result    = {
                            "bump_id": r["bump_id"], "repo_id": repo_id,
                            "dep": r["dep"], "target_version": r["latest_ver"],
                            "is_safe": r["affected"] == 0,
                        }
                        st.rerun()
                else:
                    col_btn.markdown("—")
        else:
            st.info("Click **Scan all requirements** to see a risk summary for every dependency in this repo.")

    with tab_history:
        st.subheader(f"Bump history — `{dep_name}` on this repo")
        try:
            history = get_bump_history(repo_id, dep_name)
            if history:
                if len(history) > 1 and not history[1]["is_safe"]:
                    prev = history[1]
                    st.warning(
                        f"⚠️ Previous attempt on {prev['ran_at'][:10]} was also unsafe "
                        f"({prev['affected_count']} file(s) affected)."
                    )
                st.table([
                    {
                        "Version": h["target_version"],
                        "Safe?":   "✅ Yes" if h["is_safe"] else "🚨 No",
                        "Affected": h["affected_count"],
                        "Run at":  h["ran_at"][:19].replace("T", " "),
                    }
                    for h in history
                ])
            else:
                st.caption("No history yet.")
        except Exception:
            st.caption("History unavailable.")
