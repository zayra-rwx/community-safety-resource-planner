# Module 6 Data Cleaning Plan — LAPD NIBRS Offenses (Streetlight Assessment)

**Student:** Zayra Martinez · **Branch:** `zayra-rwx` · **Status:** IMPLEMENTED in `clean_nibrs.py` and `Data Cleaning.ipynb` (2026-10-04). Results are in `outputs/`. The record-check expectations in §8 were written before implementation and were not changed.

Project: Community Safety Resource Planner: Streetlight Assessment (Team 12).
Business question: *Which LAPD reporting districts show recurring nighttime reported offenses across months, so the Bureau of Street Lighting can prioritize them for on-site lighting assessments?*
Main metric: nighttime offense counts by reporting district and month (`RPT Dist No` × `occ_year_month`), reported both including and excluding `Time OCC = 0000`, with distinct-case counts alongside. These counts are prioritization evidence. They are **not** crime rates, individual risk, or proof that poor lighting causes offenses.

The §1 findings were measured on the **full** local CSV (all 489,955 rows) during planning, using read-only scripts. The CSV, the notebook, and `.gitignore` have not been modified.

---

## 0. Source and version

**Our dataset is the fixed local file, identified by its SHA-256.** It is the data for this assignment and all later project work. Portal updates after this snapshot are not pulled in.

| Item | Value | Basis |
|---|---|---|
| Local file | `data/LAPD_NIBRS_Offenses_Dataset_20261004.csv`, 178,693,032 bytes, LF line endings | |
| **SHA-256 (identity of our data)** | `97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5` | Computed locally. Recomputed before and after every run to show the file is unchanged. |
| Dataset | LAPD NIBRS Offenses Dataset, Los Angeles Police Department | Portal metadata API `https://data.lacity.org/api/views/k7nn-b2ep.json` |
| Catalog link (Phase 1) | https://catalog.data.gov/dataset/lapd-nibrs-offenses-dataset-2026-to-present | Phase 1 document. The portal metadata says the dataset was renamed on 2026-08-18. |
| Portal page | https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep/about_data | Link you provided. The metadata API confirms the ID `k7nn-b2ep`. |
| Export endpoint | `https://data.lacity.org/api/views/k7nn-b2ep/rows.csv?accessType=DOWNLOAD` | HEAD request (2026-10-04): HTTP 200, `text/csv`, Last-Modified `Tue, 29 Sep 2026 19:18:36 GMT` |
| Portal "rows last updated" | 2026-09-29 19:18:36 UTC | Metadata API |
| Snapshot identifier | `20261004`, from the filename | **The download date is unconfirmed.** The file's modified time (2026-10-04 19:16 local) matches the filename, but neither proves when it was downloaded. |

**Consistency checks, not proof of an exact match:** on 2026-10-04, the live portal reported 489,955 rows, max `date_occ` 2026-09-19, and max `date_rptd` 2026-09-28 19:52:01. Our file has the same three values. That agreement is consistent with our file coming from the portal version updated 2026-09-29. It does not prove the contents are byte-identical, because no checksum was published. The SHA-256 above is what identifies our data.

Load rule (already in the notebook): `pd.read_csv(path, dtype="string")`. This keeps leading zeros and stops pandas from guessing types. **It does not keep every original value literally:** `read_csv` still turns its default missing-value tokens (empty fields, `NA`, `NULL`, …) into NA. A literal reload (`keep_default_na=False`) showed that in this file only empty fields became NA, and every non-missing value matches the literal text. `raw` is never modified; all work happens on copies.

---

## 1. Inspection findings (full dataset)

### 1.1 Baseline counts (your initial results are confirmed)
- 489,955 rows × 31 columns. **0** exact duplicate rows.
- `UniqueNIBRNo`: no missing values and no repeats, so 489,955 distinct values. 440,121 distinct `CaseNo` values.
- `UniqueNIBRNo` always parses as `CaseNo_NIBRCode_seq`. The CaseNo part matches `CaseNo` in every row, and the code part matches `NIBR Code` in every row. When `NIBR Code` is missing (1,149 rows), the code part is empty (e.g. `251604056__1`).
- Read in as text, the dataset has no blank or whitespace-only strings. Missing values are true NA.

### 1.2 Dates and times
- `Date OCC` parses for 489,955 of 489,955 rows using `%Y %b %d %I:%M:%S %p`. `Date Rptd` parses for every non-missing value; 7,787 are missing.
- `Date OCC` ranges from 1800-01-06 to 2026-09-19 00:00. Rows by year: before 2024: 6,824; 2024: 103,040; 2025: 223,307; 2026: 156,784. Three rows fall before 1900 (1800 ×2, 1826 ×1). They are flagged as implausible and are out of scope anyway.
- **End of the observed data:** in-scope occurrences run at about 500–620 per day through 2026-09-18. 2026-09-19 has **8 observed records**, all with `Time OCC` 0000, and no later occurrence dates exist. Report dates continue to 2026-09-28 for offenses that occurred earlier. Why the last occurrence date is 2026-09-19 is not documented. All 8 records are kept as observed data.
- `Time OCC` matches `^([01]\d|2[0-3])[0-5]\d$` in every row. **`Time OCC` equals the HH:MM inside `Date OCC` in 489,955 of 489,955 rows.** 13,590 `Date OCC` values have non-zero seconds, which `Time OCC` does not carry.
- **0000** appears in 15,333 rows (10,330 in scope); every one has `Date OCC` time `12:00:00 AM`. Hour 0 contains 28,130 rows versus 14,548 in hour 1, so exact-midnight values are heaped. **Heaping alone does not tell us whether these are true midnight events, rounded times, or unknown times, and the source documentation doesn't say.** So 0000 is flagged and reported both ways (§5). **1200** is also heaped: 13,314 rows (9,333 in scope). It is daytime under our definition, so it doesn't affect nighttime counts. Overall, 36% of times end in :00 and 86% fall on a multiple of 5 minutes.
- `Date OCC` > `Date Rptd` in 523 rows (29 in scope), mostly legacy rows whose report time is midnight. They are flagged and kept.
- **Reporting delay (lag = `Date Rptd` − `Date OCC`), in scope:** median 0.13 days. 87.6% are reported within 7 days, 93.9% within 30, 96.4% within 90, and 97.9% within 365. For occurrences in the first half of 2025: 86.2% within 7 days, 92.5% within 30, 95.2% within 90, 97.3% within 365. So **every month, including older ones, can still receive late reports**; recent months have had the least time to do so.

### 1.3 Geography
- `AREA` (21 two-character codes) maps one-to-one to `AREA NAME` (21 names). Every `AREA NAME` is right-padded with spaces to 20 characters.
- `RPT Dist No`: 1,183 distinct values. **558 rows (504 in scope) contain only the 2-digit area code** instead of a 4-digit district; 502 of the 504 in-scope rows belong to C-prefixed cases. Every 4-digit district's first two digits equal `AREA`, and no district maps to more than one area. In scope there are 1,151 distinct 4-digit districts.
- `LAT`/`LON` in scope:
  - 109 rows missing (always both).
  - 478 rows at exactly (0, 0), 427 of them on C-prefixed cases. They cluster in January–March 2025: 161, 154, and 105 rows, then single digits per month.
  - 379,504 rows with coordinates present and non-zero.
- **Basic range check:** 120 in-scope rows with coordinates (161 in the full dataset) fall outside a rough box around the City of LA (lat 33.70–34.35, lon −118.70 to −118.15).
- **Distance review:** this is each row's distance from the median point of its district's street-address rows. The typical (median) distance in scope is 0.32 km. 1,848 in-scope rows are more than 5 km away, and that includes all 120 rows outside the box. A large distance is a reason to review a point, **not proof that it is wrong**.
- **Suspected generalized locations:** 10,412 rows (8,217 in scope) have `LOCATION` equal to `RPT Dist No` (e.g. `0246`). Among those rows, each district has exactly one coordinate pair. That *suggests* a district-level point rather than a hundred-block location, but the source does not document it. This is suggestion S1 (§12), for you to verify. Another 111 rows have `LOCATION` equal to the 2-digit area code.

### 1.4 Offense and case fields
- **`TotalOffenseCount` is a case-level value repeated on each offense row.** Reconciliation of the earlier "55 vs 80":

  | Calculation | Records used | Result |
  |---|---|---|
  | First-row method (used in my first draft) | All 440,121 cases in the full file. Each case's `TotalOffenseCount` was taken from its **first row only** and compared with its row count in the full file. | 55 cases mismatch (15 have more offenses than rows, 40 fewer) |
  | **Row-level method (adopted)** | Every row in the full file. A row mismatches if its `TotalOffenseCount` ≠ the number of rows with that `CaseNo` in the full file. | **96 rows in 80 cases** |
  | Row-level method, in scope | The same rule, applied to the 380,091 in-scope rows | **96 rows in 80 cases.** Identical, because all mismatching cases are in scope and no case has rows both in and out of scope (0 such cases). |

  The 25-case difference comes from the 68 cases whose `TotalOffenseCount` **varies across their own rows**. In 25 of them, the first row happened to match the row count while another row didn't. The first-row method missed those; the row-level method catches all 68. The plan uses the row-level rule (`toc_mismatch`).
- **`TotalVictimCount` is case-level as well.** 17 cases (all in scope) have conflicting values across their rows. Summing over in-scope rows gives 389,767, which counts multi-offense cases more than once. **No victim total will be produced.** Picking one value per case would mean choosing arbitrarily among the conflicting values, and victims are outside the metric anyway.
- 1,374 in-scope rows are identical to another row except for `UniqueNIBRNo` (same case, same NIBR code, different sequence number). They are kept, because each has its own offense ID.
- `NIBR Code` is missing in 1,149 rows (72 in scope). These rows carry older-style descriptions, and their `Group` and `Crime Against` are missing too. In 16 rows, the code at the end of the description differs from `NIBR Code`.
- `Group` is missing in 15,480 rows (10,153 in scope), mostly codes 26F and 90C. `Crime Against` has 4 values; `Person, Property, Society` is a real combined category.
- `NIBR Description`: 82,058 rows contain doubled internal spaces. Collapsing them reduces 2,409 distinct descriptions to 2,398.
- `Premise Cd` is a coarse code (e.g. `01` covers many transit stations). 22,744 rows have `Premise Desc` without `Premise Cd`. 962 rows (7 in scope) use legacy descriptions such as `101 - STREET`.
- `Weapon Used Cd`/`Weapon Desc` are missing together in 345,971 rows (277,461 in scope). Codes can hold several values (`08, 06`). Code `00` = **Unknown** (3,243 rows), which is different from missing. **Missing ≠ "no weapon".**
- `Status` → `Status Desc`: codes 10 and 20 each map to two descriptions. 2 rows have a description but no code.
- The eight Yes/No flags contain only `Yes`/`No`, with no missing values.
- `CaseNo` lengths range from 8 to 14 characters. In-scope prefixes: numeric 300,431, `C` 79,543, `MC` 116, `RFC` 1. The meaning of the prefixes is undocumented.
- Within-case inconsistencies (in scope): `Date OCC` differs in 3 cases, `RPT Dist No` in 4, and `LOCATION`/`LAT` in 1. They are flagged, and each row keeps its own values.

### 1.5 Existing notebook review
`Data Cleaning.ipynb` (7 cells) loads the CSV as strings into `raw` and `nibrs`, runs `info()`, counts missing values, checks duplicates and IDs, and records the findings in Markdown. Every number it states was re-verified and is correct, so **no corrections are needed**. All existing cells, outputs, and Markdown are kept unchanged, and new sections are appended below them.

---

## 2. Cleaning vs. analysis scope

1. **Cleaning covers all 489,955 rows and removes none.** There are no exact duplicates, no repeated IDs, and no unparseable dates. Cleaning standardizes text, converts types, and adds flags. Output: `nibrs_clean` with 489,955 rows.
2. **The analysis scope is `Date OCC >= 2025-01-01 00:00`**, based on occurrence date, not report date. Out-of-scope rows stay in `nibrs_clean` with a reason code.

| Reason code | Rule | Rows |
|---|---|---|
| `pre_2024` | `Date OCC` < 2024-01-01 (includes the 3 rows flagged as before 1900) | 6,824 |
| `2024_pre_rms` | 2024-01-01 ≤ `Date OCC` < 2024-03-07 | 1,351 |
| `2024_rms_transition` | 2024-03-07 ≤ `Date OCC` < 2025-01-01 | 101,689 |
| **Out of scope total** | | **109,864** |
| **In scope** | `Date OCC` ≥ 2025-01-01 | **380,091** rows / 344,186 distinct cases |

Check: 380,091 + 109,864 = 489,955. The code re-asserts every count in this table.

3. **Eligibility flags inside the scope** decide which metric a row feeds. They never delete a row:
   - `district_eligible`: `RPT Dist No` has 4 digits (379,587 in-scope rows).
   - `night`: §5.
   - `map_eligible`: §4.

---

## 3. Column-by-column rules

Original columns keep their names. New columns use `snake_case`. "Flag" means a new boolean column; the original value is kept.

| # | Column | Type | Missing / blank | Text / categories | Validity checks / suspicious values | Action | Reason | Verification |
|---|---|---|---|---|---|---|---|---|
| 1 | CaseNo | string | 0 | Prefixes C, MC, RFC, OA, LASPD; lengths 8–14 | Equals the CaseNo part of UniqueNIBRNo | Keep. Add `case_prefix`. | Leading characters and prefixes are meaningful. Repeats are legitimate multi-offense cases. | 440,121 distinct; prefix counts |
| 2 | UniqueNIBRNo | string (key) | 0 | `case_code_seq` | Unique | Keep. Assert unique after each step. | Defines one row. | `is_unique` |
| 3 | Date Rptd | datetime (naive local) | 7,787 | — | 0 parse failures; report before occurrence: 523 rows | Convert. Keep NA. Flag `rpt_before_occ`. Add `report_lag_days`. | Used only for delay diagnostics. | Failures = 0; NA count unchanged |
| 4 | Date OCC | datetime (naive local) | 0 | — | 0 parse failures; 3 before 1900; none after 2026-09-19 | Convert. Flag `occ_implausible_year`. Add `occ_date` and `occ_year_month` (`YYYY-MM`). | Sets scope and month. | Failures = 0; min/max; counts by year |
| 5 | Time OCC | string `HHMM` | 0 | Leading zeros kept | Valid HHMM in every row; equals Date OCC HH:MM in every row | Keep as string. Add `occ_minute_of_day`, `time_is_0000`, `time_is_1200`. Flag `time_conflict` if any disagreement appears. | 0000 is kept and flagged, not set to missing. | Regex and agreement re-check (expected 489,955) |
| 6 | AREA | string (2 characters) | 0 | `01`–`21` | 1-to-1 with AREA NAME | Keep. | Grouping key. | 21 values |
| 7 | AREA NAME | string | 0 | Padded with spaces to 20 characters | 21 values | Strip leading and trailing whitespace. | Formatting only. | Before/after list 21 → 21; mapping unchanged |
| 8 | RPT Dist No | string (4 characters) | 0 NA; 558 area-only values | Leading zeros kept | Prefix = AREA | Keep. Flag `rpt_dist_area_only`. `district_eligible=False` for those rows. **No district is guessed.** | A 2-digit value is an area, not a district. | Flag counts; unassigned totals by area and month |
| 9 | TotalOffenseCount | Int64 | 0 | — | Case-level; row-level mismatch: 96 rows / 80 cases | Convert. Flag `toc_mismatch` (row-level rule, §1.4). **Never sum.** | Case attribute repeated on each offense row | 0 failures; 96 / 80 |
| 10 | Group | string | 15,480 | A/B | Missing mostly for 26F and 90C | Keep NA. Do not fill. | Not used. Filling it would be an assumption. | NA before = after |
| 11 | NIBR Code | string | 1,149 | 58 codes | 16 conflicts with the description's code | Keep. Flag `nibr_code_missing`, `nibr_desc_code_conflict`. Rows **stay counted**. | A missing code doesn't mean "not an offense". | Counts |
| 12 | NIBR Description | string | 0 | Doubled spaces | 2,409 → 2,398 distinct | Collapse whitespace and strip. **No case changes.** | Consistent display without merging categories. | The 11 merged pairs listed |
| 13 | Crime Against | string | 2,297 | 4 categories | — | Keep NA. | Valid category values. | Value counts before = after |
| 14 | Premise Cd | string | 22,853 | Coarse code | One code has many descriptions | Keep. | Premise Desc is the analytic field. | NA unchanged |
| 15 | Premise Desc | string | 109 | Legacy upper-case values | — | Keep NA. No recoding. | No crosswalk; very few rows in scope. | Counts |
| 16–17 | Weapon Used Cd / Weapon Desc | string | 345,971 (same rows) | Multi-value lists; `00` = Unknown | — | Keep NA. **Never fill with "None".** | Missing ≠ no weapon. | NA unchanged; same rows asserted |
| 18–19 | Status / Status Desc | string | 1,044 / 1,042 | 10/20 → 2 descriptions each | 2 description-only rows | Keep. | Not used. | Crosstab |
| 20 | TotalVictimCount | Int64 | 0 | — | Case-level; 17 cases with conflicting values | Convert. Flag `tvc_conflict`. **Never sum; no victim total.** | Repeated, and sometimes conflicting, case attribute | 0 failures; 17 cases |
| 21–28 | Victim Shot … Homeless-Arrestee Crime | boolean | 0 | Yes/No only | — | Yes → True, No → False. Assert no other values. | Typed booleans; nothing lost | True counts = original Yes counts |
| 29 | LOCATION | string | 0 | 10,412 equal RPT Dist No; 111 equal AREA | — | Keep. Flag `location_suspected_generalized`. | Possible district-level placeholder (unverified; S1) | Counts |
| 30–31 | LAT / LON | Float64 | 131 NA; 550 at (0, 0) | — | Missing, zero, outside the basic range, far from the district median | Convert. **(0, 0) → NA**, recorded by `coord_zero`. No replacement coordinates. Other flags are separate (§4). | (0, 0) is not a location in LA. | NA +550, explained; flag counts |

**Derived columns:** `case_prefix`, `occ_date`, `occ_year_month`, `occ_minute_of_day`, `time_is_0000`, `time_is_1200`, `time_conflict`, `report_lag_days`, `rpt_before_occ`, `occ_implausible_year`, `rpt_dist_area_only`, `district_eligible`, `toc_mismatch`, `tvc_conflict`, `nibr_code_missing`, `nibr_desc_code_conflict`, `same_code_repeat_in_case`, `case_field_inconsistent`, `location_suspected_generalized`, `coord_missing`, `coord_zero`, `coord_outside_basic_range`, `coord_far_from_district_review`, `map_eligible`, `scope_reason`, `in_scope`, `night`, `calendar_coverage`.

---

## 4. Coordinates: separate flags, no automatic exclusion by distance

District summaries use `RPT Dist No`, not coordinates. **No coordinate flag removes a row from any district count.** Each flag is its own boolean, so they can overlap:

| Flag | Rule | In scope | Use |
|---|---|---|---|
| `coord_missing` | LAT/LON NA in the source | 109 | Not mappable |
| `coord_zero` | LAT = 0 and LON = 0 in the source (set to NA after cleaning) | 478 | Not mappable |
| `coord_outside_basic_range` | Present, non-zero, and outside lat 33.70–34.35 / lon −118.70 to −118.15 | 120 | Review flag |
| `location_suspected_generalized` | `LOCATION` = `RPT Dist No` | 8,217 (8,121 with coordinates) | Review flag (S1) |
| `coord_far_from_district_review` | More than 5 km from the median of the district's present, non-zero, non-generalized rows | 1,848 | **Review flag only.** Distance doesn't prove an error. |

Basic validity flags added at implementation: `coord_nonnumeric`, `coord_nonfinite`, and `coord_out_of_global_bounds` (latitude outside ±90 or longitude outside ±180). **`map_eligible`** means the coordinates are present, numeric, finite, within global bounds, and not (0, 0). That gives 379,504 in-scope rows. Passing these checks does **not** establish that a location is accurate. The three review flags are carried alongside, and the dashboard step decides how to show them. No coordinate is corrected or imputed. District medians are used only to compute the review flag; they are never written into a row.

---

## 5. Nighttime definition (decided)

- **`night` = Time ≥ 20:00 OR time < 06:00** (20:00 inclusive, 06:00 exclusive, wrapping past midnight). It is computed from `occ_minute_of_day`: `>= 1200 or < 360`.
- It is documented as a **fixed-clock approximation of nighttime**. It doesn't follow seasonal sunset and sunrise, and clock time is not a measure of lighting conditions. Sunset/sunrise-based definitions are **deferred**.
- **0000 handling:** 0000 rows are kept and flagged, and they fall inside the window, so `night=True` for them. Totals are computed **before** any exclusion:
  - In-scope rows with `Time OCC` = 0000: **10,330**.
  - Night rows including 0000: **137,415**.
  - Night rows excluding 0000: **127,085** (= 137,415 − 10,330).
- Both versions are reported throughout. The plan makes no claim about what 0000 means, beyond noting the heaping.
- **Time OCC vs Date OCC check:** the code asserts `Time OCC == Date OCC.strftime("%H%M")` for every row. 489,955 matches are expected. Any mismatch is flagged `time_conflict` and reported, not corrected.

---

## 6. Year-month field and monthly district summary

- `occ_year_month = Date OCC.strftime("%Y-%m")`, derived only after date validation. Years stay separate (`2025-01` ≠ `2026-01`).
- **Calendar coverage (`calendar_coverage`)** describes the month itself:
  - `complete` for 2025-01 through 2026-08.
  - `partial` for **2026-09**: the last occurrence date in our file is 2026-09-19.

  All September records are kept, including the 8 on 2026-09-19, and its observed counts are reported as-is: 10,097 in-scope rows; 3,643 night rows including 0000; 3,446 excluding.
- **Reporting completeness** is treated separately from calendar coverage. Every month, older ones included, can still receive late reports (§1.2). The summary therefore carries **`days_since_month_end_to_last_report`**: the number of days from the month's last day to 2026-09-28, the latest report in our file. It is descriptive context. **No month is labeled final.** Limitations will say that recent months have had the least time to collect late reports.
- **Output `district_month_night.csv` (observed combinations only)** has one row for each (`RPT Dist No`, `occ_year_month`) with at least one in-scope, district-eligible night offense including 0000. Columns:
  - Keys: `RPT Dist No`, `AREA`, `AREA NAME`, `occ_year_month`.
  - Month context: `calendar_coverage`, `days_since_month_end_to_last_report`.
  - Offense counts: `night_offenses_incl_0000`, `night_offenses_excl_0000`, `night_offenses_0000`.
  - Distinct-case counts: `night_distinct_cases_incl_0000`, `night_distinct_cases_excl_0000`.

  During planning this produced 21,290 combinations across 1,140 districts, with a total of 137,243 night offenses including 0000. A combination with no records is **absent, not zero**. The complete district × month grid is **deferred**.
- **Missing grouping keys:**
  - `occ_year_month` and `AREA` are never missing.
  - 504 in-scope rows (`rpt_dist_area_only`) have no district. 172 of them are night rows including 0000, and 166 excluding. They are left out of `district_month_night.csv` and reported by area and month in `validation_summary.json` and in the notebook.
- **Reconciliation:** the district-month total plus the unassigned total must equal the in-scope night total. Including 0000: 137,243 + 172 = 137,415. Excluding 0000: 126,919 + 166 = 127,085. In addition, 3 random cells are recounted directly from `raw` with plain string filters, independently of the cleaning code.
- **Persistence thresholds are deferred** and are not part of this assignment. No threshold is built into the code.

---

## 7. Counting units and case-level totals

- **Offense count** = rows (`UniqueNIBRNo`).
- **Distinct cases** = distinct `CaseNo` among the same rows. They are labeled "distinct cases" and **not** assumed to be distinct incidents.
- In scope, 67,490 rows belong to cases with more than one row, and 1,374 rows repeat a code within their case. Comparing the two counts shows where multi-offense cases make the offense count larger.
- `TotalOffenseCount` and `TotalVictimCount` are **never summed** across rows. No victim total is produced; 17 cases have conflicting victim counts (§1.4).

---

## 8. Five record checks (expected results written before transformation; actual results pending)

| # | UniqueNIBRNo (raw index) | Why difficult | Key original values | Expected result and reason |
|---|---|---|---|---|
| R1 | `25088246_290_2` (1) | Multi-offense case: 3 rows (`_13A_0` at index 0, `_290_2`, `_23F_1` at index 11526); case-level totals repeated | Date OCC `2025 May 15 02:21:00 PM`, Time `1421`, AREA `05`, AREA NAME `Harbor` + 14 spaces, RPT `0558`, TotalOffenseCount `3`, TotalVictimCount `5`, Weapon `02`/`Handgun`, Gang `Yes`, LAT/LON `33.746`/`-118.2817` | Kept; `in_scope=True`; `occ_year_month="2025-05"`; RPT stays `"0558"`; AREA NAME → `"Harbor"`; `toc_mismatch=False` (3 rows, value 3); `Gang-related Crime=True`; `map_eligible=True` with no review flags. **`night=False` (14:21 is daytime), so it contributes to no nighttime count and no row in `district_month_night.csv`.** It is still district-eligible for any all-hours summary. |
| R2 | `26172245_220_0` (53) | Time 0000; month 2026-08 | Date OCC `2026 Aug 31 12:00:00 AM`, Time `0000`, Date Rptd `2026 Sep 01 08:22:37 PM`, RPT `1555`, Weapon NA | Kept; `in_scope=True`; `occ_year_month="2026-08"`; `calendar_coverage="complete"`; `time_is_0000=True`; `night=True`. Counted in `night_offenses_incl_0000` and `night_offenses_0000` for (1555, 2026-08), **not** in `night_offenses_excl_0000`. Weapon stays NA, not "None"; `report_lag_days` ≈ 1.85. |
| R3 | `C259005916_23H_0` (2549) | Area-only district; (0, 0) coordinates; C-prefixed case | RPT `10`, AREA `10`, LOCATION `Victory Blvd & Tampa Ave`, LAT/LON `0`/`0`, Date OCC `2025 Feb 10 03:00:00 PM`, Time `1500` | Kept; `in_scope=True`; RPT stays `"10"`; `rpt_dist_area_only=True`; `district_eligible=False`; `coord_zero=True`; LAT/LON → NA; `map_eligible=False`; `case_prefix="C"`; `night=False` (15:00), so it is not in any nighttime count, district or unassigned. |
| R4 | `25000271_13B_0` (120102) | Scope boundary: a night occurrence on 2024-12-31, reported on 2025-01-01 | Date OCC `2024 Dec 31 11:55:00 PM`, Time `2355`, Date Rptd `2025 Jan 01 09:06:34 AM`, RPT `0647` | Kept in `nibrs_clean`; `in_scope=False`, `scope_reason="2024_rms_transition"` (occurrence date sets scope, not report date); `night=True` but it contributes to **no** in-scope metric; counted in the exclusion table; `occ_year_month="2024-12"`. |
| R5 | `26173656_90D_0` (106) | Coordinates about 32 km from its district's median; partial month; time 06:45 | AREA `01` Central, RPT `0138`, LOCATION `Alameda & 2nd`, LAT/LON `34.1244`/`-117.9063`, Date OCC `2026 Sep 03 06:45:00 AM`, Time `0645`, TotalVictimCount `0` | Kept; `in_scope=True`; coordinates **unchanged**; `coord_outside_basic_range=True` and `coord_far_from_district_review=True` are review flags only; `map_eligible=True` (present and non-zero); `district_eligible=True`; `occ_year_month="2026-09"`, `calendar_coverage="partial"`. **`night=False` (06:45 is after the 06:00 end), so it contributes to no nighttime count.** |

These expectations will be copied into a notebook Markdown cell **before** the transformation cells run. Actual values will then be filled in from the output, with a match column for each record.

---

## 9. Sample of up to 50 cleaned rows

- File: `outputs/sample_cleaned_rows.csv`. It contains all cleaned columns plus `sample_reason`.
- The selection is deterministic: `select_sample(clean, seed=576)` in `clean_nibrs.py`.
  1. The 5 record-check rows (R1–R5) and the other 2 rows of case 25088246.
  2. Up to 2 rows per difficult-case category, chosen with the fixed seed:
     - Time: `time_is_0000` (night), `time_is_1200`, night-boundary times (1959, 2000, 0559, 0600).
     - Dates: an observed 2026-09-19 record, `rpt_before_occ`, `Date Rptd` missing.
     - District: `rpt_dist_area_only`.
     - Coordinates: `coord_missing`, `coord_zero`, `coord_outside_basic_range`, `coord_far_from_district_review` (inside the basic range), `location_suspected_generalized`.
     - Offense and case fields: `nibr_code_missing`, `nibr_desc_code_conflict`, `toc_mismatch`, `tvc_conflict`, `same_code_repeat_in_case`.
     - Weapon: NA, multi-code, `00`.
     - Out of scope: `pre_2024`, `2024_rms_transition`, `occ_implausible_year`.
  3. The rest are filled with in-scope rows that carry no flags, chosen with the same seed, up to 50 in total.
- Each row is listed once, under its first matching reason. The notebook prints the count for each reason. The full dataset is still cleaned and verified; the sample only illustrates it.

---

## 10. Implementation layout

- **`clean_nibrs.py`** holds the shared logic that the notebook and the CLI both use:
  - Pipeline: `load_raw()` → `standardize_text()` → `convert_types()` → `add_quality_flags()` → `add_time_fields()` → `add_coordinate_flags()` → `apply_scope()` → `build_district_month()`.
  - Plus `select_sample()`, `validate()` (assertions), and `main()`.
  - Constants at the top: scope date `2025-01-01`; night window 20:00–06:00; distance review threshold 5 km; basic coordinate range; sample seed 576.
  - Run with: `python clean_nibrs.py --input data/LAPD_NIBRS_Offenses_Dataset_20261004.csv --outdir outputs`.
- **Notebook:** the existing 7 cells stay unchanged. New sections each have a Markdown cell before (what and why) and after (what changed and the check result):
  1. Record checks: expectations.
  2. Text standardization.
  3. Type conversion.
  4. Quality flags.
  5. Time and nighttime.
  6. Coordinates.
  7. Scope and exclusion accounting.
  8. District-month summary.
  9. Record checks: actual results.
  10. Sample.
  11. Reconciliation.
  12. Limitations.

  The notebook imports `clean_nibrs`.
- **Outputs (`outputs/`):**

  | File | Git |
  |---|---|
  | `nibrs_clean.csv` (all 489,955 rows) | Ignored (large derived data) |
  | `district_month_night.csv` | Included via a narrow exception (approved) |
  | `sample_cleaned_rows.csv` | Included via a narrow exception |
  | `validation_summary.json` (counts, hashes, assertion results, unassigned-by-area table) | Included (not ignored) |
  | `cleaning_decision_log.md` (rule / reason / check) | Included |
  | `record_checks.md` | Included |

- **`.gitignore`:** append `!outputs/sample_cleaned_rows.csv` and `!outputs/district_month_night.csv`. `outputs/` itself isn't ignored (only the `*.csv` pattern matches), so these negations work. `data/` and every other CSV stay ignored. Verify with `git check-ignore -v` on the two exceptions, on `outputs/nibrs_clean.csv`, and on the raw CSV. **No commit or push until you approve.**
- **`requirements.txt`:** `pandas==3.0.4`, `numpy==2.5.0`, `ipykernel==7.3.0` (for running the notebook in VS Code). No nbconvert. The README records Python 3.14.6 separately.

---

## 11. Verification after each transformation

| Step | Checks |
|---|---|
| Load | Shape 489,955 × 31; the CSV's SHA-256 equals §0, checked before and after the run |
| Text standardization | Row count unchanged; changed cells counted per column (only AREA NAME and NIBR Description); AREA NAME 21 → 21; NIBR Description 2,409 → 2,398; lengths of `AREA`, `RPT Dist No`, `Premise Cd`, `Weapon Used Cd`, and `Time OCC` unchanged (leading zeros intact) |
| Type conversion | 0 failed conversions per column (NA → NA excluded); NA before/after table, equal except LAT/LON (+550 from (0, 0) → NA); boolean True counts = original Yes counts |
| Flags | Each flag count matches §1, §3, and §4 (e.g. `toc_mismatch` = 96 rows / 80 cases; `tvc_conflict` cases = 17) |
| Time | Time OCC = Date OCC HH:MM for 489,955 rows; minute of day within 0–1439; in scope: 0000 = 10,330, night incl. 0000 = 137,415, excl. 0000 = 127,085 |
| Scope | 380,091 + 109,864 = 489,955; per-reason counts match §2; ID still unique |
| District-month | 137,243 + 172 = 137,415 and 126,919 + 166 = 127,085; 3 cells recounted independently from `raw`; September counts present |
| Record checks | R1–R5 actual vs expected, with a match column |
| Reproducibility | (1) VS Code **Restart Kernel → Run All** on the notebook, which writes `outputs/`. (2) Run the CLI with `--outdir` pointing to a **separate temporary folder** (e.g. `%TEMP%\nibrs_repro`). (3) Compare the SHA-256 of every output file in the temporary folder with `outputs/`. They must match. `outputs/` is never deleted. (4) Recheck the raw CSV's SHA-256. |

---

## 12. Suggestion designated for your verification (handout's AI-suggestion item)

AI tools used: **ChatGPT** (OpenAI) for planning and review, and **Claude Code** (Anthropic) for implementation. Codex was not used. The handout allows this: "If you did not use Codex, explain how you checked one cleaning decision." The cleaning decision below came from Claude Code.

**Your verification (performed 2026-10-04, district 0984 only):** 5 records have `LOCATION` = `RPT Dist No`, all sharing (34.149, −118.4537). The street-address records shown have varied coordinates. This supports the flag but does not prove how LAPD assigned the coordinates. You did not check a second district or inspect a map.

**Suggestion S1 (from Claude Code, offered for your independent check):** *"Rows whose `LOCATION` equals their `RPT Dist No` (e.g. `0246`) appear to carry one shared district-level coordinate rather than a hundred-block location. Flag them `location_suspected_generalized`, keep them in district counts, and let the dashboard decide how to map them."*

You can check it yourself, without my code:
1. `raw[(raw["LOCATION"]=="0984") & (raw["RPT Dist No"]=="0984")][["LAT","LON"]].drop_duplicates()`: expect exactly one coordinate pair.
2. `raw[(raw["RPT Dist No"]=="0984") & (raw["LOCATION"]!="0984")][["LOCATION","LAT","LON"]].head(10)`: expect varied coordinates.
3. Paste the shared point and a few street-address points into a map. Note whether the shared point lines up with any listed address.
4. Repeat for a second district of your choice.

If any district has more than one coordinate pair among these rows, the suggestion does not hold for that district. **You have not verified this yet. The PDF will report only what you actually observe.**

---

## 13. Mapping to the 14 checklist items

Every status below is **planned**. The evidence depends on implementation and will be filled in only from validated outputs.

| # | Item | Planned status | Evidence (pending unless noted) |
|---|---|---|---|
| 1 | Vision and question | Done (text ready) | Header of this plan; README and notebook intro (pending) |
| 2 | Define one row | Done (verified in planning and in the existing notebook) | One row = one offense; `UniqueNIBRNo` unique (§1.1). Re-asserted in code (pending). |
| 3 | Preserve source | Pending | §0; SHA-256 before and after a run; `raw` never modified |
| 4 | Columns and types | Pending | §3; conversion-failure table in the notebook |
| 5 | Standardize text | Pending | AREA NAME and NIBR Description before/after; leading-zero checks |
| 6 | Duplicates | Pending | 0 exact duplicates and 0 repeated IDs (verified in the existing notebook); same-code repeats explained |
| 7 | Missing data | Pending | NA before/after per affected column; reasons (§3) |
| 8 | Suspicious values | Pending | Pre-1900 dates, report before occurrence, 0000/1200 heaping, coordinate flags, area-only districts, case-total mismatches and conflicts, code conflicts |
| 9 | Verify merges | **Done** (corrected; an earlier draft said "Not applicable") | No **external** dataset is merged. The code does perform **internal joins**: three many-to-one left joins on `occ_year_month` attach month context to the district-month table, the unassigned table, and the month summary. Two lookups (per-`CaseNo` counts; district median point) also act as joins. All are audited: row counts before and after, extra rows, unmatched keys, and duplicate right keys (`validation_summary.json` → `join_audits`, `lookup_audits`). The streetlight GIS join is a later dashboard step. |
| 10 | Reconcile changes | Pending | 489,955 cleaned → 380,091 in scope; 109,864 exclusions by reason; LAT/LON NA +550 |
| 11 | Check calculations | Pending | Record counts per metric (incl./excl. 0000); distinct cases; unassigned districts; no summing of case totals; no victim total |
| 12 | Five record checks | Pending | §8 expectations fixed now; actual results from the output |
| 13 | Reproducibility | Pending | VS Code Restart & Run All + CLI run in a temporary folder + hash comparison |
| 14 | Limitations | Pending (draft below) | §14 |

## 14. Known limitations (draft)
- Counts are reported offenses. They depend on reporting and recording practices and have no exposure denominator, so they are not rates or risk.
- The nighttime window is a fixed-clock approximation and ignores seasonal sunset/sunrise.
- 0000 and 1200 are heaped, and the source does not explain why. Results are shown with and without 0000.
- Any month can still receive late reports; recent months have had the least time. September 2026 is calendar-partial, ending 2026-09-19 in our file.
- 504 in-scope rows have no district. 8,217 have a suspected generalized location. 478 have (0, 0) coordinates, concentrated in early 2025. 1,848 are flagged for distance review.
- `TotalOffenseCount` and `TotalVictimCount` are inconsistent within some cases. The meaning of the CaseNo prefixes is undocumented. A distinct case is not necessarily a distinct incident.
- Streetlight assets are context only. They are not measurements of lighting quality or outages, and nothing here shows that poor lighting causes offenses.
- The download date is unconfirmed. Our data is the fixed SHA-256-identified snapshot and does not include later LAPD updates.

## 15. Deliverables checklist
- [ ] `clean_nibrs.py`
- [ ] `Data Cleaning.ipynb` (existing; new sections appended)
- [ ] `outputs/sample_cleaned_rows.csv` (≤ 50 rows) and `outputs/district_month_night.csv`, plus the narrow `.gitignore` exceptions
- [ ] `requirements.txt`
- [ ] `README.md`: source and version (SHA-256, portal consistency checks, unconfirmed download date), run instructions, expected outputs, branch `zayra-rwx`, branch URL `https://github.com/zayra-rwx/community-safety-resource-planner/tree/zayra-rwx`, submitted commit ID
- [ ] Commit and push to `zayra-rwx` only, **after your approval** (merge, never rebase); record the commit ID in the README and the PDF
- [ ] Verify instructor access: `gh api repos/zayra-rwx/community-safety-resource-planner/collaborators/yalimohammadi` should return 204. If it doesn't, invite `yalimohammadi`.
- [ ] PDF, generated **after** validation from the verified outputs: 14 items, decision log, five record checks, your own S1 verification, branch, URL, and commit

## 16. Decision record
| ID | Decision (2026-10-04) |
|---|---|
| N1 | Night = 20:00 inclusive to 06:00 exclusive; a fixed-clock approximation. Sunset/sunrise deferred. |
| N2 | Keep and flag 0000. Report night counts including and excluding 0000. No claim about what 0000 means. |
| M1 | Calendar coverage (`complete` / `partial` for 2026-09) is separate from reporting completeness, which is described by days since month end. No month is labeled final. |
| M2 | Keep the observed September counts. Export observed district-month combinations only. The complete grid and persistence thresholds are deferred. |
| C1 | More than 5 km from the district median is a review flag only. Coordinate flags are kept separate. No exclusion by distance. |
| O1 | Report distinct `CaseNo` counts as "distinct cases". Never sum case-level totals. No victim total. |
| G1 | Include `district_month_night.csv` through a narrow `.gitignore` exception. No commit or push yet. |
| R | Reproducibility: VS Code Restart Kernel → Run All, plus a CLI run in a separate temporary folder. No nbconvert. |
| P1 | Persistence threshold: deferred, not part of this assignment. |
| D | Data: the fixed local CSV, identified by SHA-256 `97a8dbad…b39e5`. |
