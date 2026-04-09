"""Astropy coordinate helpers for the pipeline."""

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u


def make_skycoord(ra_deg: float | np.ndarray, dec_deg: float | np.ndarray) -> SkyCoord:
    return SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")


def separation_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    c1 = make_skycoord(ra1, dec1)
    c2 = make_skycoord(ra2, dec2)
    return float(c1.separation(c2).arcsec)


def match_catalog(
    ra_test: np.ndarray, dec_test: np.ndarray,
    ra_ref: np.ndarray, dec_ref: np.ndarray,
    max_sep_arcsec: float = 10.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Match test positions to reference catalog.

    Returns (idx, sep_arcsec, matched_mask) where:
      idx — index into ref catalog for each test position
      sep_arcsec — separation in arcseconds
      matched_mask — bool array, True if within max_sep_arcsec
    """
    c_test = make_skycoord(ra_test, dec_test)
    c_ref = make_skycoord(ra_ref, dec_ref)
    idx, sep, _ = c_test.match_to_catalog_sky(c_ref)
    sep_arcsec = sep.arcsec
    matched = sep_arcsec < max_sep_arcsec
    return idx, sep_arcsec, matched


def galactic_coords(ra_deg: np.ndarray, dec_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert ICRS RA/Dec to Galactic l, b in degrees."""
    c = make_skycoord(ra_deg, dec_deg)
    gal = c.galactic
    return gal.l.deg, gal.b.deg


def jd_to_iso(jd: float) -> str:
    """Convert Julian date to ISO 8601 date string."""
    return Time(jd, format="jd").iso[:10]


def poss_date_to_jd(date_str: str) -> float | None:
    """Convert a POSS-I obs date string to Julian date."""
    try:
        return float(Time(date_str[:10]).jd)
    except Exception:
        return None
