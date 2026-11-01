#!/usr/bin/env python3
"""Create manuscript figures for the frozen top-15 evidence hierarchy."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TOP15 = ROOT / "output/research_summary_20261025/top15_article_statistics_v1"
FIG_DIR = ROOT / "manuscript/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def save_both(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def short_signal(value: str) -> str:
    value = value.replace("keyboard_", "")
    value = value.replace("_median_inter_event_interval_ms", " IEI")
    value = value.replace("_median_correction_recovery_time_ms", " correction recovery")
    value = value.replace("_inter_event_interval_cv", " IEI-CV")
    value = value.replace("_", " ")
    return value


def primary_secondary_forest() -> None:
    df = pd.read_csv(TOP15 / "six_signal_article_ready_table_v1.csv")
    df["label"] = df["feature_name"].map(short_signal) + " → " + df["outcome"].str.replace("_", " ")
    df = df.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(df))

    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.axvline(0, color="#777777", lw=1)
    for i, row in df.iterrows():
        ax.plot(
            [row["discovery_ci_low"], row["discovery_ci_high"]],
            [y[i] + 0.10, y[i] + 0.10],
            color="#4c78a8",
            lw=2,
        )
        ax.scatter(row["discovery_rho"], y[i] + 0.10, color="#4c78a8", s=34, zorder=3, label="Discovery" if i == 0 else None)
        ax.plot(
            [row["recording_adjusted_ci_low"], row["recording_adjusted_ci_high"]],
            [y[i] - 0.10, y[i] - 0.10],
            color="#f58518",
            lw=2,
        )
        ax.scatter(row["recording_adjusted_partial_rho"], y[i] - 0.10, color="#f58518", s=34, zorder=3, label="Recording-adjusted" if i == 0 else None)

    primary = df["label"].str.contains("12 18 IEI") & df["outcome"].eq("executive_function")
    for i in np.flatnonzero(primary.to_numpy()):
        ax.axhspan(i - 0.38, i + 0.38, color="#fff2cc", zorder=0)

    ax.set_yticks(y)
    ax.set_yticklabels(df["label"])
    ax.set_xlabel("Spearman rho / recording-adjusted partial rho")
    ax.set_title("Frozen six-signal keyboard evidence set")
    ax.legend(loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    save_both(fig, "figure_primary_secondary_forest_v1")


def top15_evidence_map() -> None:
    df = pd.read_csv(TOP15 / "top15_article_inferential_audit_v1.csv")
    df["label"] = df["feature"].map(short_signal) + " → " + df["outcome"].str.replace("_", " ")
    df = df.sort_values("estimate").reset_index(drop=True)
    colors = {
        "complete_saved_or_recomputed_descriptives": "#4c78a8",
        "partial_coverage_adjustment": "#f58518",
        "supplementary_exploratory": "#54a24b",
    }
    status = []
    for _, row in df.iterrows():
        if row["feature"] == "keyboard_12_18_median_inter_event_interval_ms" and row["outcome"] == "executive_function":
            status.append("primary")
        elif row["reliability_robustness_evidence"] != "not_saved_for_this_row":
            status.append("secondary")
        else:
            status.append("supplementary")
    df["group"] = status
    group_colors = {"primary": "#e45756", "secondary": "#4c78a8", "supplementary": "#72b7b2"}

    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(11, 8.2))
    ax.axvline(0, color="#777777", lw=1)
    for i, row in df.iterrows():
        color = group_colors[row["group"]]
        ax.plot([row["ci_low_final"], row["ci_high_final"]], [y[i], y[i]], color=color, lw=2)
        ax.scatter(row["estimate"], y[i], color=color, s=38, zorder=3)
        if row["group"] == "primary":
            ax.axhspan(i - 0.42, i + 0.42, color="#fff2cc", zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels(df["label"], fontsize=8.5)
    ax.set_xlabel("Association estimate with 95% confidence interval")
    ax.set_title("Top-15 evidence map: effect estimates and uncertainty")
    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=group_colors["primary"], label="Primary POC", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=group_colors["secondary"], label="Secondary six-signal set", markersize=7),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=group_colors["supplementary"], label="Supplementary exploratory", markersize=7),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    save_both(fig, "figure_top15_evidence_map_v1")


if __name__ == "__main__":
    primary_secondary_forest()
    top15_evidence_map()
    print("Created primary/secondary forest and top-15 evidence map figures.")
