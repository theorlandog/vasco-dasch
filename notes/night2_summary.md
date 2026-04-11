# VASCO × DASCH Project — Night 2 Summary
## April 9–10, 2026

---

## Major methodology change

### The problem with positional matching
The Night 1 pipeline was built around checking exact VASCO positions on Harvard
plates: "did the same spot flash again?" This was the wrong question — the
probability of catching the identical flash is ~0%. The pipeline's Stages 2–3
(APASS check, candidate classification) were designed for this approach.

### New approach: consecutive plate-pair differencing
Detect transients the way POSS-I did — compare consecutive exposures from the
same telescope. A source on plate A but absent on plate B (same series,
consecutive dates) is a transient candidate. This gives an independent Harvard
transient catalog that can be compared to VASCO statistically.

The science questions are now:
1. **Rate comparison** — does Harvard see transients at a similar rate to POSS-I?
2. **Spatial correlation** — do Harvard transients cluster near VASCO positions?
3. **Earth shadow deficit** — does the antisolar deficit reproduce on Harvard data?
4. **Nuclear test correlation** — does the temporal correlation hold?

### Full-sky inventory
Night 1 only queried plates at VASCO positions (Dec > -3.3°, northern sky only).
This biased the sample. Night 2 added a full-sky grid query (`01b_query_full_sky.py`)
at 5° spacing, covering Dec -85° to +85°. This picks up deep-series plates in
the southern hemisphere that VASCO never touched, giving an unbiased sample for
rate comparison and shadow deficit.

---

## What we accomplished

### Stage 1 completed (vetted catalog)
- 5,390 positions queried (100% coverage in 1949–1957 window)
- 9 errors (polar/timeout)
- Go/No-Go gate passed

### Memory leak fixed in Stage 1
The pipeline OOM-killed twice at ~600–700 queries. Root causes:
1. `query_one()` returned ALL ~1,455 plates per position instead of just window
   plates — each future held megabytes of plate dicts
2. All futures submitted at once via `ThreadPoolExecutor` — thousands of results
   accumulated in memory
3. New `DASCHClient()` created per query instead of per worker thread

Fixes:
- Return only window-filtered plates from `query_one()`
- Batch futures: only `2 × n_workers` in flight at a time
- Thread-local client instances
- Reduced workers from 4 to 2 as additional safety margin

### Pipeline redesigned (Stages 4–8)
Old pipeline (positional matching):
```
Stage 2: APASS check at VASCO positions → Stage 3: classify → Stage 4: download
plates per candidate → Stage 5: look for source at exact VASCO RA/Dec
```

New pipeline (plate-pair differencing):
```
Stage 1b: full-sky grid query → Stage 4: download consecutive plate pairs →
Stage 5: DAOStarFinder on both plates, diff unmatched sources → Stage 6: rate
comparison → Stage 7: spatial correlation → Stage 8: shadow deficit
```

### Consecutive pair logic
- Group plates by series within each queried position
- Sort by expdate, form consecutive pairs
- Filter to ≤30 day gap (avoids variable star contamination)
- Deduplicate across positions (same plate pair from different VASCO positions)
- Result: **3,146 pairs from VASCO positions** (before grid query completes)

### Pair time-gap analysis (200-position sample)
| Gap | % of pairs |
|-----|-----------|
| ≤1 day | 41% |
| ≤7 days | 54% |
| ≤30 days | 64% |
| Median | 5 days |

Same-night pairs are ideal (closest to POSS-I's method). 30-day default
filter keeps the majority while excluding multi-month gaps.

### Stage 5 — source extraction rewritten
Key engineering decisions:
- **WCS overlap filter**: compute footprint intersection of both plates using
  Shapely polygons. Only consider sources in the overlap region. This eliminates
  thousands of false "transients" caused by plate-edge differences.
- **SNR > 10 cut**: bright sources should appear on both plates of similar depth.
  High-SNR unmatched sources are credible candidates; low-SNR ones are noise.
- **APASS API too slow for wide-field**: tried per-source queries (hours per pair),
  then tiled 30-arcmin queries (minutes per pair), settled on SNR filtering
  (seconds per pair). APASS filtering can be revisited with a local catalog file.

### Test run results (6 pairs)
| Stage | Result |
|-------|--------|
| Stage 5 | 1,254 candidates (~200/pair) — still high, needs tuning |
| Stage 6 | Harvard rate 4.7× POSS-I (inflated by noisy candidates) |
| Stage 7 | 0 spatial matches with VASCO (expected at this scale) |
| Stage 8 | 0/1254 in shadow, p=2.4e-5 (small sample, sky region bias) |

### Full-sky grid query launched
- 1,668 positions at 5° spacing, cos(dec)-adjusted RA density
- Running at ~4s/position with 2 workers, ETA ~2 hours
- Southern sky already producing plates not seen in VASCO queries:
  7,051 deep plates from first 156 grid positions (Dec -85 to -55)
- `mf` dominant in south, `mc` concentrated in north

### Plate inventory
| Source | Unique deep plates |
|--------|-------------------|
| VASCO positions (5,400) | 3,181 |
| Grid (partial, 156 of 1,668) | ~7,000+ (growing) |

---

## Disk and storage estimates
- Current FITS on disk: 2.2 GB (test data from Night 1)
- VASCO pairs only: ~30 GB (3,146 pairs × 2 × 3 MB)
- With full-sky grid: ~60–90 GB estimated
- Free disk: 268 GB — fits comfortably

---

## Files changed tonight

| File | Change |
|------|--------|
| `src/01_query_plate_coverage.py` | Fixed OOM: window-only plates, batched futures, thread-local clients |
| `src/01b_query_full_sky.py` | **New**: full-sky grid query for unbiased plate inventory |
| `src/utils/plate_pairs.py` | **New**: consecutive pair builder with max-gap filter |
| `src/utils/database.py` | Added `harvard_transients` table |
| `src/04_download_fits.py` | Rewritten for plate pairs, not per-candidate |
| `src/05_source_extraction.py` | Rewritten: full-plate diff with WCS overlap + SNR filter |
| `src/06_rate_comparison.py` | **New**: Harvard vs POSS-I Poisson rate test |
| `src/07_spatial_correlation.py` | Updated: reads Harvard transients |
| `src/08_shadow_analysis.py` | Updated: shadow test on Harvard transients |
| `run_pipeline.sh` | Updated stage descriptions, workers=2 |
| `README.md` | Created with background, approach, Mermaid diagrams |

---

## Processes running
- **Stage 1b (grid):** 288/1,668, ETA ~1.5 hours

---

## Next steps

### After grid query completes
- [ ] Count total unique pairs with grid + VASCO combined
- [ ] Launch Stage 4 download overnight (~15–20 hours for all pairs)
- [ ] Run Stage 5 on downloaded pairs
- [ ] Tune SNR threshold — 200 candidates/pair is too high
- [ ] Run Stages 6–8 on full dataset

### Candidate count tuning
The ~200 candidates/pair suggests either:
- SNR > 10 is too permissive — try SNR > 20 or SNR > 30
- 30-arcsec match radius needs adjustment for specific series
- Need to add back APASS filtering via local catalog (Vizier download)

### Longer term
- [ ] Download APASS catalog locally for fast filtering (avoids API bottleneck)
- [ ] Nuclear test temporal correlation (Stage 8b — needs implementation)
- [ ] Email Bruehl/Villarroel for full 107k catalog
- [ ] Figure generation (Stage 9)
