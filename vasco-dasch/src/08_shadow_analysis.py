"""Stage 8: Earth shadow deficit analysis.

Tests whether VASCO / Harvard transients are deficient in the antisolar
direction (Earth's umbral shadow cone, ~1.4% of sky).

If transients are satellite glints or near-Earth objects, they would be
suppressed in the shadow cone. This is one of the VASCO project's own tests.

Usage:
    poetry run python src/08_shadow_analysis.py
"""

import sys
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from astropy.time import Time
from astropy.coordinates import get_sun, SkyCoord
import astropy.units as u

sys.path.insert(0, str(Path(__file__).parent))
from utils.statistics import earth_shadow_test

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"


def get_solar_elongation(ra_deg: float, dec_deg: float, utc_date: str) -> float | None:
    """Return solar elongation in degrees for a source at a given date."""
    try:
        t = Time(utc_date)
        sun = get_sun(t)
        src = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
        return float(sun.separation(src).deg)
    except Exception:
        return None


def main():
    cands_csv = RESULTS_DIR / "candidates.csv"
    if not cands_csv.exists():
        print("Run Stage 3 first.")
        return

    df = pd.read_csv(cands_csv)
    singles = df[df["flag"] == "SINGLE_DETECTION"].copy()

    print(f"Earth shadow analysis")
    print(f"  Single-detection candidates: {len(singles)}")

    if "utc_date" not in singles.columns:
        print("  No UTC date column — cannot run shadow test.")
        print("  Shadow test requires observation dates in the catalog.")
        return

    singles = singles.dropna(subset=["utc_date"])
    if len(singles) == 0:
        print("  No candidates with observation dates.")
        return

    # Compute solar elongations
    singles["solar_elongation"] = singles.apply(
        lambda r: get_solar_elongation(r["ra"], r["dec"], r["utc_date"]), axis=1
    )
    singles = singles.dropna(subset=["solar_elongation"])
    print(f"  Sources with valid elongations: {len(singles)}")

    if len(singles) == 0:
        print("  Insufficient data for shadow test.")
        return

    # Shadow cone: antisolar direction ± ~0.27 deg (half-angle)
    SHADOW_THRESHOLD = 179.73  # elongation > this → in shadow
    in_shadow = singles["solar_elongation"] > SHADOW_THRESHOLD
    n_shadow = int(in_shadow.sum())
    n_total = len(singles)
    frac_obs = n_shadow / n_total
    frac_exp = 0.014

    print(f"\nShadow cone analysis:")
    print(f"  In shadow: {n_shadow} / {n_total} = {frac_obs:.3f}")
    print(f"  Expected (geometric): {frac_exp:.3f}")

    # Statistical test
    result = earth_shadow_test(
        obs_times_utc=singles["utc_date"].tolist(),
        ra_list=singles["ra"].values,
        dec_list=singles["dec"].values,
    )
    print(f"  Chi-square: {result.get('chi2','?')}, p={result.get('p_value','?')}")
    print(f"  Significant deficit: {result.get('significant',False)}")

    # Save result
    out = RESULTS_DIR / "shadow_analysis.json"
    out.write_text(json.dumps(result, indent=2))

    # Plot elongation distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(singles["solar_elongation"], bins=36, range=(0, 180),
            color="steelblue", edgecolor="white")
    ax.axvline(SHADOW_THRESHOLD, color="red", linestyle="--",
               label=f"Shadow threshold ({SHADOW_THRESHOLD}°)")
    ax.set_xlabel("Solar elongation (degrees)")
    ax.set_ylabel("Number of candidates")
    ax.set_title("Solar Elongation Distribution of Single-Detection Candidates")
    ax.legend()
    fig.tight_layout()

    fig_dir = RESULTS_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / "fig_shadow_elongation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"\nResults saved to {out}")
    print(f"Figure saved to {fig_dir}/fig_shadow_elongation.png")


if __name__ == "__main__":
    main()
