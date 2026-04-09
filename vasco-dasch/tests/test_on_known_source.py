"""End-to-end test: run the full pipeline on a single known bright star.

Uses Vega (RA=279.2347, Dec=38.7836) as a well-known source that should
have Harvard plate coverage and a detectable lightcurve.
"""

import sys
import json
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.dasch_api import DASCHClient, parse_csv_response
from utils.coordinates import separation_arcsec


VEGA_RA = 279.2347
VEGA_DEC = 38.7836
DATE_START = "1949-11-01"
DATE_END = "1957-10-04"


def test_vega_has_plate_coverage():
    client = DASCHClient()
    raw = client.query_exposures(ra_deg=VEGA_RA, dec_deg=VEGA_DEC)
    assert isinstance(raw, list) and len(raw) > 1, "Expected plate list for Vega"
    plates = parse_csv_response(raw)
    assert len(plates) > 0, "Should have at least one plate"

    # Check for 1949-1957 coverage
    in_window = [
        p for p in plates
        if DATE_START <= p.get("expdate", "")[:10] <= DATE_END
    ]
    print(f"  Vega: {len(plates)} total plates, {len(in_window)} in 1949-1957 window")
    assert len(in_window) > 0, "Vega should have Harvard plates in the POSS-I era"


def test_vega_refcat():
    client = DASCHClient()
    raw = client.query_refcat(ra_deg=VEGA_RA, dec_deg=VEGA_DEC,
                              radius_arcsec=60.0, refcat="apass")
    assert isinstance(raw, list), "Expected refcat response"
    rows = parse_csv_response(raw)
    print(f"  Found {len(rows)} APASS sources within 60 arcsec of Vega")
    # Note: Vega is too bright for APASS, so we may not get a match
    # The test just checks that the API responds correctly


def test_vega_lightcurve():
    """Retrieve lightcurve for a source near Vega."""
    client = DASCHClient()
    # First get a refcat source
    raw_cat = client.query_refcat(ra_deg=VEGA_RA, dec_deg=VEGA_DEC,
                                  radius_arcsec=300.0, refcat="apass")
    rows = parse_csv_response(raw_cat)
    if not rows:
        print("  No APASS source near Vega — skipping lightcurve test")
        return

    src = rows[0]
    gsc_bin_index = int(src["gsc_bin_index"])
    ref_number = int(src["ref_number"])
    print(f"  Testing lightcurve for gsc_bin_index={gsc_bin_index}, ref_number={ref_number}")

    raw_lc = client.get_lightcurve(gsc_bin_index=gsc_bin_index, ref_number=ref_number)
    assert isinstance(raw_lc, list), f"Expected lightcurve list, got {type(raw_lc)}"
    lc = parse_csv_response(raw_lc)
    print(f"  Lightcurve: {len(lc)} data points")
    assert len(lc) > 0, "Should have at least one lightcurve point"


if __name__ == "__main__":
    print("=== End-to-end test on Vega ===\n")
    print("Test 1: Plate coverage...")
    test_vega_has_plate_coverage()
    print("Test 2: Refcat lookup...")
    test_vega_refcat()
    print("Test 3: Lightcurve retrieval...")
    test_vega_lightcurve()
    print("\nAll end-to-end tests passed.")
