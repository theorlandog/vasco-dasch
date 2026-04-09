"""Stage 2: Retrieve DASCH lightcurves for sources with plate coverage.

For each VASCO source that has Harvard plate coverage in 1949-1957:
  1. Query the APASS reference catalog to find the nearest known source
  2. Retrieve the full DASCH lightcurve using the refcat identifiers

Results stored in SQLite:
  - refcat_lookup: refcat IDs for each position
  - lightcurves: full lightcurve data as JSON

Usage:
    poetry run python src/02_retrieve_lightcurves.py
"""

import sys
import yaml
import math
import pandas as pd
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from utils.dasch_api import DASCHClient, parse_csv_response
from utils.database import (
    init_db, get_positions_with_window_coverage,
    refcat_already_queried, save_refcat,
    lightcurve_already_queried, save_lightcurve,
    get_refcat_for_lightcurve,
)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def angular_sep_arcsec(ra1, dec1, ra2, dec2) -> float:
    """Great-circle separation in arcseconds."""
    d2r = math.pi / 180
    dra = (ra2 - ra1) * d2r
    d1 = dec1 * d2r
    d2 = dec2 * d2r
    a = math.sin(dra / 2) ** 2 + math.cos(d1) * math.cos(d2) * math.sin(
        (d2 - d1) / 2
    ) ** 2
    return 2 * math.asin(min(1, math.sqrt(a))) * (180 / math.pi) * 3600


def find_nearest_refcat(rows: list[dict], ra: float, dec: float) -> dict | None:
    """Find nearest refcat source to (ra, dec); return the row dict."""
    if not rows:
        return None
    best = None
    best_sep = float("inf")
    for r in rows:
        try:
            r_ra = float(r["ra_deg"])
            r_dec = float(r["dec_deg"])
            sep = angular_sep_arcsec(ra, dec, r_ra, r_dec)
            if sep < best_sep:
                best_sep = sep
                best = r
                best["_sep_arcsec"] = sep
        except (KeyError, ValueError):
            continue
    return best


def main():
    cfg = load_config()
    radius = cfg["pipeline"]["search_radius_arcsec"]
    refcat = cfg["pipeline"].get("refcat", "apass")

    init_db()
    client = DASCHClient()

    # Step 1: refcat lookup for all positions with window coverage
    positions = get_positions_with_window_coverage()
    print(f"Stage 2a: Refcat lookup for {len(positions)} positions with coverage")

    n_found = 0
    n_not_found = 0
    n_errors = 0

    with tqdm(total=len(positions), desc="Refcat lookup", unit="src") as pbar:
        for vasco_id, ra, dec in positions:
            if refcat_already_queried(vasco_id):
                pbar.update(1)
                continue
            try:
                raw = client.query_refcat(ra_deg=ra, dec_deg=dec,
                                          radius_arcsec=radius, refcat=refcat)
                rows = parse_csv_response(raw) if isinstance(raw, list) else []
                nearest = find_nearest_refcat(rows, ra, dec)
                if nearest:
                    save_refcat(
                        vasco_id, ra, dec,
                        gsc_bin_index=int(nearest["gsc_bin_index"]),
                        ref_number=int(nearest["ref_number"]),
                        sep_arcsec=nearest.get("_sep_arcsec", 0.0),
                        refcat=refcat,
                    )
                    n_found += 1
                else:
                    # Save a sentinel so we don't retry
                    save_refcat(vasco_id, ra, dec, -1, -1, -1.0, refcat)
                    n_not_found += 1
            except Exception as e:
                tqdm.write(f"  ERROR refcat {vasco_id}: {e}")
                n_errors += 1
                save_refcat(vasco_id, ra, dec, -1, -1, -1.0, refcat)
            pbar.update(1)
            pbar.set_postfix(found=n_found, not_found=n_not_found, errors=n_errors)

    print(f"  Refcat found: {n_found}, not found: {n_not_found}, errors: {n_errors}")

    # Step 2: retrieve lightcurves
    lc_sources = get_refcat_for_lightcurve()
    # Filter out sentinel rows (gsc_bin_index = -1)
    lc_sources = [r for r in lc_sources if r["gsc_bin_index"] > 0]
    print(f"\nStage 2b: Retrieving lightcurves for {len(lc_sources)} sources")

    n_lc = 0
    n_lc_errors = 0

    with tqdm(total=len(lc_sources), desc="Lightcurves", unit="src") as pbar:
        for src in lc_sources:
            vasco_id = src["vasco_id"]
            if lightcurve_already_queried(vasco_id):
                pbar.update(1)
                continue
            try:
                raw = client.get_lightcurve(
                    gsc_bin_index=src["gsc_bin_index"],
                    ref_number=src["ref_number"],
                    refcat=src["refcat"],
                )
                lc = parse_csv_response(raw) if isinstance(raw, list) else []
                save_lightcurve(vasco_id, src["ra"], src["dec"], lc)
                n_lc += 1
            except Exception as e:
                tqdm.write(f"  ERROR lightcurve {vasco_id}: {e}")
                save_lightcurve(vasco_id, src["ra"], src["dec"], [])
                n_lc_errors += 1
            pbar.update(1)
            pbar.set_postfix(retrieved=n_lc, errors=n_lc_errors)

    print(f"\n=== Stage 2 Complete ===")
    print(f"Lightcurves retrieved: {n_lc}, errors: {n_lc_errors}")


if __name__ == "__main__":
    main()
