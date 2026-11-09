# Community Safety Resource Planner: Streetlight Assessment

- **Live app:** https://community-safety-resource-planner-dso576.streamlit.app/ (no sign-in needed)
- **Demo video (4:05, with subtitles):** https://drive.google.com/file/d/11IM9l-sum0Tx78rnS_JavcsQW43WmbPW/view?usp=sharing

## Intended users and decision

The dashboard is for an LA Bureau of Street Lighting program manager deciding which
LAPD reporting districts should receive on-site lighting assessments first. It ranks
districts by how often and how consistently nighttime offenses are reported there.

Reported-offense patterns identify places for further assessment. They do not
establish that lighting conditions caused offenses or that additional lighting will
reduce them.

## Data scope

- **Source:** [LAPD NIBRS Offenses Dataset](https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep)
  from the City of Los Angeles open data portal.
- **No random sample or row limit.** The app loads all 489,955 cleaned offense rows.
- **Date subset:** metrics use offenses that occurred from January 1, 2025 through
  September 19, 2026 (380,091 rows). Older records stay in the file but never
  enter the metrics or the app's date range.
- **Default results:** 179,209 nighttime offenses (18:00 through 05:59) across 1,164
  reporting districts. Of those offenses, 178,921 have valid map coordinates.
- **Map:** coordinates are rounded to 3 decimal places for display. Offenses without
  valid coordinates still count for their district but do not appear on the map.

## Current limitations

- **No streetlight data.** No approved asset file was available, so rankings use
  reported-offense frequency and persistence only, and the map shows approximate
  offense locations, not lighting conditions.
- Reported offenses are not all actual offenses, and recent months can still receive
  late reports. The newest month is partial.
- No verified district population exists, so no population-adjusted rates are shown.
- Some locations are approximate, and some two-digit district codes are area-level
  entries ranked as recorded.
- Recorded midnight (0000) may be a source convention for unknown times; it is kept
  and flagged.
- Rankings support assessment prioritization only. They are not predictions, danger
  labels or enforcement recommendations.

The app's **Methods and Data Quality** tab has the full list.

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
| `docs/technical-notes.md` | Deployment, metric definitions, backend API and earlier workflow |

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

Metric definitions, deployment settings and the backend API are in
[docs/technical-notes.md](docs/technical-notes.md).
