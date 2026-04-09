"""Validate coordinate transform functions."""

import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.coordinates import separation_arcsec, galactic_coords, jd_to_iso
import numpy as np


def test_separation_known():
    """Vega–Deneb separation should be ~23.7 degrees = ~85,320 arcsec."""
    sep = separation_arcsec(279.2347, 38.7836, 310.3579, 45.2808)
    assert 80000 < sep < 90000, f"Unexpected separation: {sep}"


def test_separation_same_point():
    sep = separation_arcsec(100.0, -30.0, 100.0, -30.0)
    assert sep < 0.001, f"Same-point separation should be ~0, got {sep}"


def test_galactic_coords():
    """Galactic center should be near l=0, b=0."""
    l, b = galactic_coords(
        np.array([266.405]), np.array([-28.936])
    )
    assert abs(l[0]) < 2.0, f"GC galactic l should be ~0, got {l[0]}"
    assert abs(b[0]) < 2.0, f"GC galactic b should be ~0, got {b[0]}"


def test_jd_conversion():
    """JD 2451545.0 = J2000.0 = 2000-01-01."""
    iso = jd_to_iso(2451545.0)
    assert iso.startswith("2000-01-01"), f"J2000 should be 2000-01-01, got {iso}"


if __name__ == "__main__":
    test_separation_known()
    test_separation_same_point()
    test_galactic_coords()
    test_jd_conversion()
    print("All coordinate tests passed.")
