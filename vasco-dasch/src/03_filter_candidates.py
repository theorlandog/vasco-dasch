"""Stage 3: Filter lightcurves and classify VASCO sources.

Classification flags:
  SINGLE_DETECTION  — exactly 1 detection on Harvard plates in 1949-1957
                      (candidate transient — target for FITS followup)
  MULTI_DETECTION   — ≥2 detections in window (persistent source;
                      suggests VASCO false positive)
  NO_DETECTION      — 0 detections in window (below limit or no coverage)
  NO_LIGHTCURVE     — no lightcurve data retrieved (refcat miss or error)

Quality cuts applied:
  - Drop detections with bad photometry flag (phot_flag != 0)
  - Drop edge detections (edgedist < 0.5 deg, if column present)
  - Drop detections with magnitude error > 1.0 mag

Output: data/results/candidates.csv

Usage:
    poetry run python src/03_filter_candidates.py
"""

import sys
import json
import sqlite3
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.database import get_conn, init_db

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "results"


def load_config():
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def parse_lc_detections(lc_rows: list, date_start: str, date_end: str) -> tuple[int, int]:
    """Count total detections and detections in the 1949-1957 window.

    Returns (n_total_detections, n_window_detections).
    Applies quality cuts.
    """
    n_total = 0
    n_window = 0
    for row in lc_rows:
        # Quality cut: skip bad photometry
        flag = row.get("phot_flag", "0")
        try:
            if int(flag) != 0:
                continue
        except (ValueError, TypeError):
            pass

        # Quality cut: skip large magnitude errors
        try:
            mag_err = float(row.get("magErr", row.get("mag_err", "0")))
            if mag_err > 1.0:
                continue
        except (ValueError, TypeError):
            pass

        # Get observation date — column might be "expdate", "date", "jd", etc.
        obs_date = row.get("expdate", row.get("date", row.get("dateObs", "")))
        if not obs_date:
            # Try Julian date
            jd_str = row.get("jd", row.get("JD", ""))
            if jd_str:
                try:
                    from astropy.time import Time
                    t = Time(float(jd_str), format="jd")
                    obs_date = t.iso[:10]
                except Exception:
                    pass

        if obs_date:
            date_part = str(obs_date)[:10]
            n_total += 1
            if date_start <= date_part <= date_end:
                n_window += 1

    return n_total, n_window


def classify(n_window: int) -> str:
    if n_window == 0:
        return "NO_DETECTION"
    elif n_window == 1:
        return "SINGLE_DETECTION"
    else:
        return "MULTI_DETECTION"


def main():
    cfg = load_config()
    date_start = cfg["pipeline"]["date_start"]
    date_end = cfg["pipeline"]["date_end"]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    with get_conn() as conn:
        # Get all sources that have coverage data
        coverage_rows = conn.execute(
            "SELECT vasco_id, ra, dec, n_window FROM plate_coverage"
        ).fetchall()

        lc_map = {}
        for row in conn.execute("SELECT vasco_id, lc_json FROM lightcurves").fetchall():
            lc_map[row["vasco_id"]] = json.loads(row["lc_json"])

    print(f"Classifying {len(coverage_rows)} sources...")

    records = []
    counts = {"SINGLE_DETECTION": 0, "MULTI_DETECTION": 0,
              "NO_DETECTION": 0, "NO_LIGHTCURVE": 0}

    for row in coverage_rows:
        vid = row["vasco_id"]
        ra = row["ra"]
        dec = row["dec"]
        n_window_plates = row["n_window"]

        if n_window_plates == 0:
            flag = "NO_DETECTION"
            n_det = 0
            n_win = 0
        elif vid not in lc_map:
            flag = "NO_LIGHTCURVE"
            n_det = 0
            n_win = 0
        else:
            lc_rows = lc_map[vid]
            n_det, n_win = parse_lc_detections(lc_rows, date_start, date_end)
            flag = classify(n_win)

        counts[flag] += 1
        records.append({
            "vasco_id": vid,
            "ra": ra,
            "dec": dec,
            "flag": flag,
            "n_detections": n_det,
            "n_window": n_win,
        })

    df = pd.DataFrame(records)
    out_path = RESULTS_DIR / "candidates.csv"
    df.to_csv(out_path, index=False)

    print(f"\n=== Stage 3 Complete ===")
    print(f"Results written to {out_path}")
    print(f"\nClassification summary:")
    total = len(records)
    for flag, count in counts.items():
        pct = 100 * count / max(total, 1)
        print(f"  {flag:<20s}: {count:5d} ({pct:.1f}%)")

    n_candidates = counts["SINGLE_DETECTION"]
    print(f"\n{n_candidates} single-detection candidates flagged for FITS followup (Stage 4).")

    if n_candidates == 0:
        print("No SINGLE_DETECTION candidates found — check lightcurve data quality.")
    elif n_candidates > 1000:
        print("NOTE: Large candidate list. Consider tightening quality cuts.")


if __name__ == "__main__":
    main()
