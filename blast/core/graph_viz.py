"""
blast.core.graph_viz — Build graph visualizations from blast radius results.

Colours:
  🔴 Red    — DIRECT (imports removed dep directly)
  🟡 Yellow — TRANSITIVE (reaches dep through imports)
  🟢 Green  — SAFE (no path to dep)
  🔵 Blue   — the dependency node itself
"""

import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx


# Node colours per label
_COLOURS = {
    "DIRECT":      "#ef4444",   # red-500
    "TRANSITIVE":  "#f59e0b",   # amber-500
    "SAFE":        "#22c55e",   # green-500
    "DEP":         "#3b82f6",   # blue-500
}

_BORDER = {
    "DIRECT":      "#b91c1c",
    "TRANSITIVE":  "#b45309",
    "SAFE":        "#15803d",
    "DEP":         "#1d4ed8",
}


def build_graph_image(
    affected: list[dict],
    dep: str,
    target_version: str,
    repo_id: str = "",
) -> bytes:
    """
    Build a static, centered PNG graph image from blast radius results.

    Uses networkx + matplotlib for a reliable, centered, fixed-size render.

    Args:
        affected:       List of affected file dicts (path, label, via, usages).
        dep:            Dependency name (e.g. "pydantic").
        target_version: Target version string.
        repo_id:        Optional repo identifier (unused, kept for API compat).

    Returns:
        PNG image bytes ready for st.image().
    """
    G = nx.DiGraph()

    dep_label = f"{dep}=={target_version}"
    G.add_node(dep_label, node_type="DEP")

    for f in affected:
        path = f["path"]
        label = f["label"]
        short = os.path.basename(path)
        G.add_node(path, node_type=label, short_name=short)

        if label == "DIRECT":
            G.add_edge(path, dep_label, edge_type="direct")
        elif label == "TRANSITIVE" and f.get("via"):
            G.add_edge(path, f["via"], edge_type="transitive")

    # ── Layout: hierarchical top-down ─────────────────────────────────────────
    # Put the dep node at the top, DIRECT below it, TRANSITIVE below those
    try:
        # Try graphviz-like hierarchical layout
        pos = _hierarchical_layout(G, dep_label)
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=2.0)

    # ── Draw ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 8), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    # Collect node colours and sizes
    node_colors = []
    node_sizes = []
    node_edge_colors = []
    labels = {}

    for node in G.nodes():
        ntype = G.nodes[node].get("node_type", "SAFE")
        if ntype == "DEP":
            node_colors.append(_COLOURS["DEP"])
            node_sizes.append(3500)
            node_edge_colors.append(_BORDER["DEP"])
            labels[node] = node
        else:
            node_colors.append(_COLOURS.get(ntype, "#64748b"))
            node_sizes.append(1800)
            node_edge_colors.append(_BORDER.get(ntype, "#334155"))
            labels[node] = G.nodes[node].get("short_name", os.path.basename(node))

    # Collect edge colours
    edge_colors = []
    edge_widths = []
    edge_styles = []
    for u, v in G.edges():
        etype = G.edges[u, v].get("edge_type", "direct")
        if etype == "direct":
            edge_colors.append("#ef4444")
            edge_widths.append(2.0)
            edge_styles.append("solid")
        else:
            edge_colors.append("#f59e0b")
            edge_widths.append(1.2)
            edge_styles.append("dashed")

    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors=node_edge_colors,
        linewidths=2,
    )

    # Draw edges with arrows
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=edge_colors,
        width=edge_widths,
        style=edge_styles,
        arrows=True,
        arrowsize=20,
        connectionstyle="arc3,rad=0.1",
        min_source_margin=25,
        min_target_margin=25,
    )

    # Draw labels
    nx.draw_networkx_labels(
        G, pos, labels=labels, ax=ax,
        font_size=8,
        font_color="#e2e8f0",
        font_family="monospace",
        font_weight="bold",
    )

    # Legend
    legend_items = [
        ("🔵 Dependency", _COLOURS["DEP"]),
        ("🔴 Direct", _COLOURS["DIRECT"]),
        ("🟡 Transitive", _COLOURS["TRANSITIVE"]),
        ("🟢 Safe", _COLOURS["SAFE"]),
    ]
    for i, (label_text, color) in enumerate(legend_items):
        ax.scatter([], [], c=color, s=120, label=label_text, edgecolors="white", linewidths=1)
    ax.legend(loc="lower right", facecolor="#1e293b", edgecolor="#334155",
              labelcolor="#e2e8f0", fontsize=9, framealpha=0.9)

    ax.set_title(
        f"Import Graph — {dep} → {target_version}",
        color="#e2e8f0", fontsize=14, fontweight="bold", pad=15,
    )
    ax.axis("off")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _hierarchical_layout(G: nx.DiGraph, root: str) -> dict:
    """
    Build a top-down hierarchical layout with the dependency at the top.
    DIRECT files in the second layer, TRANSITIVE below them.
    """
    pos = {}
    layers = {}

    # Layer 0: dependency node (top)
    layers[0] = [root]

    # Layer 1: DIRECT files (they connect to dep)
    direct_nodes = [n for n in G.nodes()
                    if G.nodes[n].get("node_type") == "DIRECT"]
    layers[1] = direct_nodes

    # Layer 2: TRANSITIVE files
    transitive_nodes = [n for n in G.nodes()
                        if G.nodes[n].get("node_type") == "TRANSITIVE"]
    layers[2] = transitive_nodes

    # Layer 3: SAFE files (bottom)
    safe_nodes = [n for n in G.nodes()
                  if G.nodes[n].get("node_type") == "SAFE"]
    layers[3] = safe_nodes

    max_layer = max(layers.keys()) if any(layers.values()) else 0

    for layer, nodes in layers.items():
        if not nodes:
            continue
        y = max_layer - layer
        count = len(nodes)
        if count == 1:
            xs = [0.0]
        else:
            spacing = 1.0
            start = -(count - 1) * spacing / 2
            xs = [start + i * spacing for i in range(count)]
        for x, node in zip(xs, nodes):
            pos[node] = (x, y)

    # Handle any nodes not yet positioned
    for node in G.nodes():
        if node not in pos:
            pos[node] = (0, 0)

    return pos
