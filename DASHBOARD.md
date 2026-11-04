# Local dashboard

## Deploy on Streamlit Community Cloud

Use repository `zayra-rwx/community-safety-resource-planner`, branch
`codex/phase3-dashboard`, main file `app.py`, and Python **3.12** in Advanced
settings. Root `requirements.txt` includes the pinned Phase 3 dependencies.
No API key or secrets are required. See the deployment section in `README.md`
for the complete configuration and post-deployment checks.

## Run locally

Run from the repository root with Python 3.12:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-phase3.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501. Stop with Ctrl+C in the terminal running Streamlit.

This Mac already has an isolated environment at ../../.venv-phase3. In the VS Code terminal opened at this repository, restart with:

```bash
../../.venv-phase3/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

The four tabs provide a priority worklist, focused district evidence, comparison of 2–5 districts, and methods/data quality. Use Focus district or select a table row to inspect evidence. Reset all filters restores the default view. Turn an All checkbox off and leave its selection empty to select no records. The top-N limit changes the overview and downloads; KPIs continue to summarize all eligible selected districts. Original backend ranks and scores remain unchanged by district selection or top-N.

Required runtime files:

- data/processed/lapd_nibrs_offenses.parquet
- reports/phase2/data_quality.json
- reports/phase2/data_dictionary.csv

The app validates the full Parquet against the field dictionary and quality report. Missing or inconsistent files produce an actionable error. The canonical backend and data remain the source of calculations. Maps contain only aggregated coordinates rounded to 3 decimal places and counts. External map tiles require internet; worklists, charts and downloads remain available when tiles fail.

The CSV download contains the displayed overview in its current order, with all 15 backend columns and unrounded values. Import reporting district codes as text to retain leading zeros. The JSON includes filters, scope counts, source hash, load time, app hash/version, backend revision and method definitions.

Streetlight assets were unavailable for this MVP. This local implementation follows BUILD_SPEC.md and uses reported-offense frequency and persistence to identify places for assessment; it does not measure lighting conditions or establish causation.

Verify:

```bash
../../.venv-phase3/bin/python -m pytest -q
```
