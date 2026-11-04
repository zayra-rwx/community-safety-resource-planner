# Module 9: Yu (Ansel) Lin's audit evidence

Audited baseline: `87a892a392727cfaff176d3c0fbbf6019a60eb4a` on team `main`.
Scope: existing CLI date selection and **Recent nighttime offenses**, with
district **1494** as the focal numeric example. Backend calls additionally
check area/district/category invariance. This is separate from Olga's
priority-score audit. The baseline has a CLI/backend and a future dashboard
specification; no dashboard interaction is claimed.

## Reproduce

From the repository root, use a dedicated Python >=3.11 environment and the
team's unchanged pinned requirements. One macOS/Linux setup is:

```sh
python3 -m venv ../module9-audit-venv
../module9-audit-venv/bin/python -m pip install -r requirements-phase2.txt
../module9-audit-venv/bin/python audits/anselyulin/check_audit.py --output-dir ../module9-audit-rerun
../module9-audit-venv/bin/python -m pytest -q
```

On Windows use the environment's `Scripts/python.exe` executable. Use a new
environment path if that example path is already occupied. `--output-dir` keeps
the committed evidence intact; omitting it regenerates this folder's evidence.
Run against the unchanged baseline source/data, with these audit-only files
added. No raw download, cleaner execution, or baseline-report regeneration is
needed. The script rejects a changed baseline file before calculation and
checks its SHA-256 again afterward.

## Evidence

| File | Purpose |
| --- | --- |
| `check_audit.py` | Executable oracle and actual CLI/backend comparisons |
| `results.json` | Source hashes, versions, resolved windows, counts and case outcomes |
| `check-output.txt` | Complete audit execution log |
| `cli-output.txt` | Commands, exit codes, actual stdout and stderr for six CLI cases |
| `district-1494-monthly.csv` | Independent monthly count breakdown; June 49 + July 47 + August 35 = 131 |
| `synthetic-input.csv` | Eleven synthetic source records for the hand-checkable fixture |
| `baseline-tests.txt` | Execution of the existing team regression tests |

The oracle reads the **committed full Parquet**, independently reconstructs
dates from `Date OCC_source` and HHMM validity/nighttime from `Time OCC_source`,
enumerates whole months with Python `calendar`/`date`, and counts distinct
offense IDs with Python sets. It does not reuse production filtering, normalized
dates, nighttime flags, month-window helpers, or counting functions for expected
answers. Pandas/PyArrow provide file IO and actual backend execution. Production
`clean_offenses` is used only to construct the *actual* side of the synthetic
tests; the synthetic reference reads the fixture's original strings separately.
Expected fixture counts were written before the first execution.

All 10 full-data backend scenarios, six CLI scenarios and five fixture scenarios
passed. All 40 existing regression tests passed. No numeric defect was found.
`AUDIT-ANSEL-01` recommends a clearer CLI explanation when no complete months
exist; it preserves the zero numeric result and existing backend contract.

The environment emitted PyArrow CPU-probe warnings because sandboxed macOS
disallowed `sysctlbyname`. They are retained verbatim in the logs. CLI exit
codes were zero and every assertion passed; those warnings are not classified
as a product defect.

## Interpretation and attribution

The reference is independent of production *calculation*, but shares the
committed processed input. This audit does not reverify the raw file, source
completeness, reporting delays, all possible filters, or any future dashboard,
export or map. Complete calendar months need not be fully reported months.

Yu Lin requested and accepted this audit scope. Codex inspected code, wrote and
ran checks, constructed fixture arithmetic, and drafted findings and prose.
Yu Lin has subsequently confirmed verification of the report's findings and
takes responsibility for the final judgments and explanations. This does not
claim personal live-dashboard use or specify an unreported verification method.
No Gradescope submission is performed as part of this audit.
