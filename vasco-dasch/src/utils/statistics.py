"""Statistical test functions for Stage 6 analysis."""

import numpy as np
from scipy import stats


def poisson_rate_test(k_obs: int, k_exp: float) -> dict:
    """One-sided Poisson test: is the observed rate higher than expected?

    Args:
        k_obs: observed count
        k_exp: expected count under null hypothesis

    Returns dict with p_value, rate_ratio, and interpretation.
    """
    p_value = stats.poisson.sf(k_obs - 1, k_exp)  # P(X >= k_obs)
    rate_ratio = k_obs / max(k_exp, 1e-10)
    return {
        "k_obs": k_obs,
        "k_exp": round(k_exp, 3),
        "rate_ratio": round(rate_ratio, 3),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
    }


def spatial_correlation_mc(
    test_ra: np.ndarray,
    test_dec: np.ndarray,
    ref_ra: np.ndarray,
    ref_dec: np.ndarray,
    n_mc: int = 10000,
    radius_arcsec: float = 10.0,
) -> dict:
    """Monte Carlo spatial correlation test.

    Tests whether test positions are spatially correlated with reference
    positions (closer than expected by chance).

    Args:
        test_ra/dec: positions to test (Harvard transients if any)
        ref_ra/dec: reference positions (VASCO transients)
        n_mc: number of Monte Carlo shuffles
        radius_arcsec: matching radius

    Returns dict with observed count, MC mean/std, z-score, p-value.
    """
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    def count_matches(ra1, dec1, ra2, dec2, r_arcsec):
        if len(ra1) == 0 or len(ra2) == 0:
            return 0
        c1 = SkyCoord(ra=ra1 * u.deg, dec=dec1 * u.deg, frame="icrs")
        c2 = SkyCoord(ra=ra2 * u.deg, dec=dec2 * u.deg, frame="icrs")
        idx, sep, _ = c1.match_to_catalog_sky(c2)
        return int((sep.arcsec < r_arcsec).sum())

    n_obs = count_matches(test_ra, test_dec, ref_ra, ref_dec, radius_arcsec)

    # Monte Carlo: shuffle ref positions on the sky
    mc_counts = []
    rng = np.random.default_rng(42)
    for _ in range(n_mc):
        rand_ra = rng.uniform(0, 360, size=len(ref_ra))
        rand_dec = np.degrees(np.arcsin(rng.uniform(-1, 1, size=len(ref_ra))))
        mc_counts.append(count_matches(test_ra, test_dec, rand_ra, rand_dec, radius_arcsec))

    mc_arr = np.array(mc_counts)
    mc_mean = float(mc_arr.mean())
    mc_std = float(mc_arr.std())
    z = (n_obs - mc_mean) / max(mc_std, 1e-10)
    p_value = float((mc_arr >= n_obs).mean())

    return {
        "n_obs_matches": n_obs,
        "mc_mean": round(mc_mean, 2),
        "mc_std": round(mc_std, 2),
        "z_score": round(z, 3),
        "p_value": round(p_value, 4),
        "significant": p_value < 0.05,
    }


def earth_shadow_test(
    obs_times_utc: list,
    ra_list: np.ndarray,
    dec_list: np.ndarray,
    observer_lon: float = -116.865,
    observer_lat: float = 33.356,
    observer_height_m: float = 1712,
) -> dict:
    """Test if transients cluster inside/outside Earth's umbral shadow cone.

    The expected fraction inside the umbra is ~1.4% geometrically.
    Uses astropy to compute Sun position at each observation time.

    Returns chi-square test result comparing observed vs expected fractions.
    """
    from astropy.time import Time
    from astropy.coordinates import get_sun, SkyCoord, EarthLocation
    import astropy.units as u

    location = EarthLocation(
        lon=observer_lon * u.deg,
        lat=observer_lat * u.deg,
        height=observer_height_m * u.m,
    )

    n_shadow = 0
    n_total = 0

    for utc_str, ra, dec in zip(obs_times_utc, ra_list, dec_list):
        try:
            t = Time(utc_str)
            sun = get_sun(t)
            src = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
            sep = sun.separation(src).deg
            # Umbral cone: antisolar direction ± ~0.27 deg (half-angle)
            in_shadow = sep > (180 - 0.27)
            if in_shadow:
                n_shadow += 1
            n_total += 1
        except Exception:
            continue

    if n_total == 0:
        return {"error": "No valid observations"}

    expected_frac = 0.014  # ~1.4% geometric expectation
    n_expected = expected_frac * n_total
    result = stats.chisquare(
        f_obs=[n_shadow, n_total - n_shadow],
        f_exp=[n_expected, n_total - n_expected],
    )
    return {
        "n_total": n_total,
        "n_shadow": n_shadow,
        "frac_shadow": round(n_shadow / n_total, 4),
        "expected_frac": expected_frac,
        "chi2": round(float(result.statistic), 4),
        "p_value": round(float(result.pvalue), 6),
        "significant": result.pvalue < 0.05,
    }


def contingency_test(n_transients_on_test_days: int,
                     n_test_days: int,
                     n_transients_off_test_days: int,
                     n_non_test_days: int) -> dict:
    """Chi-square contingency table for nuclear test temporal correlation."""
    table = np.array([
        [n_transients_on_test_days, n_test_days - n_transients_on_test_days],
        [n_transients_off_test_days, n_non_test_days - n_transients_off_test_days],
    ])
    chi2, p, dof, expected = stats.chi2_contingency(table)
    rate_on = n_transients_on_test_days / max(n_test_days, 1)
    rate_off = n_transients_off_test_days / max(n_non_test_days, 1)
    return {
        "rate_on_test_days": round(rate_on, 4),
        "rate_off_test_days": round(rate_off, 4),
        "rate_ratio": round(rate_on / max(rate_off, 1e-10), 3),
        "chi2": round(float(chi2), 4),
        "p_value": round(float(p), 6),
        "dof": int(dof),
        "significant": p < 0.05,
    }
