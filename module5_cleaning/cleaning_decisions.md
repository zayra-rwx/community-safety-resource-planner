# Cleaning Decisions

## Scope and fixed input

- Project question: from January 1, 2025 onward, how are nighttime reported offense records distributed across LAPD areas, and which areas merit further on-site lighting assessment?
- Analysis period: `Date OCC >= 2025-01-01`, with no 2026 cutoff. Include all later occurrence dates present in the fixed team snapshot. This follows the team scope restated by Zayra on October 4 and confirmed by the user before this rerun. The observed maximum date does not prove complete reporting.
- Night definition: 18:00 through 05:59, a modifiable analysis assumption.
- Source: `../LAPD_NIBRS_Offenses_Dataset.csv`.
- Current team snapshot: `LAPD_NIBRS_Offenses_Dataset_20261004.csv`, adopted on 2026-10-04, America/Los_Angeles. The active local copy retains the original input filename. The upstream download/update time is not independently verified.
- SHA-256 recorded for the input: `97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5`.

## Rules

| Rule | Reason | Affected fields | Verification |
|---|---|---|---|
| Read every column as string first | Protect identifiers and codes from numeric coercion | All columns; especially `CaseNo`, `UniqueNIBRNo`, `AREA`, `RPT Dist No`, codes | Compare values and identifier sets before/after |
| Strip leading/trailing whitespace; convert empty-after-strip values to missing | `AREA NAME` has trailing spaces on every row; blank values should be explicit missing values | All text fields | Before/after blank counts and examples |
| Do not fill weapon blanks as `None` or `No weapon` | A blank is not evidence that no weapon was involved | `Weapon Used Cd`, `Weapon Desc` | Missingness remains visible |
| Parse dates with `format='mixed'`; retain original cleaned text and add parsed columns | Dates contain month-name timestamps and may be missing | `Date Rptd`, `Date OCC` | Parse failure counts before/after |
| Flag `Date OCC` year <= 1900; do not rewrite it | This is a manual-review threshold, not proof of error | `Date OCC` | Count and sample flagged rows |
| Validate `Time OCC` as four-digit HHMM and derive hour | Supports reproducible day/night grouping | `Time OCC` | Invalid and missing time counts |
| Preserve `0000` and add a midnight flag | Midnight is a valid time and its source meaning is uncertain | `Time OCC` | Compare night metrics including/excluding midnight |
| Convert coordinates to numeric and flag missing, double-zero, and outside global range | Coordinates are needed only for mapping and 0,0 is not a valid LA location | `LAT`, `LON` | Counts for each flag; no automatic row deletion |
| Do not deduplicate `CaseNo` | One case can contain multiple offense records | `CaseNo`, `UniqueNIBRNo` | Case count versus offense-record count |
| Require `UniqueNIBRNo` to be unique and check full-row duplicates | This is the available row-level identity evidence | `UniqueNIBRNo`, all columns | Independent set and duplicate checks |
| Do not merge external lighting data in this assignment | No merge key or lighting source is part of this build | None | Merge is documented as not applicable |
| Compute area metrics only with valid area, occurrence date, and time | Makes numerator and denominator explicit; eligibility is tested independently with parsed `year >= 2025` | `AREA`, parsed occurrence date, parsed time | Independent metric recomputation and date-boundary tests |
| Exclude midnight from sensitivity denominator as well as numerator | A midnight-excluded proportion must remove `0000` records from both parts | `Time OCC`, area metrics | Independent denominator and numerator recomputation |
| Compare raw and cleaned records by `UniqueNIBRNo` | Row positions are not the identity contract | `UniqueNIBRNo`, original fields, analysis flags | Full-data mismatch counts in `full_validation.json` |
| Protect raw input and output paths | Cleaning must never overwrite the original CSV | Input/output paths and SHA-256 | Path guard and hash before/after checks |
| Do not call results population crime rates or causal lighting evidence | No population denominator, lighting condition, reporting process, or causal design is present | Metric outputs and report | Review wording in report |

## Revision log

| Date | Change | Reason |
|---|---|---|
| 2026-09-27 | Initial rules recorded before cleaning | Build-stage decision record |
| 2026-09-27 | Replaced inclusive `2025-12-31 00:00:00` endpoint with `< 2026-01-01`; removed midnight records from both sensitivity denominator and numerator; added ID-based full validation and sample evidence | External review found 583 omitted December 31 records, including 299 nighttime records, and an invalid sensitivity denominator |
| 2026-10-04 | Adopted the team-provided 20261004 snapshot; archived the previous source and outputs; reran the unchanged cleaning rules and full-data verification | Team requested a common data snapshot. Current raw and cleaned row count: 489,955. |
| 2026-10-04 | Removed the January 1, 2026 upper cutoff; renamed period flags and metric columns to 2025 onward. Recorded this rule before rerunning. Preserved true raw whitespace in five-record evidence and saved raw-derived expectations before reading the cleaned output. | User confirmed alignment with the team's January 1, 2025 onward scope. |

## Unresolved items

- The exact semantic definition of one row and special code meanings require an official data dictionary; this build does not invent those meanings.
- The source's completeness and reporting changes over time are not established by this CSV alone.
- The meaning of `0000`, historical occurrence dates, and coordinate 0,0 requires source-owner confirmation.
- Reported offenses alone cannot establish that inadequate lighting caused an offense or that every offense is suitable for a lighting intervention.
