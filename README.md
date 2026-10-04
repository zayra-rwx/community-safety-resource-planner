# Community Safety Resource Planner - data cleaning

## Project vision

The confirmed vision is to help a City of Los Angeles street-lighting
program manager identify areas with recurring nighttime reported offenses for
further on-site lighting assessment. The results are a screening tool, not
evidence that lighting caused an offense or that a specific lighting project
should be approved.

## Data sources and versions

- City of Los Angeles, LAPD NIBRS Offenses Dataset, local download dated
  2026-09-09: `export.csv%3FaccessType=DOWNLOAD.csv`.
- City of Los Angeles, Crime Data from 2020 to 2024, local download dated
  2026-09-09: `export.csv%3FaccessType=DOWNLOAD (1).csv`.

The original CSV files are stored outside this repository and are never
modified. NIBRS has one row per offense record (`UniqueNIBRNo`); one `CaseNo`
can have multiple offense rows. Legacy has one row per `DR_NO` record and can
store additional offense codes in `Crm Cd 2` through `Crm Cd 4`. The sources
are cleaned and reported separately.

## Reproduce the submitted evidence

Create an environment and install the listed dependencies:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Place the two unchanged source CSV files in `../dataset`, or pass their folder
explicitly. Then run:

```text
.venv\Scripts\python clean_data.py
```

For a different source folder:

```text
.venv\Scripts\python clean_data.py --data-dir "C:\path\to\dataset"
```

The notebook `cleaning.ipynb` provides the visual walkthrough. The script is
the reproducible, non-interactive version used to generate the submitted
evidence.

## Expected output files

Running the script recreates these small files in `outputs/`:

- `run_summary.json`: source paths, row reconciliation, flag counts, and record-check total.
- `nibrs_validation.csv` and `legacy_validation.csv`: pass/fail validation results.
- `missing_values_before_after.csv`: missing counts for every source column.
- `cleaning_decision_log.csv`: each rule, reason, implementation, and check.
- `record_checks.csv`: five approved difficult cases with original, expected, actual, and match.
- `data_sample.csv`: no more than 50 cleaned rows, including every approved difficult case.

## Important analytical decisions

- No source rows are dropped during cleaning.
- Suspicious dates, `0000` times, and missing or zero coordinates are flagged.
- The confirmed nighttime rule is 8:00 p.m. through 5:59 a.m. This is clock
  time and does not prove that a location was dark.
- For NIBRS, the primary metric is distinct `CaseNo`; offense-record count is
  displayed as a secondary metric. Legacy record count is labeled and shown
  separately because Legacy does not have an equivalent validated case unit.
- The reporting systems are not appended into a single time trend.

## GitHub submission information

- Branch: `jiatongy-svg`
- Branch URL: `https://github.com/zayra-rwx/community-safety-resource-planner/tree/jiatongy-svg`
- Commit ID: `[fill after the final commit]`
