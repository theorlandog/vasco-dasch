"""Stage 9: Generate publication-quality figures.

Figures produced:
  fig1_sky_coverage.png    — VASCO positions + Harvard plate coverage map
  fig2_coverage_hist.png   — Histogram of plates per VASCO source (1949-1957)
  fig3_flag_summary.png    — Pie/bar chart of classification flags
  fig4_lc_examples.png     — Example lightcurves (detection + non-detection)
  fig5_stat_results.png    — Summary table of statistical test results

Output: data/results/figures/

Usage:
    poetry run python src/09_generate_figures.py
"""

import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.database import get_conn

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"
FIG_DIR = RESULTS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Journal-quality settings
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def fig1_sky_coverage():
    """Sky map of VASCO positions colored by Harvard coverage."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ra, dec, n_window FROM plate_coverage"
        ).fetchall()

    if not rows:
        print("  fig1: no data")
        return

    ra = np.array([r["ra"] for r in rows])
    dec = np.array([r["dec"] for r in rows])
    n_window = np.array([r["n_window"] for r in rows])

    fig, ax = plt.subplots(figsize=(10, 5))
    # Wrap RA to [-180, 180]
    ra_plot = np.where(ra > 180, ra - 360, ra)

    has_cov = n_window > 0
    sc = ax.scatter(ra_plot[has_cov], dec[has_cov], c=n_window[has_cov],
                    cmap="viridis", s=4, alpha=0.7, label="Has Harvard coverage")
    ax.scatter(ra_plot[~has_cov], dec[~has_cov], c="lightgray", s=2,
               alpha=0.3, label="No coverage")

    cb = plt.colorbar(sc, ax=ax, pad=0.02)
    cb.set_label("Harvard plates in 1949–1957")
    ax.set_xlabel("RA (deg, J2000)")
    ax.set_ylabel("Dec (deg, J2000)")
    ax.set_title("VASCO Transient Positions — Harvard DASCH Plate Coverage")
    ax.legend(markerscale=3, loc="lower right")
    ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_sky_coverage.png")
    plt.close(fig)
    print(f"  fig1: saved ({has_cov.sum()} sources with coverage)")


def fig2_coverage_histogram():
    """Histogram of number of Harvard plates per VASCO source."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT n_window FROM plate_coverage WHERE n_window > 0"
        ).fetchall()

    if not rows:
        print("  fig2: no data")
        return

    n_plates = [r["n_window"] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(n_plates, bins=min(50, max(n_plates)), color="steelblue",
            edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Harvard plates in 1949–1957 window per VASCO position")
    ax.set_ylabel("Number of VASCO sources")
    ax.set_title("Harvard Plate Coverage Distribution")
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_coverage_hist.png")
    plt.close(fig)
    print(f"  fig2: saved ({len(n_plates)} sources with coverage)")


def fig3_classification():
    """Bar chart of classification flag counts."""
    cands_csv = RESULTS_DIR / "candidates.csv"
    if not cands_csv.exists():
        print("  fig3: candidates.csv not found")
        return

    df = pd.read_csv(cands_csv)
    counts = df["flag"].value_counts()

    colors = {
        "SINGLE_DETECTION": "crimson",
        "MULTI_DETECTION": "steelblue",
        "NO_DETECTION": "lightgray",
        "NO_LIGHTCURVE": "orange",
    }

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(
        counts.index,
        counts.values,
        color=[colors.get(k, "gray") for k in counts.index],
        edgecolor="black", linewidth=0.8,
    )
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(v), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Number of VASCO sources")
    ax.set_title("VASCO Source Classification on Harvard Plates")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_classification.png")
    plt.close(fig)
    print(f"  fig3: saved")


def fig5_stats_table():
    """Table figure summarizing statistical test results."""
    stats_json = RESULTS_DIR / "statistical_tests.json"
    if not stats_json.exists():
        print("  fig5: statistical_tests.json not found")
        return

    results = json.loads(stats_json.read_text())
    rows = []
    for key, res in results.items():
        if "error" in res:
            rows.append([key, "—", "—", "SKIPPED"])
        else:
            p = res.get("p_value", "—")
            sig = "Yes" if res.get("significant") else "No"
            summary = res.get("rate_ratio", res.get("z_score", "—"))
            rows.append([key, f"{p:.4f}", str(round(summary, 3)), sig])

    fig, ax = plt.subplots(figsize=(9, 3))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["Test", "p-value", "Effect size", "Significant?"],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)
    ax.set_title("Statistical Test Summary", pad=20)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_stats_table.png")
    plt.close(fig)
    print(f"  fig5: saved")


def main():
    print("=== Stage 9: Generating Figures ===\n")
    fig1_sky_coverage()
    fig2_coverage_histogram()
    fig3_classification()
    fig5_stats_table()
    print(f"\nFigures saved to {FIG_DIR}")


if __name__ == "__main__":
    main()
