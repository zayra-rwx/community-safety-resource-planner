# Community Safety Resource Planner: Streetlight Assessment

A Streamlit dashboard that helps an LA Bureau of Street Lighting planning manager
decide which LAPD reporting districts should receive on-site lighting assessments
first. It compares recurring nighttime reported-offense patterns using the full
cleaned LAPD NIBRS dataset.

Reported-offense patterns and mapped streetlights identify places for further assessment. They do not establish that lighting conditions caused offenses or that additional lighting will reduce them.

Streetlight asset data was unavailable for this MVP. Rankings use reported-offense frequency and persistence; the map shows approximate offense locations, not measured lighting conditions.

## Links

- **Live app:** https://community-safety-resource-planner-dso576.streamlit.app/ (no sign-in needed)
- **Demo video (4:05, with subtitles):** `demo_video.mp4` in the submission zip; also
  on branch [`jiatongy-svg`](https://github.com/zayra-rwx/community-safety-resource-planner/tree/jiatongy-svg/demo-video)
  with its subtitle file and script

## Run the dashboard

Use Python 3.11 or later. From the repository root (Windows PowerShell; use
`.venv/bin/python` on macOS/Linux):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-phase3.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens at http://localhost:8501. It needs only three committed files:
`data/processed/lapd_nibrs_offenses.parquet`, `reports/phase2/data_quality.json`
and `reports/phase2/data_dictionary.csv`. The raw CSV is not needed to run it.

## Deploy on Streamlit Community Cloud

Use repository `zayra-rwx/community-safety-resource-planner`, branch `main`, main
file `app.py`, and Python 3.12 or 3.13 under Advanced settings. No secrets are
needed. Cloud installs from `requirements.txt`, which includes the pinned dashboard
requirements, and redeploys when `main` changes.

## Dashboard views

- **Priority Overview:** ranked districts, totals, an approximate offense map, and
  the worklist CSV and metadata downloads.
- **District Evidence:** one district's monthly counts, persistence, and offense and
  premise composition.
- **Compare Districts:** 2 to 5 districts on the same evidence, with original ranks.
- **Methods and Data Quality:** limitations, how zeros are handled, definitions,
  the full-source audit and data provenance.

District labels such as `0182 · Central · near S Flower St` combine the official
code and LAPD area with the most common street recorded in that district. The street
is a landmark we derive, not an official name. The first two digits of a code are
the LAPD area; two-digit codes are area-level entries. Downloads keep plain codes,
so import `RPT Dist No` as text to retain leading zeros.

## Repository layout

| Path | Contents |
| --- | --- |
| `app.py` | Streamlit UI and session state |
| `src/analysis.py`, `src/clean_data.py`, `src/config.py`, `src/validate_phase2.py` | Backend: cleaning, metrics, validation |
| `src/dashboard/` | Adapters, charts, map, export, loading, validation, settings and styling |
| `.streamlit/config.toml` | Theme and app settings |
| `tests/` | Backend, label and app tests |
| `data/processed/`, `reports/phase2/` | Canonical data, quality report, dictionary and validation evidence |
| `audits/<name>/`, `change-requests.md` | Individual Module 9 audits and the shared change requests |
| `BUILD_SPEC.md`, `project-start.md`, `members.md` | Project specification, vision and team |

## Troubleshooting

- **Changes under `src/` don't appear, or an `AttributeError` names a new function:**
  stop the server with `Ctrl+C` and start it again. Refreshing the browser does not
  reload those modules.
- **A named data error appears on launch:** restore the file it names from `main`.
  The app never falls back to a sample or other dataset.
- **The map background is blank:** basemap tiles load from the internet. Metrics,
  charts and downloads keep working without them.
- **Some map points seem missing:** the map opens on where most points are. Zoom out;
  the caption under the map says how many plot outside the opening view.
- **Results are all 0:** a filter has "All" unticked with nothing chosen, which means
  no records. Tick "All" or use **Reset all to defaults**.

The sections below document the backend data pipeline, metric definitions and
historical notebook workflow. Use `src/` and these sections for current definitions.

## Canonical data and reproducibility

- Raw: `data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv` (178,693,032 bytes;
  489,956 physical lines; 489,955 data rows; 31 source columns).
- SHA-256: `97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5`.
- Processed: `data/processed/lapd_nibrs_offenses.parquet`, all 489,955 rows,
  45 source/derived/audit columns, approximately 24.46 MB with Zstandard compression.
- The cleaning command checks the exact approved source before writing outputs.
  Raw CSVs remain ignored, read-only, and outside ordinary Git; no LFS setup is needed.
- `data/raw/lapd_nibrs_offenses_raw.csv` and all existing notebook artifacts are
  preserved, but are not inputs to this Phase 2 pipeline.

Use Python 3.11 or later. From the repository root, use this setup path (Windows
PowerShell; use `.venv/bin/python` on macOS/Linux):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt
.venv\Scripts\python.exe -m src.clean_data
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m src.validate_phase2
.venv\Scripts\python.exe -m src.analysis --top 10
```

Place the approved CSV at the exact raw path first. Dependencies are pinned in
`requirements-phase2.txt`: Pandas for tabular analysis, PyArrow for Parquet, and
pytest for tests. Existing Jupyter dependencies remain in `requirements.txt`.
Cleaning regenerates the Parquet, data-quality JSON and dictionary; validation
regenerates aggregate example outputs and reconciliation results. The decision
log is maintained documentation, not overwritten by cleaning.

## Canonical definitions

- One record represents one NIBRS offense. Count distinct nonmissing
  `UniqueNIBRNo`; never deduplicate on `CaseNo`. Remove only completely identical
  source rows. Retain and flag nonidentical repeated offense IDs for review;
  attribution-based analysis rejects those conflicts. The approved input has none.
- Trim surrounding text whitespace; preserve missingness, identifier formatting
  and category distinctions. Convert dates, numeric counts and coordinates to
  appropriate nullable types. Source date/time/coordinate text is retained in
  audit columns. See `reports/phase2/data_dictionary.csv` for every column.
- Preserve full history in Parquet. Metrics use inclusive occurrence dates from
  January 1, 2025 through the available maximum (September 19, 2026). Missing or
  invalid dates, times, district keys or offense IDs cannot enter district metrics.
- Nighttime is **18:00–05:59** using valid HHMM: hour 00–23, minute 00–59.
  Preserve `0000` as midnight, flag it separately and include it in nighttime
  counts. This supersedes the historical notebook's 20:00 start and treatment
  of midnight. Invalid times remain in quality totals, excluded from metrics.
- Coordinates pass a broad inclusive box: latitude **33.5–34.9**, longitude
  **−118.9–−117.5**. Missing, nonnumeric, zero or outside-box values fail. These
  offenses still contribute to district metrics; they cannot enter map/spatial
  inputs. The box is a screening check, not a verified city boundary.
- Geographic unit: `RPT Dist No`; persistence unit: calendar month. Monthly
  outputs include zero-count months, including partial months intersecting the
  selected interval. Eligible months are the number of those calendar months;
  active months have at least one qualifying offense.
- **Persistence = active months / eligible months**; **average monthly nighttime
  offenses = nighttime offenses / eligible months**. Return zero for a zero
  denominator. No population-adjusted rates are calculated.
- **Priority score = (0.60 × frequency percentile + 0.40 × persistence percentile)
  × 100**. Percentiles use ascending average rank divided by district count
  (`rank(method="average", pct=True)`), within [0, 1]. Districts represented after
  date/area/offense/crime-against/premise filters form the universe, including
  districts with only daytime offenses. A district with zero nighttime offenses
  has score zero. District display/comparison selection never changes that
  universe, percentile, score, or rank. Compute without rounding, then sort score,
  nighttime count, persistence descending and numeric district code ascending
  (source string breaks any residual tie).
- Recent counts use the latest up to three **complete calendar months** contained
  in the selected interval, capped by the canonical maximum date, before
  categorical filtering. Zero-offense months remain eligible. Partial start/end
  months are excluded. Return period labels; no complete months means zero and
  no period. The default recent period is June 1–August 31, 2026.
- Streetlight proximity, when an approved file is supplied, means nearest mapped
  light distance and number of mapped lights within **150 feet**, projected to
  **EPSG:2229 (US feet)**. No approved GIS input exists here; proximity is
  unavailable and is not implemented or included in scoring.

## Reusable backend

```python
from src.analysis import (
    Filters, load_processed, filter_offenses, nighttime_offenses,
    count_nighttime_offenses, monthly_counts, ranked_districts,
    category_summary, compare_districts, recent_period,
)

data = load_processed()
filters = Filters(start="2025-01-01", end="2026-09-19", areas=("Central",))
ranking = ranked_districts(data, filters)
monthly = monthly_counts(data, filters)
mapped = nighttime_offenses(data, filters, mapped_only=True)
categories = category_summary(data, "NIBR Description", filters)
premises = category_summary(data, "Premise Desc", filters)
comparison = compare_districts(data, ranking.head(2)["RPT Dist No"], filters)
```

Pass the canonical full frame and explicit `Filters` to each function. Filter
options are `start`, `end`, `areas`, `districts`, `codes`, `descriptions`,
`crime_against`, and `premises`. `None` means unrestricted; an empty tuple means
no selections and produces empty results. Multiple category filters intersect.
Functions return new dataframes/scalars/dictionaries and do not mutate inputs.
Do not prefilter the canonical frame to selected display districts before ranking.
Unknown premises are labeled `Unknown` only in summary output.

## Reports and limitations

`reports/phase2/` contains `data_quality.json`, `cleaning_decisions.md`,
`data_dictionary.csv`, `backend_validation.json`, `district_ranking.csv`,
`example_comparison_monthly.csv`, `offense_summary.csv`, and `premise_summary.csv`.
Tests cover time boundaries, duplicates, coordinate eligibility, dates, zero-filled
months, denominators, score weights, deterministic ties, comparison invariance,
categorical filters, empty results and source verification failures.

Reported offenses are not all actual offenses. Reporting-system changes, historical
date anomalies, approximate locations, missing data, and midnight source conventions
limit interpretation. The newest month may be incomplete; complete calendar months
can still have reporting delays. The coordinate box does not establish jurisdiction.
Multiple area labels in a district are shown together rather than silently choosing
one. No verified district population denominator or approved streetlight asset file
is available. Spatial calculations and tests await that file. No causal effect,
danger prediction or enforcement recommendation is inferred.

## Historical notebook workflow (preserved)

## Project

This project cleans the LAPD NIBRS Offenses Dataset to support prioritization of geographic areas for on-site street-lighting assessments. The analysis does not claim that lighting conditions caused reported offenses.

## Data source

- **Dataset:** LAPD NIBRS Offenses Dataset.
- **Official source:** https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep
- **Raw filename:** `lapd_nibrs_offenses_raw.csv`.
- **Download date:** October 3, 2026 (confirmed by Olga).
- **Version (SHA-256):** `8003ffd45a3e17938913b5794a5bad0a8078bfafec736591123005212614d1cf`.
- **Coverage:** Supplied export, not the earlier 2,500-row sample; completeness against the live dataset is unverified.

The original raw file is not modified and is excluded from Git.

## Files

- Cleaning notebook: `notebooks/data_cleaning.ipynb`.
- Raw data: `data/raw/lapd_nibrs_offenses_raw.csv`.
- Cleaned sample: `data/cleaned/lapd_nibrs_cleaned_sample.csv`.
- Decision log: `data/cleaned/cleaning_decision_log.csv`.
- Record verification: `data/cleaned/five_record_checks.csv`.
- Dependencies: `requirements.txt`.

## How to run

1. From the repository root, install dependencies with `pip install -r requirements.txt`.
2. Place the original LAPD CSV at `data/raw/lapd_nibrs_offenses_raw.csv`.
3. Open `notebooks/data_cleaning.ipynb` and select the Python environment with the installed dependencies.
4. Run all cells from top to bottom.
5. Find the three generated outputs in `data/cleaned/`.

## Expected outputs

- `lapd_nibrs_cleaned_sample.csv`: Up to 50 cleaned records with selection reasons.
- `cleaning_decision_log.csv`: Cleaning rules, reasons, affected counts, and limitations.
- `five_record_checks.csv`: Expected and actual results for five individual record checks.

Audits, reconciliation, metrics, and compact district/month previews are displayed in the notebook. Complete result tables remain in memory; their shapes appear in section 11. The full cleaned master remains in memory as `df`. No builder script is needed.

## Submission information

- **Branch:** `Olga`.
- **Branch URL:** https://github.com/zayra-rwx/community-safety-resource-planner/tree/Olga.
- Verified analysis commit: 23b559daa432455ea86fa43a7403a1cf6f4fa055
