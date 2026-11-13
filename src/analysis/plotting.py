"""
Plotting Module for H1: Frozen-Commitment Mechanism.

Generates publication-quality figures comparing FREEZE_OFF vs FREEZE_ON:
  1. Box plot of paired differences per instance
  2. Grouped bar chart of mean distances per instance
  3. Forest plot of rank-biserial effect sizes per instance

All figures are saved as both PNG (300 dpi) and PDF.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analysis.stats_test import (
    load_h1_data,
    wilcoxon_h1_per_instance,
    bonferroni_adjust,
)


# ============================================================
# STYLE DEFAULTS
# ============================================================

_FIGSIZE = (10, 6)
_DPI = 300
_PALETTE = {
    "off": "#1f77b4",   # blue  — FREEZE_OFF
    "on": "#ff7f0e",    # orange — FREEZE_ON
    "diff": "#2ca02c",  # green  — difference
}


def _savefig(fig: plt.Figure, output_dir: Path, name: str) -> None:
    """Save figure as PNG and PDF, creating dirs as needed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{name}.png", dpi=_DPI, bbox_inches="tight")
    fig.savefig(output_dir / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 1. BOX PLOT — PAIRED DIFFERENCES
# ============================================================

def plot_h1_paired_distance(
    csv_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Box plot of D_off − D_on per instance.

    A positive difference means freezing reduced total distance.
    """
    df = load_h1_data(csv_path)
    output_dir = Path(output_dir)
    instances = sorted(df["instance"].unique())

    fig, ax = plt.subplots(figsize=_FIGSIZE)

    data = [df[df["instance"] == inst]["diff"].values for inst in instances]

    bp = ax.boxplot(
        data,
        tick_labels=instances,
        patch_artist=True,
        notch=True,
        showmeans=True,
        meanprops=dict(marker="D", markerfacecolor="red", markersize=6),
    )

    for patch in bp["boxes"]:
        patch.set_facecolor(_PALETTE["diff"])
        patch.set_alpha(0.6)

    ax.axhline(y=0, color="grey", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Instance")
    ax.set_ylabel("Paired Difference (D_off − D_on)")
    ax.set_title("H1: Distribution of Paired Distance Differences per Instance")
    ax.grid(axis="y", alpha=0.3)

    _savefig(fig, output_dir, "h1_paired_differences")
    return output_dir / "h1_paired_differences.png"


# ============================================================
# 2. GROUPED BAR CHART — D_OFF vs D_ON
# ============================================================

def plot_h1_distance_comparison(
    csv_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Grouped bar chart of mean total distance per instance and condition."""
    df = load_h1_data(csv_path)
    output_dir = Path(output_dir)
    instances = sorted(df["instance"].unique())

    means_off = [df[df["instance"] == inst]["D_off"].mean() for inst in instances]
    means_on = [df[df["instance"] == inst]["D_on"].mean() for inst in instances]
    stds_off = [df[df["instance"] == inst]["D_off"].std() for inst in instances]
    stds_on = [df[df["instance"] == inst]["D_on"].std() for inst in instances]

    x = np.arange(len(instances))
    width = 0.35

    fig, ax = plt.subplots(figsize=_FIGSIZE)

    ax.bar(
        x - width / 2,
        means_off,
        width,
        yerr=stds_off,
        label="FREEZE_OFF",
        color=_PALETTE["off"],
        alpha=0.8,
        capsize=4,
    )
    ax.bar(
        x + width / 2,
        means_on,
        width,
        yerr=stds_on,
        label="FREEZE_ON",
        color=_PALETTE["on"],
        alpha=0.8,
        capsize=4,
    )

    ax.set_xlabel("Instance")
    ax.set_ylabel("Mean Total Distance (D)")
    ax.set_title("H1: Distance Comparison — FREEZE_OFF vs FREEZE_ON")
    ax.set_xticks(x)
    ax.set_xticklabels(instances)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    _savefig(fig, output_dir, "h1_distance_comparison")
    return output_dir / "h1_distance_comparison.png"


# ============================================================
# 3. FOREST PLOT — EFFECT SIZE (r_rb)
# ============================================================

def plot_h1_effect_size(
    csv_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Forest plot of rank-biserial correlation (r_rb) per instance.

    Shows per-instance effect size with significance markers.
    """
    df = load_h1_data(csv_path)
    output_dir = Path(output_dir)

    per_instance_raw = wilcoxon_h1_per_instance(df)
    per_instance = bonferroni_adjust(per_instance_raw, k=len(per_instance_raw))

    instances = sorted(per_instance.keys())
    r_rbs = [per_instance[inst]["r_rb"] for inst in instances]
    significants = [per_instance[inst].get("significant", False) for inst in instances]

    fig, ax = plt.subplots(figsize=(_FIGSIZE[0], max(4, len(instances) * 0.8)))

    y_pos = np.arange(len(instances))
    colors = [
        "#2ca02c" if sig else "#d62728" for sig in significants
    ]

    ax.barh(y_pos, r_rbs, color=colors, alpha=0.7, height=0.5)
    ax.axvline(x=0, color="grey", linestyle="--", linewidth=0.8)

    # Mark significance
    for i, (r, sig) in enumerate(zip(r_rbs, significants)):
        label = f"  r={r:.3f}" + (" *" if sig else "")
        ha = "left" if r >= 0 else "right"
        ax.text(r, i, label, va="center", ha=ha, fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(instances)
    ax.set_xlabel("Rank-Biserial Correlation (r_rb)")
    ax.set_title("H1: Effect Size per Instance (Bonferroni-adjusted)")
    ax.set_xlim(-1.1, 1.1)
    ax.grid(axis="x", alpha=0.3)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2ca02c", alpha=0.7, label="Significant (p_adj < .05)"),
        Patch(facecolor="#d62728", alpha=0.7, label="Not significant"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")

    _savefig(fig, output_dir, "h1_effect_size")
    return output_dir / "h1_effect_size.png"
