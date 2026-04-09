"""SQLite storage layer for the pipeline."""

import sqlite3
import json
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"


def db_path() -> Path:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return Path(__file__).parent.parent.parent / cfg["paths"]["db"]


def get_conn() -> sqlite3.Connection:
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS plate_coverage (
            vasco_id    TEXT PRIMARY KEY,
            ra          REAL,
            dec         REAL,
            queried_at  TEXT,
            plate_json  TEXT
        );

        CREATE TABLE IF NOT EXISTS lightcurves (
            vasco_id    TEXT PRIMARY KEY,
            ra          REAL,
            dec         REAL,
            queried_at  TEXT,
            lc_json     TEXT
        );

        CREATE TABLE IF NOT EXISTS candidates (
            vasco_id        TEXT PRIMARY KEY,
            ra              REAL,
            dec             REAL,
            flag            TEXT,
            n_detections    INTEGER,
            n_window        INTEGER,
            notes           TEXT
        );
        """)


def coverage_already_queried(vasco_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM plate_coverage WHERE vasco_id = ?", (vasco_id,)
        ).fetchone()
        return row is not None


def save_coverage(vasco_id: str, ra: float, dec: float, plates: list):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO plate_coverage
               (vasco_id, ra, dec, queried_at, plate_json)
               VALUES (?, ?, ?, datetime('now'), ?)""",
            (vasco_id, ra, dec, json.dumps(plates)),
        )


def lightcurve_already_queried(vasco_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM lightcurves WHERE vasco_id = ?", (vasco_id,)
        ).fetchone()
        return row is not None


def save_lightcurve(vasco_id: str, ra: float, dec: float, lc: dict):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO lightcurves
               (vasco_id, ra, dec, queried_at, lc_json)
               VALUES (?, ?, ?, datetime('now'), ?)""",
            (vasco_id, ra, dec, json.dumps(lc)),
        )


def get_positions_with_coverage(date_start: str, date_end: str):
    """Return (vasco_id, ra, dec) for positions with plates in the date window."""
    with get_conn() as conn:
        rows = conn.execute("SELECT vasco_id, ra, dec, plate_json FROM plate_coverage").fetchall()
    results = []
    for row in rows:
        plates = json.loads(row["plate_json"])
        in_window = [
            p for p in plates
            if date_start <= p.get("obs_date", "") <= date_end
        ]
        if in_window:
            results.append((row["vasco_id"], row["ra"], row["dec"]))
    return results
