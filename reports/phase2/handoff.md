# Phase 2 validation and proposed commit

Prepared October 18, 2026. Branch: `Olga`. No dashboard, commit, push or merge.

## Verified source

`data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv` matches all supplied values:
178,693,032 bytes; SHA-256
`97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5`;
489,956 physical lines, 489,955 parsed records, 31 columns. Exact source columns
and hash are recorded in `data_quality.json`. The cleaner rechecks the hash before
writing outputs. Both raw CSV files remain ignored and unchanged by this work.

Canonical output: `data/processed/lapd_nibrs_offenses.parquet`, Parquet/Zstandard,
489,955 rows, 45 columns, 24,459,185 bytes. This is the full processed source,
not a sample, and is below GitHub's per-file limit.

## Data quality

| Measure | Count |
|---|---:|
| Raw / processed rows | 489,955 / 489,955 |
| Exact duplicates found / removed | 0 / 0 |
| Repeated offense IDs | 0 |
| Repeated case values / rows retained in those cases | 44,390 / 94,224 |
| Invalid or missing occurrence dates | 0 |
| Before January 1, 2025 | 109,864 |
| Invalid or missing times | 0 |
| Recorded midnight values, full history | 15,333 |
| Missing district keys / offense IDs | 0 / 0 |
| Missing / nonnumeric coordinates | 131 / 0 |
| Zero / nonzero out-of-box coordinates | 550 / 1 |
| Total invalid coordinates, full history | 682 |
| Nighttime records, full history | 231,811 |
| Qualifying nighttime offenses, 2025 onward | 179,209 |
| Qualifying mapped nighttime offenses | 178,921 |
| Qualifying mapped coverage | 99.8393% |

Dates span 1800-01-06 through 2026-09-19. Historical anomalies are retained,
excluded from 2025-forward metrics. Report-date missingness is separate from
occurrence-date eligibility; source-column missingness is in the quality JSON.

## Validation

- Automated suite: **40 passed**, Python 3.14.7, Pandas 3.0.6, PyArrow 23.0.1,
  pytest 9.0.2. Run `python -m pytest -q` in the configured environment.
- Full cleaning completed and source verification passed.
- Full-data reconciliation passed: 1,172 districts, 21 eligible months, 24,612
  district-month rows; monthly, district, mapped and category counts reconcile.
- Tested each non-district category filter on the full data; comparison selection
  preserves original ranks/scores; empty selections return valid empty tables.
- Recent full months: June 1–August 31, 2026; 26,646 nighttime offenses.
- CLI example `python -m src.analysis --top 3` completed successfully.
- `git diff --check` passed. No streetlight distances or spatial tests were
  fabricated; the approved streetlight file is absent.

| Rank | District | Area | Score (display only) | Nighttime offenses | Active / eligible months |
|---|---|---|---:|---:|---:|
| 1 | 0182 | Central | 87.679181 | 1,167 | 21 / 21 |
| 2 | 1494 | Pacific | 87.627986 | 1,097 | 21 / 21 |
| 3 | 0636 | Hollywood | 87.576792 | 978 | 21 / 21 |

Stored results retain unrounded scores. Average-rank percentiles mean a district
with maximum persistence can have a percentile below 1 when many districts tie.

## Every proposed commit file

| File | Purpose |
|---|---|
| `.gitignore` (modified) | Ignore pytest caches; retain existing raw exclusions |
| `README.md` (modified) | Canonical setup, definitions, commands, API and limitations; preserve historical workflow |
| `requirements-phase2.txt` | Pinned backend and test dependencies |
| `src/__init__.py` | Importable backend package |
| `src/config.py` | Approved source contract, paths, bounds and score weights |
| `src/clean_data.py` | Verified reproducible full-data cleaning and quality/dictionary generation |
| `src/analysis.py` | Loading, filtering, counts, monthly metrics, summaries, comparison and ranking |
| `src/validate_phase2.py` | Reproducible full-data reconciliation and aggregate examples |
| `tests/test_phase2.py` | Automated boundary, invariance and error-handling tests |
| `data/processed/lapd_nibrs_offenses.parquet` | Canonical full processed team dataset |
| `reports/phase2/data_quality.json` | Source verification, quality counts and processed metadata |
| `reports/phase2/cleaning_decisions.md` | Explicit cleaning decisions and conflicts resolved with older notebook |
| `reports/phase2/data_dictionary.csv` | All source, derived and audit field definitions/types |
| `reports/phase2/backend_validation.json` | Measured full-data reconciliation results |
| `reports/phase2/district_ranking.csv` | Full ranked district output, unrounded |
| `reports/phase2/example_comparison_monthly.csv` | Monthly comparison for the first three districts |
| `reports/phase2/offense_summary.csv` | Distinct nighttime offense counts by source description |
| `reports/phase2/premise_summary.csv` | Distinct nighttime offense counts by premise |
| `reports/phase2/handoff.md` | This validation summary and commit manifest |

Proposed commit message: `Complete Phase 2 canonical cleaning and assessment backend`.
Only these Phase 2 files are proposed. `.vscode/`, both raw CSVs, the existing
notebook and its outputs, and every `BUILD_SPEC.md` are excluded.

## Remaining limitations

The approved streetlight GIS input is absent; asset validation, EPSG:2229 nearest
distance and 150-foot counts await that file. This does not block nonspatial
Phase 2 outputs. No population denominator is available. Reported versus actual
offenses, reporting delays/system changes, approximate coordinates and a broad
geographic screen limit interpretation. Midnight is preserved as recorded, not
inferred. The Downloads BUILD_SPEC's backend definitions are followed with the
user's Phase 2 scope; Phase 3 UI requirements are outside this work.

Reported-offense patterns and mapped streetlights identify places for further assessment. They do not establish that lighting conditions caused offenses or that additional lighting will reduce them.
