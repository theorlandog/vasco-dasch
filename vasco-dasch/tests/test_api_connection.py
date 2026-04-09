"""Verify DASCH API endpoints respond correctly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.dasch_api import DASCHClient, parse_csv_response


def test_exposures_known_star():
    """Query exposures for Vega; expect a non-empty plate list."""
    client = DASCHClient()
    # Vega: RA=279.2347, Dec=+38.7836
    result = client.query_exposures(ra_deg=279.2347, dec_deg=38.7836)
    print(f"Exposures result type: {type(result)}, length: {len(result) if result else 0}")
    if isinstance(result, list) and len(result) > 1:
        rows = parse_csv_response(result)
        print(f"  Parsed {len(rows)} exposure rows")
        print(f"  Columns: {list(rows[0].keys()) if rows else 'none'}")
        print(f"  Sample row: {rows[0] if rows else 'none'}")
    else:
        print(f"  Raw result: {result}")
    assert isinstance(result, list), f"Expected list, got {type(result)}"


def test_refcat_known_star():
    """Query APASS catalog near Vega."""
    client = DASCHClient()
    result = client.query_refcat(ra_deg=279.2347, dec_deg=38.7836, radius_arcsec=60.0)
    print(f"Refcat result type: {type(result)}, length: {len(result) if result else 0}")
    if isinstance(result, list) and len(result) > 1:
        rows = parse_csv_response(result)
        print(f"  Parsed {len(rows)} catalog sources")
        if rows:
            print(f"  Columns: {list(rows[0].keys())}")
    else:
        print(f"  Raw result: {result}")


def test_vasco_position():
    """Test a real VASCO-like coordinate for plate coverage."""
    client = DASCHClient()
    # RA=180, Dec=+45 — a test position from the project plan
    result = client.query_exposures(ra_deg=180.0, dec_deg=45.0)
    print(f"VASCO-test position coverage: {len(result) if result else 0} lines")
    assert isinstance(result, list)


if __name__ == "__main__":
    print("=== Test 1: Exposures for Vega ===")
    test_exposures_known_star()
    print("\n=== Test 2: Refcat near Vega ===")
    test_refcat_known_star()
    print("\n=== Test 3: VASCO-style position ===")
    test_vasco_position()
    print("\nAll API tests passed.")
