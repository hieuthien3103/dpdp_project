"""
Statistical Testing Module for H1: Frozen-Commitment Mechanism.

Performs one-sided Wilcoxon signed-rank tests on paired (instance, seed)
distance measurements: FREEZE_OFF vs FREEZE_ON.

Expected CSV columns (from run_h1.py):
    instance, seed, freeze_enabled, total_distance_D, ...
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


# ============================================================
# DATA LOADING
# ============================================================

def load_h1_data(csv_path: str | Path) -> pd.DataFrame:
    """Load H1 raw CSV and pivot into paired columns.

    Returns a DataFrame with columns:
        instance, seed, D_off, D_on, diff
    where diff = D_off - D_on  (positive means freeze helped).
    """
    df = pd.read_csv(csv_path)

    # Normalise freeze_enabled to boolean string
    df["freeze_enabled"] = df["freeze_enabled"].astype(str).str.lower()

    off = (
        df[df["freeze_enabled"] == "false"]
        .rename(columns={"total_distance_D": "D_off"})
        [["instance", "seed", "D_off"]]
    )
    on = (
        df[df["freeze_enabled"] == "true"]
        .rename(columns={"total_distance_D": "D_on"})
        [["instance", "seed", "D_on"]]
    )

    paired = pd.merge(off, on, on=["instance", "seed"], how="inner")
    paired["diff"] = paired["D_off"] - paired["D_on"]

    return paired


# ============================================================
# WILCOXON SIGNED-RANK (OVERALL)
# ============================================================

def wilcoxon_h1_overall(df: pd.DataFrame) -> dict[str, Any]:
    """One-sided Wilcoxon signed-rank test over ALL (instance, seed) pairs.

    H1: D_off > D_on  ⇔  diff > 0   (alternative='greater').

    Returns dict with:
        W_plus, W_minus, statistic, p_value, r_rb, n,
        mean_diff, median_diff
    """
    diffs = df["diff"].values

    # Drop zero differences (scipy does this internally, but we want n)
    nonzero = diffs[diffs != 0]
    n = len(nonzero)

    if n == 0:
        return {
            "W_plus": 0.0,
            "W_minus": 0.0,
            "statistic": 0.0,
            "p_value": 1.0,
            "r_rb": 0.0,
            "n": 0,
            "mean_diff": 0.0,
            "median_diff": 0.0,
        }

    result = stats.wilcoxon(
        diffs, zero_method="wilcox", alternative="greater"
    )
    statistic = result.statistic
    p_value = result.pvalue

    # Compute W+ and W- from ranks
    abs_diffs = np.abs(nonzero)
    ranks = stats.rankdata(abs_diffs)
    w_plus = float(np.sum(ranks[nonzero > 0]))
    w_minus = float(np.sum(ranks[nonzero < 0]))

    # Rank-biserial correlation
    denom = w_plus + w_minus
    r_rb = (w_plus - w_minus) / denom if denom > 0 else 0.0

    return {
        "W_plus": w_plus,
        "W_minus": w_minus,
        "statistic": float(statistic),
        "p_value": float(p_value),
        "r_rb": float(r_rb),
        "n": n,
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
    }


# ============================================================
# WILCOXON PER INSTANCE
# ============================================================

def wilcoxon_h1_per_instance(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Run one-sided Wilcoxon per instance.

    Returns dict[instance_name -> test_results].
    """
    results: dict[str, dict[str, Any]] = {}

    for instance, grp in df.groupby("instance"):
        diffs = grp["diff"].values
        nonzero = diffs[diffs != 0]
        n = len(nonzero)

        if n < 2:
            # Not enough non-zero differences for a meaningful test
            results[str(instance)] = {
                "W_plus": 0.0,
                "W_minus": 0.0,
                "statistic": 0.0,
                "p_value": 1.0,
                "r_rb": 0.0,
                "n": n,
                "mean_diff": float(np.mean(diffs)),
                "median_diff": float(np.median(diffs)),
            }
            continue

        res = stats.wilcoxon(diffs, zero_method="wilcox", alternative="greater")

        abs_diffs = np.abs(nonzero)
        ranks = stats.rankdata(abs_diffs)
        w_plus = float(np.sum(ranks[nonzero > 0]))
        w_minus = float(np.sum(ranks[nonzero < 0]))
        denom = w_plus + w_minus
        r_rb = (w_plus - w_minus) / denom if denom > 0 else 0.0

        results[str(instance)] = {
            "W_plus": w_plus,
            "W_minus": w_minus,
            "statistic": float(res.statistic),
            "p_value": float(res.pvalue),
            "r_rb": float(r_rb),
            "n": n,
            "mean_diff": float(np.mean(diffs)),
            "median_diff": float(np.median(diffs)),
        }

    return results


# ============================================================
# BONFERRONI CORRECTION
# ============================================================

def bonferroni_adjust(
    per_instance_results: dict[str, dict[str, Any]],
    k: int = 6,
) -> dict[str, dict[str, Any]]:
    """Apply Bonferroni correction to per-instance p-values.

    Adds 'p_adjusted' and 'significant' keys to each result.
    """
    adjusted: dict[str, dict[str, Any]] = {}

    for instance, res in per_instance_results.items():
        entry = dict(res)
        p_adj = min(res["p_value"] * k, 1.0)
        entry["p_adjusted"] = p_adj
        entry["significant"] = p_adj < 0.05
        adjusted[instance] = entry

    return adjusted


# ============================================================
# FORMATTING
# ============================================================

def format_h1_results(
    overall: dict[str, Any],
    per_instance: dict[str, dict[str, Any]],
) -> str:
    """Format all H1 results as a human-readable report string."""
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("H1 FROZEN-COMMITMENT — WILCOXON SIGNED-RANK TEST RESULTS")
    lines.append("=" * 70)
    lines.append("")

    # Overall
    lines.append("OVERALL (all instances pooled)")
    lines.append("-" * 40)
    lines.append(f"  n (non-zero diffs) : {overall['n']}")
    lines.append(f"  W+                 : {overall['W_plus']:.1f}")
    lines.append(f"  W-                 : {overall['W_minus']:.1f}")
    lines.append(f"  Test statistic     : {overall['statistic']:.1f}")
    lines.append(f"  p-value (one-sided): {overall['p_value']:.6f}")
    lines.append(f"  r_rb (effect size) : {overall['r_rb']:.4f}")
    lines.append(f"  Mean diff (off-on) : {overall['mean_diff']:.4f}")
    lines.append(f"  Median diff        : {overall['median_diff']:.4f}")
    sig = "YES" if overall["p_value"] < 0.05 else "NO"
    lines.append(f"  Significant (α=.05): {sig}")
    lines.append("")

    # Per instance
    lines.append("PER-INSTANCE (Bonferroni-adjusted, k=6)")
    lines.append("-" * 70)
    header = (
        f"{'Instance':<12} {'n':>4} {'W+':>8} {'W-':>8} "
        f"{'p':>10} {'p_adj':>10} {'r_rb':>8} {'Sig?':>5}"
    )
    lines.append(header)
    lines.append("-" * 70)

    for inst in sorted(per_instance):
        r = per_instance[inst]
        sig_flag = "*" if r.get("significant", False) else ""
        lines.append(
            f"{inst:<12} {r['n']:>4} {r['W_plus']:>8.1f} {r['W_minus']:>8.1f} "
            f"{r['p_value']:>10.6f} {r.get('p_adjusted', r['p_value']):>10.6f} "
            f"{r['r_rb']:>8.4f} {sig_flag:>5}"
        )

    lines.append("-" * 70)
    lines.append("")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    """CLI entry point: python -m src.analysis.stats_test [csv_path]."""
    # Default CSV path relative to project root
    project_root = Path(__file__).resolve().parents[2]
    default_csv = project_root / "results" / "raw" / "h1_raw.csv"

    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv

    if not csv_path.is_file():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        print("Run the H1 experiment first to generate results.", file=sys.stderr)
        return 1

    # Load and analyse
    df = load_h1_data(csv_path)

    print(f"Loaded {len(df)} paired observations from {csv_path.name}")
    print(f"Instances: {sorted(df['instance'].unique())}")
    print()

    overall = wilcoxon_h1_overall(df)
    per_instance_raw = wilcoxon_h1_per_instance(df)
    per_instance = bonferroni_adjust(per_instance_raw, k=len(per_instance_raw))

    report = format_h1_results(overall, per_instance)
    print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
