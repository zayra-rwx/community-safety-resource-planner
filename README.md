# Community Safety Resource Planner

## Streamlit Community Cloud deployment (Route B)

The dashboard supports LA street-lighting planning managers deciding which
reporting districts should receive on-site assessments first. Deploy the
existing Python app directly; no Sites plugin or JavaScript conversion is needed.

| Community Cloud setting | Value |
|---|---|
| Repository | `zayra-rwx/community-safety-resource-planner` |
| Branch | `codex/phase3-dashboard` |
| Main file path | `app.py` |
| Advanced settings: Python | `3.12` (validated locally with 3.12.14) |
| Dependencies | Root `requirements.txt`, which includes `requirements-phase3.txt` |
| Secrets | None required for the bundled dataset |

At https://share.streamlit.io/, sign in, choose **Create app** and **Yup, I have
an app**, then use the settings above and deploy. Community Cloud runs the app
from the repository root. Do not enter a localhost URL or a custom start command.
The deployment branch keeps `main` unchanged until team review and merge approval.

Required tracked runtime files are `app.py`, `dashboard_support.py`, `src/`,
`data/processed/lapd_nibrs_offenses.parquet`, `reports/phase2/data_quality.json`,
and `reports/phase2/data_dictionary.csv`. The raw CSVs and notebook environment
are not required at runtime. Do not commit credentials; `.streamlit/secrets.toml`
and `.env` files are ignored.

After deployment, compare the default KPIs against **179,209** nighttime reported
offenses, **1,164** eligible districts, **90.4%** mean persistence and **178,921**
mapped nighttime offenses. Test an area filter, district evidence, comparison,
CSV/JSON downloads, an empty selection and reset. External map tiles need network
access; other analysis and downloads use the bundled canonical dataset.

Deployment status: files prepared and tested locally; a live URL is not yet
recorded. Streamlit account sign-in and any required private-repository access
must be completed before cloud deployment. Keep the repository private; review
the app's sharing settings separately if a publicly accessible course demo is
required.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy


## Local Phase 3 dashboard

See [DASHBOARD.md](DASHBOARD.md) for installation, local startup, filters and downloads. On this Mac, run from the repository root:

```bash
../../.venv-phase3/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501.
## Phase 2 pipeline

The canonical Phase 2 pipeline produces full cleaned team data and reusable
backend analysis for street-lighting assessment. The local Phase 3 dashboard is described above.
The historical notebook documentation below describes the previous workflow;
use this section and `src/` for current data and metric definitions.

Reported-offense patterns and mapped streetlights identify places for further assessment. They do not establish that lighting conditions caused offenses or that additional lighting will reduce them.

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
