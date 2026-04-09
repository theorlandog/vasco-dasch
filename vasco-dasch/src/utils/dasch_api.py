"""DASCH StarGlass API wrapper with rate limiting and retry logic."""

import time
import yaml
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class DASCHClient:
    def __init__(self):
        cfg = load_config()
        self.base_url = cfg["dasch"]["base_url"]
        self.api_key = cfg["starglass_api_key"]
        self.rate_limit = cfg["dasch"]["rate_limit_rps"]
        self.max_retries = cfg["dasch"]["max_retries"]
        self.backoff_base = cfg["dasch"]["backoff_base"]
        self._last_request = 0.0

    def _headers(self):
        return {"x-api-key": self.api_key, "Accept": "application/json"}

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        gap = 1.0 / self.rate_limit
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self._last_request = time.monotonic()

    def get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                resp = requests.get(url, params=params, headers=self._headers(), timeout=30)
                if resp.status_code == 429:
                    wait = self.backoff_base ** attempt
                    print(f"  Rate limited; sleeping {wait:.1f}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                wait = self.backoff_base ** attempt
                print(f"  Request error ({e}); retry {attempt+1}/{self.max_retries} in {wait:.1f}s")
                time.sleep(wait)
        raise RuntimeError(f"DASCH API call failed after {self.max_retries} retries: {url}")

    def query_plate_coverage(self, ra: float, dec: float, radius_arcsec: float = 5.0) -> dict:
        """Query plates covering a sky position."""
        return self.get("/dasch/dr7/queryexps", params={
            "ra": ra, "dec": dec, "radius": radius_arcsec / 3600.0,
        })

    def get_lightcurve(self, ra: float, dec: float, radius_arcsec: float = 5.0) -> dict:
        """Retrieve DASCH lightcurve at a position."""
        return self.get("/dasch/dr7/lightcurve", params={
            "ra": ra, "dec": dec, "radius": radius_arcsec / 3600.0,
            "catalog": "apass",
        })

    def download_fits(self, plate_id: str, bin_factor: int = 16, dest_path: Path = None) -> Path:
        """Download a plate FITS mosaic."""
        url = f"{self.base_url}/full/plates/p/{plate_id}/mosaic/download"
        self._throttle()
        resp = requests.get(url, params={"bin_factor": bin_factor},
                            headers=self._headers(), stream=True, timeout=120)
        resp.raise_for_status()
        if dest_path is None:
            dest_path = Path(f"{plate_id}_bin{bin_factor:02d}.fits")
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        return dest_path
