# LAPD current NIBRS and Legacy crime-data cleaning plan

## Goal

Prepare both downloaded LAPD core datasets for transparent analysis and dashboard prototyping while preserving each source's row meaning. Clean the Current NIBRS and Legacy 2020–2024 files separately, evaluate their comparability, and show why the available evidence supports some parts of Candidate Visions A and B and not others.

## Non-negotiable rules

1. Keep both downloaded CSVs unchanged. Create a separate NIBRS cleaned DataFrame; clean Legacy in reproducible chunks and retain its audit summaries and sample unless a chunked output is explicitly approved.
2. Do not drop rows automatically. Flag questionable rows and explain any later exclusion from a specific analysis.
3. Do not change units, identifiers, or categories silently.
4. Preserve identifiers such as `CaseNo`, `UniqueNIBRNo`, `AREA`, `RPT Dist No`, and codes as text.
5. Report row counts, missing values, conversion failures, duplicates, and changed cells after each major transformation.
6. In NIBRS, treat `UniqueNIBRNo` as the offense-record identifier and `CaseNo` as the case identifier. In Legacy, preserve `DR_NO` and the separate `Crm Cd 1–4` structure. State which unit is being counted.
7. Keep `0000` times, early occurrence dates, and zero coordinates visible until their meaning is resolved.
8. Use reported-offense language. Do not describe the data as all crime or infer causation.
9. Do not append the two files or compare their raw row counts as one trend until the team validates a common unit, category crosswalk, transition boundary, and overlap policy.

## Human decisions to make before final analysis

| Decision | Why it matters | Initial notebook setting |
|---|---|---|
| Nighttime definition | A fixed clock window and actual darkness are not identical across seasons. | **Approved:** 8:00 p.m. through 5:59 a.m.; label this as clock time, not observed darkness. |
| Counting unit | One case can contain multiple offense rows. | **Approved:** NIBRS distinct cases are the primary metric and offense records are secondary; Legacy record counts remain separate. |
| Date scope | The RMS began in 2024, but the file includes older occurrence dates and extreme historical values. | Keep all rows; flag dates before 2000 and let the analyst choose the dashboard period |
| Geographic unit | Hundred-block locations are privacy-rounded, and coordinates can be missing or zero. | Compare LAPD area/reporting district first; use point locations only after quality filtering |
| Relevant premise categories | Lighting review may focus on outdoor settings, but the included categories are an analytical choice. | Display categories first; do not silently filter them |

## Proposed column rules

| Column | Meaning/type | Proposed cleaning rule | Validation |
|---|---|---|---|
| `CaseNo` | Case identifier | Keep as trimmed text. Never convert to a number. | Missing count and distinct count |
| `UniqueNIBRNo` | Offense-row identifier | Keep as trimmed text. Do not rebuild it. | Missing and duplicate counts |
| `Date Rptd` | Report timestamp | Parse to datetime with conversion failures reported. | Missing, min, max, failed parses |
| `Date OCC` | Occurrence timestamp | Parse to datetime. Flag unusually early dates rather than deleting them. | Missing, min, max, dates before 2000 |
| `Time OCC` | Local occurrence time, `HHMM` | Keep as four-character text. Validate hour/minute and add a numeric hour column. Keep `0000` visible. | Invalid formats and `0000` count |
| `AREA` | LAPD area code | Keep as trimmed text with leading zeros. | Missing and unexpected lengths |
| `AREA NAME` | LAPD area name | Trim outer whitespace only. | Changed values and unique categories |
| `RPT Dist No` | Reporting-district identifier | Keep as trimmed text with leading zeros. | Missing and unique count |
| `TotalOffenseCount` | Count | Convert to nullable numeric. Do not use as the row count without checking its meaning. | Missing, min, max, nonpositive values |
| `Group` | NIBRS group | Trim text; preserve observed categories. | Unique categories and missing count |
| `NIBR Code` | Offense code | Keep as text. Preserve missing values. | Missing and unique count |
| `NIBR Description` | Offense description | Trim outer whitespace; preserve wording. | Missing and code-description consistency review |
| `Crime Against` | Category | Trim text; preserve observed categories and missing values. | Unique categories and missing count |
| `Premise Cd` | Premise code | Keep as text. | Missing and unique count |
| `Premise Desc` | Premise description | Trim outer whitespace; preserve categories. | Missing and unique categories |
| `Weapon Used Cd` | Optional weapon code | Keep as text; missing can mean not applicable or unreported. | Missing and unique count |
| `Weapon Desc` | Optional weapon description | Trim text; do not fill from assumptions. | Missing and code-description review |
| `Status` | Status code | Keep as text. | Missing and unique count |
| `Status Desc` | Status description | Trim text; preserve categories. | Missing and code-description review |
| `TotalVictimCount` | Count | Convert to nullable numeric. Preserve zero. | Missing, min, max, negative values |
| `Victim Shot` | Yes/No category | Trim text; do not convert missing to `No`. | Unique categories and missing count |
| `Domestic Violence Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Hate Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Gang-related Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Transit-related Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Homeless-Victim Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Homeless-Suspect Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `Homeless-Arrestee Crime` | Yes/No category | Trim text; preserve source categories. | Unique categories and missing count |
| `LOCATION` | Privacy-rounded hundred-block location | Trim text. Do not interpret it as an exact address. | Missing and unique count |
| `LAT` | Latitude | Convert to nullable numeric. Flag missing, zero, nonfinite, or out-of-range values. | Missing, zero, min, max |
| `LON` | Longitude | Convert to nullable numeric. Flag missing, zero, nonfinite, or out-of-range values. | Missing, zero, min, max |

## Proposed Legacy column rules

| Column | Meaning/type | Proposed cleaning rule | Validation |
|---|---|---|---|
| `DR_NO` | Legacy record identifier | Keep as trimmed text; do not equate it automatically with NIBRS `CaseNo`. | Missing and duplicate counts |
| `Date Rptd` | Report date | Parse to datetime and report failures. | Missing, min, max |
| `DATE OCC` | Occurrence date | Parse to datetime; preserve the source date. | Missing, min, max, year distribution |
| `TIME OCC` | Local occurrence time | Keep as four-character text, validate `HHMM`, and add an hour column. | Invalid formats and `0000` count |
| `AREA` | LAPD area code | Keep as text with leading zeros. | Missing and unique count |
| `AREA NAME` | LAPD area name | Trim outer whitespace only. | Changed cells and unique categories |
| `Rpt Dist No` | Reporting-district identifier | Keep as text with leading zeros. | Missing and unique count |
| `Part 1-2` | Legacy crime-part category | Keep as categorical text; do not map to NIBRS `Group` without documentation. | Unique categories and missing count |
| `Crm Cd` | Primary legacy crime code | Keep as text. | Missing and unique count |
| `Crm Cd Desc` | Primary crime description | Trim outer whitespace; preserve wording. | Missing and code-description review |
| `Mocodes` | Modus-operandi codes | Keep as source text; do not split without a documented code reference. | Missing and format review |
| `Vict Age` | Reported victim age | Convert to nullable integer; flag nonpositive or implausible values rather than deleting. | Missing, min, max, flagged count |
| `Vict Sex` | Reported victim sex category | Trim text; preserve missing and observed categories. | Unique categories and missing count |
| `Vict Descent` | Reported victim-descent code | Keep as text; interpretation requires the source code reference. | Unique categories and missing count |
| `Premis Cd` | Premise code | Keep as text. | Missing and unique count |
| `Premis Desc` | Premise description | Trim outer whitespace; preserve categories. | Missing and unique categories |
| `Weapon Used Cd` | Optional weapon code | Keep as text; do not replace missing with `No weapon`. | Missing and unique count |
| `Weapon Desc` | Optional weapon description | Trim text; preserve missing values. | Missing and code-description review |
| `Status` | Status code | Keep as text. | Missing and unique count |
| `Status Desc` | Status description | Trim text; preserve categories. | Missing and code-description review |
| `Crm Cd 1` | First recorded crime code | Keep as text and compare with `Crm Cd`. | Missing and mismatch review |
| `Crm Cd 2` | Additional crime code | Keep as text; missing means no value is present, not zero. | Populated count and unique count |
| `Crm Cd 3` | Additional crime code | Keep as text. | Populated count and unique count |
| `Crm Cd 4` | Additional crime code | Keep as text. | Populated count and unique count |
| `LOCATION` | Privacy-protected location | Trim text; do not treat as an exact address. | Missing and unique count |
| `Cross Street` | Optional cross street | Trim text and preserve missing values. | Missing and unique count |
| `LAT` | Latitude | Convert to nullable numeric; flag zero, nonfinite, or out-of-range values. | Missing, zero, min, max |
| `LON` | Longitude | Convert to nullable numeric; flag zero, nonfinite, or out-of-range values. | Missing, zero, min, max |

## Cross-dataset comparability rules

1. Produce a separate cleaned table and validation report for each source.
2. Use source-specific row labels: NIBRS offense record, NIBRS distinct case, or Legacy record.
3. Show 2020–2024 Legacy and 2024–2026 NIBRS as separate reporting eras by default.
4. Do not use `DR_NO = CaseNo` as a general join. Only 518 values match exactly, and matching text alone does not prove the same real-world event.
5. Do not map `Crm Cd` to `NIBR Code` without a documented crosswalk.
6. Treat the 2024 overlap as a possible double-counting zone until a defensible overlap rule exists.

## Transformations to implement

1. Load every source column as PyArrow-backed pandas `string` so identifiers retain leading zeros without excessive memory use.
2. Create separate copies for the two sources.
3. Trim leading and trailing whitespace from text fields and record changed-cell counts by column.
4. Convert the two date columns and the four numeric measurement/count columns explicitly.
5. Validate `Time OCC` and add `Hour OCC` without replacing the source time.
6. Add review flags for dates before 2000, missing/zero/invalid coordinates, and `0000` time.
7. Add an editable nighttime flag based on the analyst's chosen hours.
8. Keep every source row. Create analysis-specific filters later and report their effects.
9. Compare schemas, coverage, and quality side by side without stacking the source rows.

## Required validation

- NIBRS row count remains 471,285 and Legacy row count remains 1,004,894 unless a future documented decision says otherwise.
- All source columns remain present in their respective cleaned tables.
- `UniqueNIBRNo` and `DR_NO` remain nonmissing and unique.
- `CaseNo`, `UniqueNIBRNo`, and `DR_NO` remain text.
- Missing-value changes are explained by explicit conversion or normalization rules.
- Date and numeric conversion failures are counted.
- The distribution of occurrence years, occurrence hours, premise categories, and coordinate-quality flags is reviewed visually for both files.
- The 2024 overlap and the different offense structures are documented before any cross-era comparison.
- At least five changed values are displayed before and after.
- The analyst explains whether the result still represents reported NIBRS offense records accurately.

## Output policy

The notebook keeps the NIBRS cleaned result only until its validation checkpoint, then releases it before processing Legacy in chunks. Saving large cleaned files is optional and disabled by default. If approved, use a chunked writer, save outside the Git repository or add the output to `.gitignore`, and do not commit downloaded or generated data.
