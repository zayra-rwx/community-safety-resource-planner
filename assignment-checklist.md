# Module 6 project data cleaning checklist

Project: Community Safety Resource Planner  
Student: Thomas Yin  
Branch: `jiatongy-svg`  
Branch URL: `https://github.com/zayra-rwx/community-safety-resource-planner/tree/jiatongy-svg`  
Commit ID: [fill after final commit]

The confirmed vision is Vision B: identify areas with recurring nighttime
reported offenses for further on-site lighting assessment. The confirmed
nighttime definition is 20:00 through 05:59. The NIBRS primary metric is
distinct `CaseNo`, with offense-record count as a secondary metric; Legacy
record counts remain separate.

## 1. State the project vision and question

Status: Done.

Evidence: `README.md`, Project vision; `data-fit.md`, Candidate Vision B. Main
comparison: distinct NIBRS cases by geography and the confirmed nighttime rule,
with offense records secondary and Legacy record counts shown separately.

## 2. Define one row

Status: Done.

Evidence: `README.md`, Data sources and versions. One NIBRS row is an offense
record identified by `UniqueNIBRNo`; multiple rows can share a `CaseNo`. One
Legacy row is a record identified by `DR_NO` and may include additional codes.

## 3. Preserve the source

Status: Done.

Evidence: `clean_data.py` reads the two unchanged CSVs and writes only to
`outputs/`. Source names and download dates are listed in `README.md`.

## 4. Inspect columns and types

Status: Done.

Evidence: `plan.md` gives rules for all 31 NIBRS and 28 Legacy source columns.
`clean_data.py` preserves identifiers as text, converts documented date and
numeric fields, and counts invalid conversions. See `outputs/run_summary.json`.

## 5. Standardize text

Status: Done.

Evidence: only outer whitespace is trimmed. NIBRS `AREA NAME` has 471,285
changed cells; identifiers and internal wording are preserved. See
`outputs/cleaning_decision_log.csv`.

## 6. Investigate duplicates

Status: Done.

Evidence: `UniqueNIBRNo` and `DR_NO` are separately checked for missing and
duplicate values. Repeated `CaseNo` values are expected multi-offense cases,
not duplicate rows. See the validation CSVs and record check `CaseNo 25164452`.

## 7. Handle missing data

Status: Done.

Evidence: missing values are preserved unless an explicit type conversion
turns an invalid value into missing. Counts for every source column appear in
`outputs/missing_values_before_after.csv`. No unknown value is filled from an
assumption.

## 8. Check suspicious values

Status: Done.

Evidence: early NIBRS dates, invalid or `0000` times, and missing, zero, or
out-of-range coordinates are flagged rather than deleted. See
`outputs/run_summary.json` and `outputs/record_checks.csv`.

## 9. Verify merges

Status: Not applicable.

Evidence: no merge is performed. The two reporting systems have different row
meanings and overlapping 2024 coverage, so they are cleaned separately. A join
or append would require a validated crosswalk and overlap policy.

## 10. Reconcile changes

Status: Done.

Evidence: NIBRS starts and ends with 471,285 rows. Legacy starts and ends with
1,004,894 rows. The difference is zero because cleaning flags questionable
records instead of dropping them. See `outputs/run_summary.json`.

## 11. Check calculations

Status: Done.

Evidence: record counts and distinct-case counts are not treated as
interchangeable. Missing group keys are retained in source-quality summaries.
Rows with coordinate issues remain in area summaries but must be excluded from
point mapping. See `plan.md` and `outputs/cleaning_decision_log.csv`.

## 12. Verify individual records

Status: Done.

Evidence: five approved checks cover an early date, zero coordinates, `0000`
time, a multi-offense case, and an additional Legacy code. Expected results
were approved before actual results were generated. All five comparisons are
in `outputs/record_checks.csv`.

## 13. Test reproducibility

Status: Done.

Evidence: `requirements.txt` records the dependencies. `README.md` gives the
command. A new Python process regenerated the evidence from all 1,476,179
source rows using the listed environment, and all assertions passed.

## 14. Document remaining limitations

Status: Done.

Evidence: the files describe reported offenses, not every offense; locations
are privacy-rounded; zero or missing coordinates cannot support point mapping;
`0000` may mean midnight or an uncertain time; clock time is not observed
darkness; the reporting systems differ; and neither source observes lighting
conditions, causal effects, project cost, or engineering feasibility.

## Codex suggestion checked by the student

Codex suggested preserving suspicious values and adding flags instead of
automatically deleting rows. The student approved five expected results before
the actual checks were generated, then checked those results and reconciled the
full-dataset row counts. All five records matched, and both source row counts
were unchanged. The student confirmed that suspicious values should remain
flagged because unusual does not necessarily mean incorrect and deleting them
could distort geographic and time patterns.
