"""Stage 7: Spatial correlation analysis.

Standalone script that runs the spatial correlation test from Stage 6
but with more detailed output and the ability to use custom parameters.

Usage:
    poetry run python src/07_spatial_correlation.py [--radius-arcsec 10] [--n-mc 10000]
"""

import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.statistics import spatial_correlation_mc

RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius-arcsec", type=float, default=10.0)
    parser.add_argument("--n-mc", type=int, default=5000)
    args = parser.parse_args()

    cands_csv = RESULTS_DIR / "candidates.csv"
    if not cands_csv.exists():
        print("Run Stage 3 first.")
        return

    df = pd.read_csv(cands_csv)
    singles = df[df["flag"] == "SINGLE_DETECTION"]

    print(f"Spatial correlation test")
    print(f"  Single-detection candidates: {len(singles)}")
    print(f"  Total VASCO positions: {len(df)}")
    print(f"  Match radius: {args.radius_arcsec} arcsec")
    print(f"  Monte Carlo shuffles: {args.n_mc}")

    if len(singles) == 0:
        print("No single-detection candidates. Cannot run test.")
        return

    result = spatial_correlation_mc(
        test_ra=singles["ra"].values,
        test_dec=singles["dec"].values,
        ref_ra=df["ra"].values,
        ref_dec=df["dec"].values,
        n_mc=args.n_mc,
        radius_arcsec=args.radius_arcsec,
    )

    print(f"\nResults:")
    print(f"  Observed matches: {result['n_obs_matches']}")
    print(f"  MC expected:      {result['mc_mean']:.1f} ± {result['mc_std']:.1f}")
    print(f"  z-score:          {result['z_score']:.3f}")
    print(f"  p-value:          {result['p_value']:.4f}")
    print(f"  Significant:      {result['significant']}")

    if result["significant"]:
        if result["z_score"] > 0:
            print("\nINTERPRETATION: Harvard single detections cluster near VASCO positions")
            print("  → Consistent with VASCO transients being real astrophysical events")
        else:
            print("\nINTERPRETATION: Harvard single detections ANTI-cluster near VASCO positions")
    else:
        print("\nINTERPRETATION: No significant spatial correlation found")
        print("  → Harvard data neither confirms nor refutes VASCO positions")


if __name__ == "__main__":
    main()
