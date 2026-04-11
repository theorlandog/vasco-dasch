# VASCO × DASCH Cross-Match Pipeline

## Project Goal

Independently test VASCO transient claims by building an independent Harvard
transient catalog and comparing it statistically to POSS-I results.

**Key questions:**
1. Do Harvard plates show a comparable transient rate to POSS-I?
2. Does the Earth-shadow deficit reproduce on an independent telescope?
3. Do Harvard transients cluster near VASCO positions?
4. Does the nuclear-test temporal correlation hold?

**Outcome:** Publishable result regardless of finding (confirmation, constraint, or refutation).

## Data Sources

- **VASCO catalog** — Bruehl & Villarroel (2025), DOI: 10.1038/s41598-025-21620-3
  - 107,875 sources with J2000 RA/Dec and UTC timestamps
  - Vetted 5,399-source subset from Solano et al. (2022) via Spanish VO
- **DASCH DR7** — Harvard plate archive, fully free/open-access
  - API: no auth for metadata; registered API key required for FITS downloads
  - Registration: starglass.cfa.harvard.edu

## Transient Detection Method

Transients are detected by **consecutive plate-pair differencing** — the same
method POSS-I used. For each pair of consecutive plates from the same telescope
series (≤30 day gap):
1. Run DAOStarFinder on both plates
2. Compute WCS overlap region (Shapely polygon intersection)
3. Cross-match sources in the overlap (30 arcsec radius)
4. Unmatched sources with SNR > 10 are transient candidates

This produces an independent Harvard transient catalog, not a positional
cross-match against VASCO coordinates.

## Project Structure

```
vasco-dasch/
├── config.yaml                  # API keys, paths, parameters
├── pyproject.toml
├── run_pipeline.sh              # master script, stages 0–3
├── data/
│   ├── vasco_catalog/           # full_107k.csv, vetted_5399.csv
│   ├── pipeline.db              # SQLite: plates, transients, results
│   ├── fits_cutouts/            # downloaded plate pair images
│   └── results/                 # analysis outputs
├── src/
│   ├── 00_fetch_vasco_catalog.py
│   ├── 01_query_plate_coverage.py   # VASCO position plate query
│   ├── 01b_query_full_sky.py        # full-sky grid plate inventory
│   ├── 02_retrieve_lightcurves.py   # (legacy, not used in current pipeline)
│   ├── 03_filter_candidates.py      # (legacy, not used in current pipeline)
│   ├── 04_download_fits.py          # download consecutive plate pairs
│   ├── 05_source_extraction.py      # plate-pair differencing transient detection
│   ├── 06_rate_comparison.py        # Harvard vs POSS-I rate test
│   ├── 07_spatial_correlation.py    # Harvard ↔ VASCO clustering
│   ├── 08_shadow_analysis.py        # Earth shadow deficit on Harvard transients
│   ├── 09_generate_figures.py
│   └── utils/
│       ├── dasch_api.py         # API wrapper with rate limiting
│       ├── plate_pairs.py       # consecutive pair builder with gap filter
│       ├── coordinates.py       # astropy coordinate helpers
│       ├── database.py          # SQLite storage layer
│       └── statistics.py        # statistical test functions
├── notebooks/
└── tests/
```

## Python Dependencies

Managed via poetry (`pyproject.toml`). Run `poetry install` to set up the venv.

```
daschlab        # official DASCH Python toolkit
astropy         # coordinates, FITS, tables
photutils       # source extraction (DAOStarFinder)
shapely         # WCS footprint overlap computation
requests        # API calls
pandas / numpy / scipy / matplotlib
python-dotenv   # loads DASCHLAB_API_KEY from .env
openpyxl        # reads the nuclear dataset Excel file
```

## DASCH API — Actual Endpoints (discovered during development)

**Base URL:** `https://api.starglass.cfa.harvard.edu/full` (authenticated)
**Method:** POST with JSON body (NOT GET params)
**Auth:** `x-api-key` header, loaded from `.env` via `DASCHLAB_API_KEY`
**Response:** CSV-like list of strings; row 0 = column headers

| Endpoint | Payload keys |
|---|---|
| `/dasch/dr7/queryexps` | `ra_deg`, `dec_deg` |
| `/dasch/dr7/querycat` | `refcat`, `ra_deg`, `dec_deg`, `radius_arcsec` (max ~1800) |
| `/dasch/dr7/lightcurve` | `refcat`, `gsc_bin_index`, `ref_number` |

**Real-world performance (measured):**
- `queryexps`: 4–17 sec/position (varies by sky density)
- Near-polar sources (|Dec| > 88°) time out — excluded automatically
- Config: 120s timeout, 3 retries, 0.5 req/sec, exponential backoff
- `querycat` max radius: ~1800 arcsec (30 arcmin). Larger values return 400.

## Pipeline Stages

### Stage 0 — Setup & Validation
- Validate VASCO catalog files
- Test DASCH API connectivity

### Stage 1 — Plate Coverage Query (automated, complete)
- For each VASCO position: POST `queryexps`, filter to deep series in 1949–1957 window
- Store plate metadata in SQLite `plate_coverage` table
- 2 parallel workers, batched futures, thread-local clients (OOM-safe)
- **Status: complete** — 5,390 positions, 100% coverage

### Stage 1b — Full-Sky Grid Query (automated)
- Query a cos(dec)-adjusted 5° grid across the full sky (-85° to +85°)
- Fills in southern hemisphere plates not covered by VASCO positions
- Same `plate_coverage` table, IDs prefixed `grid_`
- **Status: running** — 1,668 positions, ETA ~2 hours

### Stage 4 — Download Plate Pairs (automated, authenticated)
- Build consecutive pairs from deep series (mc, mf, rb, b), ≤30 day gap
- Deduplicate across positions
- Download both plates at bin_factor=16 via `daschlab.Session.mosaic()`
- Directory: `data/fits_cutouts/{pair_id}/{plate_id}_16.fits`
- Flags: `--limit N`, `--max-gap-days N`, `--full`

### Stage 5 — Transient Detection (automated)
- For each plate pair: DAOStarFinder on both plates
- WCS overlap filter (Shapely polygon intersection)
- Cross-match sources (30 arcsec), keep unmatched with SNR > 10
- Output: `data/results/harvard_transients.csv` + `harvard_transients` table
- ~4 seconds per pair

### Stage 6 — Rate Comparison (automated)
- Harvard transient rate vs POSS-I rate (transients / pair / sq deg)
- Poisson test via `utils/statistics.py`
- Output: `data/results/rate_comparison.json`

### Stage 7 — Spatial Correlation (automated)
- Do Harvard transients cluster near VASCO positions?
- Monte Carlo nearest-neighbor shuffle test
- Output printed to stdout

### Stage 8 — Earth Shadow Deficit (automated)
- Solar elongation of each Harvard transient using plate observation dates
- Chi-square test vs 1.4% geometric expectation
- Output: `data/results/shadow_analysis.json` + figure

### Stage 9 — Figures & Paper Draft
- Sky coverage map, rate comparison plot, shadow elongation histogram
- **Human role:** write interpretation, discussion, conclusions

## Key Engineering Patterns

All API query loops must include:
- Rate limiting at 0.5 req/sec with exponential backoff
- Batched futures (≤ 2×workers in flight) to avoid OOM
- Thread-local API clients
- Checkpoint/resume logic (skip already-queried records)
- SQLite as the storage layer

## Deep Series Filter

Only 4 telescope series reach VASCO transient depth (mag 15–16):

| Series | Median lim mag | Role |
|--------|---------------|------|
| `mc` (Metcalf) | 17.0 | Best depth, mostly northern sky |
| `mf` | 16.4 | Good depth, strong southern coverage |
| `rb` | 15.8 | Marginal, widespread |
| `b` (Bache) | 15.3 | Marginal, sparse in 1950s |

Patrol cameras (`ai`, `fa`, `ka`, etc.) are excluded — too shallow.

## Scale & Storage

| Resource | Estimate |
|----------|----------|
| Stage 1 query time | ~12 hours (2 workers, vetted set) |
| Stage 1b query time | ~2 hours (1,668 grid positions) |
| Plate pairs (30d gap) | ~3,100 from VASCO + more from grid |
| FITS download | ~60–90 GB at bin16 |
| Stage 5 processing | ~4 sec/pair |
| Free disk needed | ~100 GB comfortable |

## Target Journals

- **RNAAS** — 1–2 page result, fast turnaround (good for null result)
- **PASP** — where Villarroel's aligned transients paper was published
- **MNRAS** — where the triple transient paper appeared
- **Scientific Reports** — where the nuclear test correlation paper appeared

## Standing Instructions for Claude

At the start of each conversation, review all files in `/notes/` and summarize
any new research notes, TODOs, or decisions that are relevant to the current
pipeline stage.

## Catalog Status

- **Vetted 5,399**: downloaded from Spanish VO, at `data/vasco_catalog/vetted_5399.csv`
- **Full 107,875**: not publicly available — must request from authors
- **Test 200**: synthetic, at `data/vasco_catalog/test_200.csv`
- **Nuclear dataset**: at `data/vasco_catalog/raw_nuclear_dataset.xlsx`

## Running the Pipeline

```bash
cd vasco-dasch/
poetry install                                        # first time only

# Stage 0+1: plate coverage (already complete)
./run_pipeline.sh --catalog vetted

# Stage 1b: full-sky inventory
poetry run python src/01b_query_full_sky.py --step 5 --workers 2

# Stages 4-8: transient detection and analysis
poetry run python src/04_download_fits.py [--limit 50] [--max-gap-days 30]
poetry run python src/05_source_extraction.py [--match-radius 30]
poetry run python src/06_rate_comparison.py
poetry run python src/07_spatial_correlation.py
poetry run python src/08_shadow_analysis.py
poetry run python src/09_generate_figures.py
```

## Completed Milestones

- [x] StarGlass API key + poetry environment
- [x] Stage 1 complete on vetted 5,399 sources (100% coverage)
- [x] OOM fix for Stage 1 (batched futures, window-only plates)
- [x] Pipeline redesigned: plate-pair differencing replaces positional matching
- [x] Stages 4–8 rewritten and tested on 6 plate pairs
- [x] Full-sky grid query launched (Stage 1b)
- [ ] Stage 1b completes
- [ ] Stage 4 full download
- [ ] Tune SNR threshold for Stage 5
- [ ] Full Stages 5–8 run on complete dataset
- [ ] Nuclear test temporal correlation (needs implementation)
- [ ] Email Bruehl/Villarroel for full 107k catalog
