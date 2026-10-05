# DSO576 Module 6 Cleaning

## Source, scope and preservation

- Team snapshot: LAPD_NIBRS_Offenses_Dataset_20261004.csv, adopted October 4, 2026 (America/Los_Angeles).
- Team described the source as updated September 29; upstream metadata timestamp was not independently reverified.
- Active input: ../LAPD_NIBRS_Offenses_Dataset.csv, a byte-identical copy of the team file.
- Raw SHA-256: 97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5
- Dimensions: 489,955 rows x 31 columns; cleaned: 489,955 rows x 44 columns.
- Recorded official source: https://catalog.data.gov/dataset/lapd-nibrs-offenses-dataset-2026-to-present
- Analysis uses Date OCC >= 2025-01-01, including all later dates in this fixed snapshot. The latest observed date is 2026-09-19; no complete-year claim is made for 2026.
- Nighttime is 18:00-05:59. This is an individual analytical choice; the team allows different analysis versions. Midnight is retained with a separate exclusion sensitivity.
- Original input remains unchanged. Previous versions and the earlier 2025-only results are archived under Project/backups/.

## GitHub submission details

- Personal branch: anselyulin
- Branch URL: https://github.com/zayra-rwx/community-safety-resource-planner/tree/anselyulin
- Submitted Module 6 commit ID: Pending - current assignment files have not been pushed.
- Instructor repository access: not independently confirmed.
- The existing branch HEAD 2c546442e4d83a1121bad685ece5c3226fed51a1 is the September 13 starting-point commit containing only members.md and project-start.md. It is not this assignment's submission commit.

## Run from the repository root (the local Project directory)

Python 3.14.7, pandas 3.0.3 and ipykernel 7.3.0 were used. Obtain the exact team file, place it at the active input path, and check its hash before running. A fresh website download may differ. The raw CSV belongs in the repository root, one level above module5_cleaning/. It is excluded from Git along with the full cleaned CSV and local backups. Use the team-provided snapshot shared in Discord; the 50-row sample is not a replacement for the full input.

```bash
python3 -m pip install -r module5_cleaning/requirements.txt
python3 module5_cleaning/clean_nibrs.py
python3 module5_cleaning/validate_nibrs.py
```

Open module5_cleaning/module5_cleaning.ipynb from its folder, restart the project kernel, Run All and save. All four code cells have been freshly executed. The historical module5 folder and notebook names remain for path compatibility. No unpack_data.py step is needed for the active uncompressed CSV.

## Expected outputs

outputs/cleaned_nibrs.csv, metrics_by_area.csv, metrics_by_area_excluding_midnight.csv, cleaning_run_metadata.json, full_validation.json, record_expectations.json, record_validation.csv and sample_50.csv.

The validator exits with status 1 if required checks fail. Five-record expectations are saved from raw data before reading the cleaned CSV. True raw whitespace is preserved in original_values.

## Verification

All 13 full-data checks and five record checks passed. A fresh notebook kernel and a separate Python cleaning process produced byte-identical cleaned and metric files. outputs/rerun_comparison.json records this audit, including boundary and midnight-denominator tests. It is not regenerated automatically by the normal commands.

Eligible period records: 380,091; nighttime records: 179,209; midnight records: 10,330; denominator without midnight: 369,761; night records without midnight: 168,879.

The 50-row cleaned sample includes the five validation cases, one double-zero-coordinate case and 44 seeded random selections. Full-data validation is separate from the sample.

## Limitations and submission

Row semantics, special code meanings, midnight meaning, historical dates and reporting completeness remain unresolved. Coordinate checks do not prove every point is in LA. Reported offenses are not population crime rates or evidence of lighting causality. No external merge was performed.

Module_6_Homework_Yu_Lin.pdf contains the local results and evidence, with the actual submission commit explicitly pending. Complete that field in the PDF and README after publishing the current files. No GitHub push or Gradescope submission was performed. The older exploratory nibrs_exploration.ipynb is not the current cleaning notebook and was not rerun. The obsolete module5_submission.zip is archived.
