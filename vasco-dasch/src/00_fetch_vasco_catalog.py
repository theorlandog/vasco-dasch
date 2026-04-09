"""Stage 0: Fetch and validate the VASCO transient catalog.

The VASCO catalog must be obtained manually:

  Full catalog (107,875 sources) — Bruehl & Villarroel (2025):
    1. Go to: https://doi.org/10.1038/s41598-025-21620-3
    2. Download supplementary data tables (RA/Dec of transients)
    3. Save as: data/vasco_catalog/full_107k.csv

  Vetted subset (5,399 sources) — Solano et al. (2022):
    1. Go to: https://doi.org/10.1093/mnras/stac1909
    2. Download supplementary table or request from Spanish VO
    3. Save as: data/vasco_catalog/vetted_5399.csv

  Required columns: source_id, ra (deg J2000), dec (deg J2000)
  Optional: utc_date, mag_r

This script:
  - Validates any catalog files that are present
  - Normalizes column names
  - Generates a synthetic 200-source test dataset if neither catalog exists
    (so the pipeline can be developed and tested end-to-end)
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

CATALOG_DIR = Path(__file__).parent.parent / "data" / "vasco_catalog"
VETTED_PATH = CATALOG_DIR / "vetted_5399.csv"
FULL_PATH = CATALOG_DIR / "full_107k.csv"
TEST_PATH = CATALOG_DIR / "test_200.csv"

# Column name aliases → canonical names
RA_ALIASES = {"ra", "ra_deg", "_raj2000", "raj2000", "ra_j2000", "right_ascension"}
DEC_ALIASES = {"dec", "dec_deg", "_dej2000", "dej2000", "de", "dec_j2000", "declination"}
DATE_ALIASES = {"utc_date", "date", "obs_date", "utc_time", "epoch"}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in RA_ALIASES and "ra" not in rename.values():
            rename[col] = "ra"
        elif cl in DEC_ALIASES and "dec" not in rename.values():
            rename[col] = "dec"
        elif cl in DATE_ALIASES and "utc_date" not in rename.values():
            rename[col] = "utc_date"
    return df.rename(columns=rename)


def validate(path: Path, name: str) -> pd.DataFrame | None:
    if not path.exists():
        print(f"  {name}: not found")
        return None
    df = pd.read_csv(path)
    df = normalize_columns(df)
    print(f"  {name}: {len(df)} rows, columns: {list(df.columns)}")

    if "ra" not in df.columns or "dec" not in df.columns:
        print(f"  ERROR: could not identify ra/dec columns. Available: {list(df.columns)}")
        return None

    bad_ra = ~df["ra"].between(0, 360)
    bad_dec = ~df["dec"].between(-90, 90)
    if bad_ra.any() or bad_dec.any():
        print(f"  WARNING: {bad_ra.sum()} bad RA, {bad_dec.sum()} bad Dec values — dropping")
        df = df[~bad_ra & ~bad_dec]

    if "source_id" not in df.columns:
        prefix = name.split("_")[0]
        df.insert(0, "source_id", [f"{prefix}_{i:07d}" for i in range(len(df))])

    print(f"  RA range : {df['ra'].min():.3f} – {df['ra'].max():.3f}")
    print(f"  Dec range: {df['dec'].min():.3f} – {df['dec'].max():.3f}")
    return df


def generate_test_catalog(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic VASCO-like sources for pipeline testing.

    Uses realistic POSS-I sky coverage: RA 0-360, Dec -33 to +90,
    avoiding the galactic plane.
    """
    rng = np.random.default_rng(seed)
    rows = []
    while len(rows) < n:
        ra = rng.uniform(0, 360)
        dec = rng.uniform(-33, 90)
        # Rough galactic plane exclusion (|b| > 15 deg)
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        c = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
        if abs(c.galactic.b.deg) < 15:
            continue
        # Random date in POSS-I survey window
        jd_start = 2433285.5  # 1949-11-19
        jd_end = 2436029.5    # 1957-04-28
        jd = rng.uniform(jd_start, jd_end)
        from astropy.time import Time
        t = Time(jd, format="jd")
        rows.append({
            "source_id": f"test_{len(rows):07d}",
            "ra": round(ra, 6),
            "dec": round(dec, 6),
            "utc_date": t.iso.split()[0],
        })
    return pd.DataFrame(rows[:n])


def main():
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Stage 0: VASCO Catalog Validation ===\n")
    print("Checking catalog files:")
    df_vetted = validate(VETTED_PATH, "vetted_5399")
    df_full = validate(FULL_PATH, "full_107k")

    if df_vetted is not None:
        df_vetted.to_csv(VETTED_PATH, index=False)
        print(f"\nVetted catalog ready: {len(df_vetted)} sources")
    if df_full is not None:
        df_full.to_csv(FULL_PATH, index=False)
        print(f"Full catalog ready: {len(df_full)} sources")

    if df_vetted is None and df_full is None:
        print("\nNo catalog found. Generating 200-source synthetic test catalog...")
        df_test = generate_test_catalog(200)
        df_test.to_csv(TEST_PATH, index=False)
        print(f"Test catalog written: {TEST_PATH}")
        print(f"  {len(df_test)} synthetic sources across POSS-I sky area")
        print("\nNOTE: Use test_200.csv for pipeline development.")
        print("Replace with real catalog files before science runs.")

    print("\nStage 0 complete.")


if __name__ == "__main__":
    main()
