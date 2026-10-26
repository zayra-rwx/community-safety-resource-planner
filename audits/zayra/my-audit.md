# My Module 9 audit — Zayra Martinez

## Context

- Name: Zayra Martinez (zayra-rwx)
- Team app and version or commit checked: Community Safety Resource Planner, `main` at commit `87a892a392727cfaff176d3c0fbbf6019a60eb4a` (Phase 2 backend + CLI; no dashboard is built yet). Checks and outputs are in `audits/zayra/` on branch `zayra-rwx`. Environment: Python 3.13 with pinned `requirements-phase2.txt` (pandas 3.0.6, pyarrow 23.0.1); the team's 40 tests pass (`pytest -q`).
- Intended user and decision: LA Bureau of Street Lighting planning manager deciding which LAPD reporting districts get on-site lighting assessments first (BUILD_SPEC §3).

## 1. Feature audit

- Feature and intended behavior: **District composition** (use case 2, BUILD_SPEC §4 and §8 "District Evidence"). For one selected district, the manager should see the offense composition and premise composition of its nighttime reported offenses, to decide whether the pattern is concentrated in one category or premise. The backend function is `category_summary(d, column, filters)` in `src/analysis.py:155-163`. Missing labels are shown as `Unknown` only in the output (§5).
- Inputs and steps to reproduce: `python audits/zayra/check_mapped.py --raw <raw csv>` (Check 4) and `python -m src.analysis --help`. Both are saved in `audits/zayra/check-output.txt` and `cli-help.txt`. Selection used: `Filters(districts=('0182',))`, with the default dates 2025-01-01 to 2026-09-19.
- Expected behavior: offense and premise breakdowns whose counts add up to the district's nighttime count (0182 = 1,167). Rows are sorted largest first, and the manager can actually reach them.
- Actual behavior and evidence:
  - **Works:** For 0182, offense composition has 146 categories and premise composition has 78. Each adds to 1,167, which matches the ranked table. The top premises are Parking Lot / Garage (246), Street/Parkway (183) and Apartment/Condo (152). The top offense is burglary from motor vehicle (222). Sorting is deterministic: by count, then by label.
  - **Missing:** The manager cannot reach this feature. The only interface is the CLI, which has only `--start`, `--end` and `--top`. There is no district option and no composition output, so use case 2 needs Python code. The output also has no share or percentage column and no period label. With 146 offense categories, "is it concentrated?" has to be worked out by hand.
  - **Misleading:** Across all districts, the premise summary shows two separate "unknown" rows. `Location Unknown` (546) is a real source label; `Unknown` (1) is the app's label for a missing premise. Both follow the spec's rule not to merge labels, but a manager would likely read them as the same thing. Offense labels are raw statute strings (for example, `594(B)(1) - PC - F - Vandalism ($400 Or More) - Felony - 290`), which a lighting planner will find hard to scan.
- Conclusion and any recommended change: The calculation is correct, but the feature is not delivered to its user. See **AUDIT-ZAYRA-03**.

## 2. Number audit

- Number audited and its meaning: **Valid mapped nighttime offenses**, focused on district **0182** (rank 1), with a value of **1,167**. It should mean: of the district's qualifying nighttime reported offenses, how many have coordinates usable on the map (BUILD_SPEC §6). Mapped coverage = mapped ÷ nighttime.
- Formula, units, population, and time window: the count of distinct `UniqueNIBRNo` values (unit: offenses). An offense counts when its occurrence date is from 2025-01-01 to 2026-09-19, its valid time is 18:00–05:59 (midnight `0000` included), its district and ID are present, and LAT is in [33.5, 34.9] and LON in [−118.9, −117.5] (both inclusive). Missing, zero, nonnumeric or outside-box coordinates fail.
- Relevant data assumptions: (a) the box is a broad screen, not the city boundary (README); (b) an offense is "mapped" if it is inside that box, even when the point is far from its own district; (c) `RPT Dist No` is a real reporting district.
- Code checked: `src/clean_data.py:65-71` (coordinate parsing and the `has_valid_coordinates` box test); `src/analysis.py:62-68` (`nighttime_offenses(..., mapped_only=True)`); `src/analysis.py:130` (ranked column):
  ```python
  d['has_valid_coordinates'] = (d['LAT'].between(*LAT_BOUNDS) & d['LON'].between(*LON_BOUNDS)).fillna(False)
  table['Valid mapped nighttime offenses'] = night.loc[night['has_valid_coordinates']].groupby('RPT Dist No')['UniqueNIBRNo'].nunique()
  ```
- What this code computes, in my own words: it takes each district's nighttime offenses and keeps the ones whose latitude and longitude both fall inside a large rectangle around greater LA. It then counts distinct offense IDs. Being inside the rectangle is the only test. It does not check whether the point is anywhere near the district the offense belongs to.
- Sanity checks: the value must be between 0 and the district's nighttime count (0182: 1,167 ≤ 1,167, so coverage is 100%). Overall: 178,921 of 179,209 = 99.84%, which matches `data_quality.json`. The district totals add to the overall total (178,921).
- Small test case and expected result (Check 2): I built 11 fixture rows and worked out the answer by hand before running them. Five rows should count: 22:00; `0000` midnight; 05:59 at the corner (33.5, −118.9); 18:00 at the corner (34.9, −117.5); and one row in a second district. Six should not: 06:00 (daytime), lat 34.9001, 0/0, blank, "abc", and a 2024 date. Expected: district 0100 = 4, district 0200 = 1, total = 5.
- Actual result: `{'0100': 4, '0200': 1}`, total 5 — **PASS**. Inclusive edges, midnight and every invalid-coordinate type behave as the spec says.
- Independent calculation (Check 1): I recomputed the number from the **raw CSV text** using only Python's `csv` module, without `clean_data.py`, the Parquet or the derived flags. I parsed `Date OCC`, `Time OCC`, `LAT` and `LON` myself. Result: 1,172 districts compared, **0 disagreements**. Totals match (178,921) and 0182 = 1,167 in both.
- Deeper check of assumption (b) (Check 3): for each district I took the median of its mapped points and measured each point's distance from it.
  - **499** "valid mapped" nighttime points are more than 10 km from their own district's center, and **265** are more than 20 km away. Reporting districts are only a few km across.
  - Example: district 0331 (Southwest), "3000 S Westview St", is plotted at (34.5683, −118.0878), which is near Palmdale and about 64 km from its district.
  - Other examples: Wilshire 0785 is plotted near Pomona (−117.733); Foothill 1685 is plotted in Lancaster; Harbor 0521 is about 100 km off.
  - These points pass the box, so they are counted as mapped. On the planned map they would show as offense dots in the wrong city.
  - Effect on the number: small overall (265 / 178,921 ≈ 0.15%). But "valid" overstates what is known, and a few districts' maps would be wrong.
- Deeper check of assumption (c): 21 "districts" have 2-digit codes `01`–`21`. They equal the AREA code, and their LOCATION is often just the area number, so they are area-level records rather than reporting districts. They hold 251 nighttime offenses, and **251 of the 288 unmapped nighttime offenses (87%)** are in these pseudo-districts (216 at 0/0 and 35 blank). They are scored and ranked (for example, `06` is rank 1087), and they add 21 rows to the 1,172-district percentile universe.
- What the evidence establishes and what remains uncertain: The number is **computed exactly as specified** (independent recount, 0 disagreements; fixture passes). Two judgment issues remain: "valid" does not mean "plausibly located", and area-level records are treated as districts. Not tested: filtered views (area, offense or date filters), and whether the far-off points are LAPD geocoding errors or real addresses. My 10/20 km thresholds use a flat-earth approximation and are a screen, not a boundary. I did not test a real district shapefile.
- Recommended change: **AUDIT-ZAYRA-01** (flag coordinates far from their own district) and **AUDIT-ZAYRA-02** (label or separate area-level 2-digit district codes). No change to the counting formula is requested.

Reproduce: `python audits/zayra/check_mapped.py --raw data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv` from the repo root (about 1 minute). The output is saved in `audits/zayra/check-output.txt`.

## My contribution

- What I personally checked and concluded: I chose an audit scope distinct from Olga (priority score), Ansel (recent offenses) and Caroline (persistence). I decided what the number and feature should mean for the planning manager, set the fixture's expected answers before running them, reviewed the far-off-coordinate examples, and judged that the formula is correct but "valid" and "district" are overstated.
- How AI helped, if used: Claude Code (Claude Opus) read the repository and teammates' audits, wrote `check_mapped.py`, ran the checks, and drafted this report and the change requests. I reviewed the code and results; the conclusions are mine.
