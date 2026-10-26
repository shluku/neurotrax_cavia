"""Verified, lightweight project knowledge graph for the Streamlit dashboard."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).parent

NODES = [
    {"id": "raw", "label": "Raw sensor data", "layer": "Data", "kind": "dataset", "detail": "Source tables: accelerometer, rotation, gyroscope, gravity, plus phone interaction tables."},
    {"id": "backup", "label": "Motion backup", "layer": "Data", "kind": "pipeline", "detail": "Verified SQL/Zstandard chunks copied to the external drive with resumable two-worker extraction."},
    {"id": "features", "label": "Feature catalog", "layer": "Features", "kind": "dataset", "detail": "Patient-level digital behavior and sensor-derived features used in downstream analyses."},
    {"id": "keyboard", "label": "Keyboard analysis", "layer": "Features", "kind": "analysis", "detail": "Keyboard timing, completion time, inter-event intervals, and T1–T2 change features."},
    {"id": "acc", "label": "Accelerometer features", "layer": "Features", "kind": "analysis", "detail": "Movement feature pilots and the patient-sequential extraction pipeline."},
    {"id": "pca_global", "label": "Global PCA / clustering", "layer": "Analysis", "kind": "analysis", "detail": "41-feature representation; PC1+PC2 explain about 59% of variation; exploratory two-cluster interaction-intensity pattern."},
    {"id": "pca_domains", "label": "Domain-specific PCA", "layer": "Analysis", "kind": "analysis", "detail": "Separate feature panels for global, memory, executive function, processing speed, attention, and motor outcomes."},
    {"id": "validation", "label": "Coverage & technical audit", "layer": "Validation", "kind": "validation", "detail": "Checks missingness, table coverage, collection intensity, stability, and sensitivity to technical confounding."},
    {"id": "cognition", "label": "Cognitive outcomes", "layer": "Outcomes", "kind": "outcome", "detail": "T1 scores and T2−T1 changes used for post-hoc interpretation; never used in the original unsupervised PCA."},
    {"id": "manuscript", "label": "Manuscript / evidence", "layer": "Outputs", "kind": "output", "detail": "Protocol, evidence register, analysis decisions, figures, and manuscript text."},
]

EDGES = [
    ("raw", "backup", "archived as"), ("raw", "features", "summarized into"),
    ("backup", "features", "supports later extraction"), ("features", "keyboard", "contains"),
    ("features", "acc", "contains"), ("features", "pca_global", "feeds"),
    ("features", "pca_domains", "feeds"), ("pca_global", "validation", "audited by"),
    ("pca_domains", "validation", "audited by"), ("pca_global", "cognition", "overlaid after fitting"),
    ("pca_domains", "cognition", "compared after fitting"), ("validation", "manuscript", "documents limits"),
    ("pca_global", "manuscript", "supports results"), ("pca_domains", "manuscript", "supports results"),
]

COLORS = {"Data": "#2563eb", "Features": "#059669", "Analysis": "#7c3aed", "Validation": "#d97706", "Outcomes": "#dc2626", "Outputs": "#475569"}
X = {"Data": 0, "Features": 1, "Analysis": 2, "Validation": 3, "Outcomes": 3, "Outputs": 4}


def knowledge_graph_page() -> None:
    st.title("Project Knowledge Graph")
    st.caption("Verified relationships across the project pipeline. Use the filters to follow data from raw tables to analyses and manuscript evidence.")
    query = st.text_input("Search nodes", placeholder="Try: PCA, keyboard, accelerometer, validation")
    layers = st.multiselect("Visible layers", list(COLORS), default=list(COLORS))
    visible = [n for n in NODES if n["layer"] in layers and (not query or query.lower() in (n["label"] + " " + n["detail"]).lower())]
    visible_ids = {n["id"] for n in visible}
    if query and not visible:
        st.info("No matching nodes.")
        return
    positions = {}
    by_layer = {}
    for node in visible:
        by_layer.setdefault(node["layer"], []).append(node)
    for layer, nodes in by_layer.items():
        for row, node in enumerate(nodes):
            positions[node["id"]] = (X[layer], row - (len(nodes) - 1) / 2)
    fig = go.Figure()
    for source, target, relation in EDGES:
        if source not in visible_ids or target not in visible_ids:
            continue
        x0, y0 = positions[source]; x1, y1 = positions[target]
        fig.add_trace(go.Scatter(x=[x0, x1, None], y=[y0, y1, None], mode="lines", line={"color": "#cbd5e1", "width": 1.5}, hoverinfo="text", text=relation, showlegend=False))
    fig.add_trace(go.Scatter(
        x=[positions[n["id"]][0] for n in visible], y=[positions[n["id"]][1] for n in visible],
        mode="markers+text", text=[n["label"] for n in visible], textposition="middle center",
        marker={"size": 52, "color": [COLORS[n["layer"]] for n in visible], "line": {"color": "white", "width": 2}},
        customdata=[[n["id"], n["detail"]] for n in visible], hovertemplate="<b>%{text}</b><br>%{customdata[1]}<extra></extra>", showlegend=False,
    ))
    fig.update_layout(height=560, margin={"l": 20, "r": 20, "t": 20, "b": 20}, plot_bgcolor="white", paper_bgcolor="white", xaxis={"visible": False, "range": [-0.5, 4.5]}, yaxis={"visible": False}, hovermode="closest")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    choices = {n["label"]: n for n in visible}
    if choices:
        selected = st.selectbox("Inspect a node", list(choices))
        node = choices[selected]
        st.info(node["detail"])
        related = [f"{relation} **{next(n['label'] for n in NODES if n['id'] == target)}**" for source, target, relation in EDGES if source == node["id"]]
        related += [f"{relation} **{next(n['label'] for n in NODES if n['id'] == source)}**" for source, target, relation in EDGES if target == node["id"]]
        if related:
            st.markdown("**Connections:** " + " · ".join(related))
    st.caption("The graph is deliberately curated from project protocols and outputs; AI-suggested links can be added later for review.")
