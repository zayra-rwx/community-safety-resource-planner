# Community Safety Resource Planner: Streetlight Assessment

DSO 576, Team 12. This README covers **Module 6: Project Data Cleaning** (individual work by Zayra Martinez).

**Business question:** Which LAPD reporting districts show recurring nighttime reported offenses across months, so that the City of Los Angeles Bureau of Street Lighting can prioritize them for on-site lighting assessments?

**Main metric:** monthly nighttime offense counts by reporting district, reported with and without `Time OCC` = 0000, plus distinct-case counts. These counts are prioritization evidence. They are **not** crime rates, individual risk, or evidence that lighting causes offenses.

## Submission details

| Item | Value |
|---|---|
| Branch | `zayra-rwx` |
| Branch URL | https://github.com/zayra-rwx/community-safety-resource-planner/tree/zayra-rwx |
| Submitted commit ID | **PENDING** (filled in after the final commit) |

## Data source and version

| Item | Value |
|---|---|
| Dataset | LAPD NIBRS Offenses Dataset (Los Angeles Police Department), City of Los Angeles Open Data |
| Catalog page | https://catalog.data.gov/dataset/lapd-nibrs-offenses-dataset-2026-to-present |
| Portal page | https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep/about_data |
| Export endpoint | https://data.lacity.org/api/views/k7nn-b2ep/rows.csv?accessType=DOWNLOAD |
| Local file | `data/LAPD_NIBRS_Offenses_Dataset_20261004.csv` (178,693,032 bytes, 489,955 rows × 31 columns) |
| **SHA-256 (identifies our fixed dataset)** | `97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5` |
| Portal version | "Rows last updated" 2026-09-29 19:18:36 UTC. On 2026-10-04 the portal's row count (489,955), latest occurrence date (2026-09-19) and latest report date (2026-09-28 19:52:01) all matched this file. That is a consistency check, not proof that the contents are byte-identical. |
| Download date | **Unconfirmed.** The filename suffix `20261004` and the file's modified time suggest 2026-10-04, but neither proves it. |

The raw CSV is **not** in Git (`data/` is ignored). To reproduce, put the file at the path above and check its SHA-256. The code is written for this fixed version and does not pull later portal updates.

## Environment

- Python **3.14.6**
- Packages: `requirements.txt` (pandas 3.0.4, numpy 2.5.0, ipykernel 7.3.0 for running the notebook in VS Code)

```
python -m pip install -r requirements.txt
```

## How to run

From the project root:

**Script**

```
python clean_nibrs.py --input data/LAPD_NIBRS_Offenses_Dataset_20261004.csv --outdir outputs
```

The script prints the number of validation checks that passed and failed (currently 104 passed, 0 failed), then the SHA-256 of each output file. It exits with code 1 if any check fails.

**Notebook**

Open `Data Cleaning.ipynb` in VS Code, choose the Python 3.14 kernel, then click **Restart** followed by **Run All**. The notebook uses the same functions from `clean_nibrs.py` and rewrites `outputs/`.

**Reproducibility check**

Run the script into a separate temporary folder, such as `--outdir %TEMP%\nibrs_repro` in `cmd` or `--outdir $env:TEMP\nibrs_repro` in PowerShell. Then compare the printed hashes with the hashes shown at the end of the notebook. Do not delete `outputs/`.

## Expected output files (`outputs/`)

| File | Contents | In Git? |
|---|---|---|
| `nibrs_clean.csv` | All 489,955 cleaned rows: original columns (standardized/typed) plus flags and derived fields (≈250 MB) | No (ignored, too large; regenerate with the script) |
| `district_month_night.csv` | 21,290 observed (district, month) combinations of in-scope night offenses | Yes (narrow `.gitignore` exception) |
| `sample_cleaned_rows.csv` | 50 cleaned rows, mostly difficult cases, with `sample_reason` | Yes (narrow `.gitignore` exception) |
| `validation_summary.json` | All automated checks (expected / actual / passed), missing-value and flag tables, scope accounting, monthly totals, unassigned-district counts, and audits of the internal joins and lookups | Yes |
| `cleaning_decision_log.md` | Cleaning decision log: rule, reason, check, and that check's actual result | Yes |
| `record_checks.md` | Five record checks: original, expected, and actual values, and whether they match | Yes |

Expected SHA-256 of the outputs from a run on the fixed dataset:

```
a388510bc6bf4decdecec4ad6c3b84fedd94bd75b6213052582713b77a6553ad  cleaning_decision_log.md
a621b862544ff869ec5348cc66870ac867c9a0ccf767e2ff3245fe3a1675b887  district_month_night.csv
226f576c80fc87ed2580a1cf5598fff3bfeea35c5c279e97fa70976c7391923f  nibrs_clean.csv
5b75ad7c7377232a7a3b7c4006e264ca9e942c95eb7941f36ca32798275e44df  record_checks.md
7af0b0dacd3d1f50bd101c7376a54afafeb0dd2f37a02783e19f2b7a7f1cc37e  sample_cleaned_rows.csv
652097e5ba4f67201a65da3e9ddaddd492870594a802164903d008edc6dcb930  validation_summary.json
```

To read the CSVs without losing leading zeros, load them as text, e.g. `pd.read_csv(path, dtype=str)`. Excel drops leading zeros if a file is opened directly.

## Repository files for this assignment

- `plan.md`: inspection findings, column-by-column rules, and the decision record (written and reviewed before implementation)
- `clean_nibrs.py`: reusable cleaning, validation, and output logic
- `Data Cleaning.ipynb`: inspection, explanations, and validation (calls `clean_nibrs.py`)
- `requirements.txt`: dependencies
- `outputs/`: generated files (see above)

## Main cleaning rules (details in `plan.md` and `outputs/cleaning_decision_log.md`)

- **No rows are removed by cleaning.** One row is one offense (`UniqueNIBRNo`, unique). Repeated `CaseNo` values are multi-offense cases.
- **Analysis scope:** `Date OCC` ≥ 2025-01-01 (occurrence date), giving 380,091 rows. The 109,864 out-of-scope rows stay in the cleaned file with a `scope_reason`.
- **Night:** 20:00 inclusive to 06:00 exclusive, a fixed-clock approximation. `Time OCC` 0000 is kept and flagged, and counts are reported with and without it.
- **Missing values** are kept as missing. Missing weapon is not "no weapon".
- **Coordinates:** (0, 0) becomes missing. Points count as map-eligible only if they are present, numeric, finite, inside global bounds, and not (0, 0). Points outside a rough LA box or more than 5 km from their district's median are review flags only. A `False` distance flag means "not flagged". The 681 rows without a distance (558 area-only districts, 123 non-mappable) were not assessed. No coordinates or medians are invented.
- `TotalOffenseCount` and `TotalVictimCount` are case-level values and are never summed. No victim total is produced.
- September 2026 is calendar-partial (data ends 2026-09-19) and is kept. Any month can still receive late reports.
- **No external dataset is merged.** Month context is attached with three internal many-to-one left joins on `occ_year_month`. Each join is audited for row counts before and after, unmatched keys, and duplicate keys. The `CaseNo` and district-median lookups are audited too (`validation_summary.json` → `join_audits`, `lookup_audits`).

## AI assistance

- **ChatGPT** (OpenAI): planning and review. I used it to draft my instructions and to review the plan and results.
- **Claude Code** (Anthropic): implementation. It inspected the data, drafted `plan.md`, and wrote `clean_nibrs.py`, the Part 2 notebook sections, and the outputs.
- Codex was not used. Following the handout's alternative, I checked one cleaning decision suggested by Claude Code: the `location_suspected_generalized` flag. I checked district 0984 myself and found 5 records whose `LOCATION` equals `RPT Dist No`, all sharing (34.149, −118.4537), while the street-address records shown had varied coordinates. This supports the flag but does not prove how LAPD assigned those coordinates. I checked one district only and did not inspect a map. See the last cells of the notebook.

## Final submission checklist

- [x] Personal verification of the suggested cleaning decision (district 0984), written up in the notebook
- [x] Notebook re-run (Restart → Run All) after the targeted changes: 104 passed, 0 failed; original CSV unchanged; hashes match the list above
- [ ] Final commit pushed to `zayra-rwx`, and its commit ID recorded here and in the PDF
- [x] Instructor (`yalimohammadi`) access confirmed: collaborator check returned HTTP 204 (2026-10-04)
- [ ] PDF submitted on Gradescope
