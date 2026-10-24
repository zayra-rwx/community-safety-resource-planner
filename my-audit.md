# Module 9 individual audit: date selection and recent nighttime offenses

- **Student:** Yu (Ansel) Lin (`anselyulin`)
- **Audit date:** October 23, 2026, America/Los_Angeles
- **Project:** Community Safety Resource Planner: Streetlight Assessment
- **Feature:** occurrence-date selection in the existing CLI; supporting backend filter checks
- **Number:** `Recent nighttime offenses`, with reporting district **1494 (Pacific)** as the focal example
**Audited version:** [`87a892a392727cfaff176d3c0fbbf6019a60eb4a`](https://github.com/zayra-rwx/community-safety-resource-planner/tree/87a892a392727cfaff176d3c0fbbf6019a60eb4a), the shared `main` baseline at inspection.

## 1. User, task and scope

The intended user is an LA Bureau of Street Lighting planning manager deciding
which reporting districts warrant on-site lighting assessment. The user needs to
select dates and distinguish recent recurring nighttime reports from the whole
selected period. An incomplete month should not silently become a supposedly
complete comparison month.

The audited version contains a working CLI and reusable backend, plus a
specification for a future Streamlit dashboard. This audit executes the existing
CLI and backend; it does not claim dashboard use or classify unbuilt dashboard
controls as broken features. The relevant requirement is in
[`BUILD_SPEC.md`, section 6](https://github.com/zayra-rwx/community-safety-resource-planner/blob/87a892a392727cfaff176d3c0fbbf6019a60eb4a/BUILD_SPEC.md#6-metric-definitions)
and the current README's canonical definitions.

Olga's available claim covers CLI prioritization and district 0182's **priority
score**. My distinct scope is **recent-period dates and counts**, supported by
source-text reconstruction, partial-month cases and small fixtures. Her score
reconstruction is not presented as my work. My claim and finding are recorded
in the [shared change-request record](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/change-requests.md); the request ID is **AUDIT-ANSEL-01**.

## 2. What the number should mean

`Recent nighttime offenses` is the integer number of **distinct nonmissing
`UniqueNIBRNo` values** in the latest **up to three complete calendar months**
contained in the selected available interval, after the applicable filters.

- Resolve inclusive occurrence dates, with start no earlier than January 1,
  2025 and end no later than the full canonical dataset's maximum occurrence
  date, currently September 19, 2026.
- Exclude partial start/end months. Keep complete months even if they contain
  zero qualifying offenses. A category/district selection must not redefine
  the available end date or recent window.
- Nighttime uses valid `Time OCC` HHMM from **18:00 through 05:59**, including
  recorded `0000`. Require a district and offense ID; missing coordinates do
  not disqualify a district-level count. Do not deduplicate on `CaseNo`.
- The unit is **reported offenses**, not cases, people, population risk, or a
  percentage. There is **no denominator**. The count must be a nonnegative
  integer no greater than qualifying nighttime offenses in the selected interval.
- With no complete month, the backend convention is recent count **0** with
  period `(None, None)`. That zero does not assert an absence of selected-period
  offenses. Persistence uses a different month rule and can include partial
  months; it is not the audited metric.

## 3. Inputs, method and reproducible evidence

Input is the committed full `data/processed/lapd_nibrs_offenses.parquet`:
**489,955 rows and 45 columns**. Its measured SHA-256 is
`36b136f5484624977f9d69d77e61bd12e82e24f6e1b1e9d50bb58a82153409b9`.
Execution used Python 3.12.14, Pandas 3.0.6, PyArrow 23.0.1 and pytest 9.0.2.

The independent reference reconstructs dates from `Date OCC_source` and validates
nighttime from `Time OCC_source`. It enumerates month boundaries with Python
`calendar`/`date` and counts distinct IDs with sets. Expected answers do not call
the production filtering, normalized date/night flags, month-window helpers, or
counting functions. These answers are then compared with real backend returns
and parsed real CLI stdout. All baseline files are checked before and after
execution. No team source, canonical data, or existing report was rewritten.

From the repository root, with the pinned environment installed:

```sh
python -m src.analysis --top 3
python -m src.analysis --start 2025-02-01 --end 2025-04-01 --top 3
python -m src.analysis --start 2026-09-01 --end 2026-09-19 --top 3
python audits/anselyulin/check_audit.py --output-dir ../module9-audit-rerun
python -m pytest -q
```

Use the project's configured Python executable for each command. The
[evidence README](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/README.md) supplies fresh-environment setup.
Evidence is committed at `dbe904c908e421353d03c5cd37ace8b0f32a872e`. The links below are pinned to that commit and work independently of this Markdown file's upload location. Committed evidence includes:

- [Executable check](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/check_audit.py),
  [structured results and source hashes](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/results.json), and
  [execution log](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/check-output.txt).
- [Actual CLI commands/stdout/stderr](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/cli-output.txt).
- [Independent district 1494 monthly breakdown](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/district-1494-monthly.csv)
  and [synthetic source input](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/synthetic-input.csv).
- [Existing regression-test output](https://github.com/zayra-rwx/community-safety-resource-planner/blob/dbe904c908e421353d03c5cd37ace8b0f32a872e/audits/anselyulin/baseline-tests.txt).

## 4. Expected versus actual results

Each row below independently compares all returned district counts; district
1494 is the compact numeric example. Six corresponding date/default cases were
also executed through the CLI and their displayed counts/endpoints checked.

| Selected interval | Expected recent window | District 1494 expected | District 1494 actual |
| --- | --- | ---: | ---: |
| Default: 2025-01-01 to available maximum | 2026-06-01 to 2026-08-31 | 131 | 131 |
| 2025-02-01 to 2025-04-01 | 2025-02-01 to 2025-03-31 | 116 | 116 |
| 2025-02-02 to 2025-04-01 | 2025-03-01 to 2025-03-31 | 62 | 62 |
| 2026-09-01 to 2026-09-19 | No complete month | 0 | 0 |
| 2026-08-01 to 2026-08-31 | 2026-08-01 to 2026-08-31 | 35 | 35 |
| 2025-01-01 to requested 2026-12-31 | End capped; 2026-06-01 to 2026-08-31 | 131 | 131 |

The default district result decomposes into **49 in June + 47 in July + 35 in
August = 131**. Its 22 September reports are excluded from the recent window
because source availability ends September 19. Across all **1,172** default
district rows, the independently recomputed recent total is **26,646**, matching
the backend. This is a new reconstruction, not just a copied validation-report
number. The audit checks this metric, not the priority-score formula.

Four additional backend scenarios passed: start clamped from 2024 to 2025,
Pacific-area selection, district 1494 selection, and a sparse offense-description
selection whose records end before the recent window. The latter still retains
the June-August comparison window and correctly returns zero. Area/district
selection leaves district 1494's recent count at 131.

### A hand-checkable small case

The following synthetic source records all share a case ID but have different
offense IDs. They are fixture data, not real offense identifiers. All are in
district 1494 except F10. F03 deliberately has missing coordinates.

| ID | Occurrence date | Time OCC | Interpretation |
| --- | --- | --- | --- |
| F01 | 2025-02-01 | 0000 | Qualifying midnight |
| F02 | 2025-02-28 | 2359 | Qualifying nighttime |
| F03 | 2025-03-01 | 0559 | Qualifying nighttime despite missing coordinates |
| F04 | 2025-03-31 | 1800 | Qualifying nighttime |
| F05 | 2025-04-01 | 1800 | Nighttime in a partial end month |
| F06 | 2025-03-15 | 0600 | Daytime boundary; exclude |
| F07 | 2025-03-16 | 1759 | Daytime boundary; exclude |
| F08 | 2025-03-20 | 2400 | Invalid clock; exclude |
| F09 | 2025-03-20 | 1900 | Distinct qualifying offense sharing the same case |
| F10 | 2025-03-20 | 1800 | Other district 0101; exclude from 1494 |
| F11 | 2025-04-30 | 1200 | Daytime record establishes fixture data availability |

For February 1-April 1, only February and March are complete: expected IDs are
F01, F02, F03, F04 and F09, so **5**. Starting February 2 excludes all of February
from the recent window: only March is complete, giving **3**. March 1-31 also
gives **3**. April 1 alone has no complete month, giving **0**.

A fifth fixture retains only F01, F05 and F11. For February 2-April 1, March is
still the valid recent period even though it has **0** offenses. This distinguishes
an eligible zero-offense month from the absence of a complete month. All five
predeclared expected results matched production behavior. The fixture arithmetic
was prepared and executed by Codex; human manual verification is not claimed.

## 5. Finding and requested change

**Numeric finding: PASS on tested cases.** Ten full-data backend scenarios,
six CLI scenarios, and five fixture scenarios agreed with independent expected
answers. The existing team suite also passed **40 tests**. No numeric change is
requested.

**Feature finding: works, with one presentation limitation.** For
`--start 2026-09-01 --end 2026-09-19 --top 3`, the CLI exits successfully. The
three displayed districts have selected-period nighttime counts **28, 28, 25**,
but recent counts **0, 0, 0** and recent endpoints **None/None**. These values
are mathematically correct. A manager could nevertheless misread the recent
zero as an absence of September reports, rather than an unavailable complete-month
comparison. The transcript records the actual output.

In the audited source, `recent_period` at `src/analysis.py:94-105` correctly
excludes partial months. `main()` at line 179 prints the DataFrame directly,
which exposes `None` without a contextual explanation. The requested improvement
**AUDIT-ANSEL-01** is to add:

> No complete months in the selected available interval; recent counts are 0 by convention.

Keep the API's `(None, None)`, zero-count convention, and ordinary selected-period
counts unchanged. This is a low-severity CLI usability recommendation; it is not
a demonstrated numeric error or a claim that future dashboard presentation
requirements already apply to a delivered CLI. A complete month with zero
offenses must still show its valid period. No implementation was made.

## 6. What this establishes and what remains uncertain

The evidence establishes agreement with the stated recent-window/count definition
for the tested data, boundary cases and filter selections. Overall conclusion:
**numeric pass; existing CLI feature passes with the presentation limitation
above**. Complete calendar months do not necessarily mean complete reporting.

The oracle shares the canonical processed input. It does not independently
verify the original raw download, upstream completeness, or whether preserved
source text matches every raw record. It does not establish population crime
rates, lighting conditions, causality, or the policy merit of the ranking. The
audit does not test all filter combinations, maps, exports, caching, future GUI
behavior, or the priority score.

PyArrow emitted sandbox-related macOS CPU-probe warnings in stderr; the logs
retain them. All commands completed successfully and assertions passed. These
environment warnings are not treated as a product finding.

## 7. Personal contribution and AI assistance

I requested and accepted the scope of this individual audit: date selection and
recent nighttime counts, separate from Olga's score audit. Codex inspected the
repository and specifications, wrote and ran the independent checks and CLI
commands, constructed fixture arithmetic, and drafted the evidence and prose.
No teammate's execution or analysis is claimed as my own.

This is a prepared report for my review before submission. I have not yet
independently rerun the checks or personally verified the fixture arithmetic;
no human manual calculation or live dashboard use is claimed. The technical
findings above describe the recorded execution; final judgments and explanations
remain my responsibility. No Gradescope submission, production-code fix, or
merge into team `main` was performed.
