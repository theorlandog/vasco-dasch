# VASCO × DASCH Project — Night 1 Summary
## April 8, 2026

---

## What we learned

### The VASCO debate
- The VASCO project (led by Beatriz Villarroel, Nordita/Stockholm) found 107,875
  transient sources on 1949–1957 Palomar Sky Survey plates — brief flashes that
  appear once and never again, all pre-dating Sputnik
- Key findings: 22σ deficit of transients inside Earth's shadow (consistent with
  sunlight reflections off orbiting objects at ~GEO altitude), 45% increased
  transient rate within 24 hours of nuclear tests
- Watters et al. (2026) published a 30-page critique arguing plate defects and
  observation schedule artifacts
- Villarroel rebutted (Feb 2026, arXiv:2602.15171)
- Independent replications: Doherty (April 2026) confirmed shadow deficit and
  nuclear correlation; Busko (March 2026) found similar transients on Hamburg
  Observatory plates via APPLAUSE — first independent telescope confirmation

### The gap we identified
- Nobody has cross-matched VASCO transients against Harvard's DASCH plate archive
- DASCH DR7 became fully public December 2024 — 430,000+ plates, 1885–1992
- The Hamburg APPLAUSE paper explicitly called for cross-instrument validation
- This is a novel, publishable project regardless of outcome

### What we ruled out
- Solar transit detection: ran the math, objects at GEO altitude produce
  0.09 ppm dimming against the solar disk — 5 orders of magnitude below
  photographic plate sensitivity. Dead end.
- Catching the identical flash on a Harvard plate: probability ~0%.
  Different approach needed (rate comparison, spatial correlation)

---

## What we accomplished tonight

### Live API queries against DASCH/StarGlass
- Confirmed the StarGlass search API works at:
  `POST https://api.starglass.cfa.harvard.edu/public/plates/search`
- Learned that "medium" precision search uses WCS bounds (can miss wide-field
  plates and produce false positives)
- "Low" precision search uses sky bins and returns comprehensive results

### Coverage confirmed
- Queried the nine-transient field (RA=83.5°, Dec=+28.9°) for all scanned
  Harvard plates 1949–1957
- Result: **~1,400 plates** potentially covering the field
- Multiple telescope series: ai, fa, ka, kb, kc, ke, kf, kg, b, bi, rh, and others

### Depth assessment
- Patrol cameras (ai, fa series): 1.5-inch aperture, wide field, 5–51 min
  exposures. Too shallow for VASCO transients (mag 15–16). Useful for rate
  comparison of brighter transients only.
- **8-inch Bache Doublet (b series): 30–45 min exposures. Comparable depth
  to Palomar's 48-inch Schmidt for the relevant magnitude range.**

### The 11 key plates identified
All 8-inch Bache Doublet, Bloemfontein, South Africa:

| Plate   | Date           | RA     | Dec    | Exp  | Offset from VASCO field |
|---------|----------------|--------|--------|------|------------------------|
| b74433  | 1949-02-03     | 78.7°  | +25.5° | 30m  | ~5.5°                  |
| b74449  | 1949-02-17     | 79.0°  | +25.7° | 45m  | ~5.3°                  |
| b74510  | 1949-03-22     | 85.5°  | +26.4° | 45m  | **~3.0°** ⭐           |
| b75044  | 1949-08-30     | 85.8°  | +26.4° | 45m  | **~3.0°** ⭐           |
| b75125  | 1949-10-21     | 79.4°  | +25.7° | 45m  | ~5.0°                  |
| b75567  | 1950-09-18     | 79.6°  | +25.7° | 45m  | ~5.0°                  |
| b75652  | 1950-11-12     | 79.7°  | +25.8° | 45m  | ~4.9°                  |
| b76004  | 1951-11-26     | 79.6°  | +25.6° | 45m  | ~5.1°                  |
| b76115  | 1952-03-18     | 85.5°  | +26.3° | 45m  | **~3.0°** ⭐           |
| b76610  | 1953-02-05     | 79.6°  | +25.6° | 45m  | ~5.0°                  |
| b76664  | 1953-03-08     | 79.4°  | +25.9° | 45m  | ~4.8°                  |

**Three best plates (⭐): b74510, b75044, b76115** — centered ~3° from the
nine-transient position, near plate center where image quality is best.

### Timeline proximity to VASCO events
- Nine-transient event: April 12, 1950
  - b74510: March 22, 1949 (13 months before)
  - b75044: August 30, 1949 (8 months before)
  - b75567: September 18, 1950 (5 months after)
- Triple transient event: July 19, 1952
  - b76115: March 18, 1952 (4 months before)

---

## Next steps

### Immediate (tonight or tomorrow)
- [ ] Sign up at starglass.cfa.harvard.edu/signin
- [ ] Get API key from user profile
- [ ] Download FITS mosaic for b76115 (best plate closest to VASCO events)
- [ ] Install daschlab: `pip install daschlab`
- [ ] Run daschlab Session query at VASCO coordinates to compare with StarGlass results

### This week
- [ ] Download VASCO supplementary data from DOI: 10.1038/s41598-025-21620-3
- [ ] Get the Solano et al. (2022) vetted 5,399-source catalog
- [ ] Run source extraction on b76115 FITS with photutils
- [ ] Check if any extracted sources coincide with known VASCO transient positions

### Project architecture
- Full pipeline plan saved as: vasco_dasch_project_plan.md
- Claude Code can automate stages 1–6
- Estimated total effort: 40–60 hours over ~10 weeks
- All data access is free
- Publishable in RNAAS, PASP, MNRAS, or Scientific Reports

---

## Key URLs
- StarGlass: https://starglass.cfa.harvard.edu
- StarGlass API docs: https://starglass.cfa.harvard.edu/docs/api/
- DASCH DR7: https://dasch.cfa.harvard.edu/dr7/
- daschlab docs: https://daschlab.readthedocs.io
- VASCO data: DOI 10.1038/s41598-025-21620-3
- DASCH mailing list: dasch@gaggle.email

---

## Important caveat
The 1.5-inch patrol cameras (majority of the 1,400 plates) almost certainly
cannot reach VASCO transient magnitudes (15–16). The 8-inch Bache Doublet
plates are the viable ones for direct transient detection. The patrol plates
are still useful for the rate comparison test at brighter magnitudes, but the
core science case rests on the 11 Bache plates plus any other deep plates
from larger Harvard telescopes that may be in the list (rh, mc series — not
yet characterized).
