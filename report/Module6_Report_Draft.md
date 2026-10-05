# DSO 576 Module 6: Project Data Cleaning

**Project:** Community Safety Resource Planner: Streetlight Assessment (Team 12)
**Student:** Zayra Martinez

All results below come from the final run of `clean_nibrs.py` and `Data Cleaning.ipynb`: **104 of 104 automated checks passed**.

**Branch:** `zayra-rwx`
**Branch URL:** https://github.com/zayra-rwx/community-safety-resource-planner/tree/zayra-rwx
**Commit ID:** `06460a04e74f9cf59f9dd226c20c7c76b76bb07d`

---

## Part 1: 14-item checklist

**1. State the project vision and question.** Status: **Done**
Vision: a street-lighting program manager at the City of Los Angeles Bureau of Street Lighting must decide which geographic areas with recurring nighttime reported offenses should be prioritized for on-site lighting assessments. Business question: *Which LAPD reporting districts show recurring nighttime reported offenses across months?* Main metric: monthly nighttime offense counts by reporting district (`RPT Dist No` × `occ_year_month`), with and without `Time OCC` = 0000, plus distinct-case counts. These counts are prioritization evidence, not rates or causal evidence. *Evidence:* README; plan.md header; notebook Part 2.

**2. Define one row.** Status: **Done**
One row = one NIBRS offense, identified by `UniqueNIBRNo`: 489,955 rows, 489,955 distinct IDs, none missing. One case (`CaseNo`, 440,121 distinct) can contain several offenses, so repeated case numbers are kept. *Evidence:* notebook cells 5–7; validation checks "UniqueNIBRNo unique in cleaned data" and "distinct CaseNo".

**3. Preserve the source.** Status: **Done**
Source: LAPD NIBRS Offenses Dataset, City of LA Open Data (`k7nn-b2ep`). Catalog: https://catalog.data.gov/dataset/lapd-nibrs-offenses-dataset-2026-to-present. Local file `data/LAPD_NIBRS_Offenses_Dataset_20261004.csv`, SHA-256 `97a8dbad…b39e5`. The portal says rows were last updated 2026-09-29; its row count and latest dates match this file, which is a consistency check, not proof. The download date is unconfirmed. The file is loaded with `pd.read_csv(path, dtype="string")`, which keeps leading zeros, but default missing-value tokens still become NA. A literal reload showed that only empty fields became NA. The SHA-256 was identical before and after the run, and `raw` is never modified. *Evidence:* README; `validation_summary.json` (`source_sha256_*`, `load_missing_tokens`).

**4. Inspect columns and types.** Status: **Done**
Conversions:
- `Date OCC` and `Date Rptd` → datetime, with explicit format `%Y %b %d %I:%M:%S %p`;
- `TotalOffenseCount` and `TotalVictimCount` → Int64;
- `LAT` and `LON` → Float64;
- 8 Yes/No columns → boolean.

IDs, codes and `Time OCC` stay as text. **Failed conversions: 0** in all 14 converted columns; the 7,787 missing `Date Rptd` values stay missing. *Evidence:* notebook Step 2; `validation_summary.json` → `type_conversion`.

**5. Standardize text.** Status: **Done**
- `AREA NAME`: trailing padding removed. Before: `'Harbor              '` (20 characters); after: `'Harbor'`. 489,955 cells changed; 21 → 21 distinct values.
- `NIBR Description`: repeated spaces collapsed. Example: `'... Grand Theft Auto - GTA  - 240'` → `'... GTA - 240'`. 82,058 cells changed; 2,409 → 2,398 distinct values. The 11 merged pairs differed only by doubled spaces.
- No case changes. The lengths of `AREA`, `RPT Dist No`, `Premise Cd`, `Weapon Used Cd` and `Time OCC` are unchanged, so leading zeros are preserved.

*Evidence:* notebook Step 1.

**6. Investigate duplicates.** Status: **Done**
- Exact duplicate rows: **0**. Repeated `UniqueNIBRNo`: **0**.
- 1,374 in-scope rows are identical except for `UniqueNIBRNo` (same case, same code, different sequence number), and 8,380 in-scope rows repeat a NIBR code within their case. All are **kept**, because each has its own offense ID. They are flagged (`same_code_repeat_in_case`) and reported as distinct-case counts alongside offense counts.

No rows were removed. *Evidence:* notebook cells 5–6 and Step 3; validation checks.

**7. Handle missing data.** Status: **Done**

| Column | Missing before | Missing after | Missing in scope | Handling |
|---|---|---|---|---|
| Weapon Used Cd / Weapon Desc | 345,971 | 345,971 | 277,461 | Kept missing. Not "no weapon". |
| Premise Cd | 22,853 | 22,853 | 10,959 | Kept; `Premise Desc` is the analytic field |
| Group | 15,480 | 15,480 | 10,153 | Kept; not filled from code |
| Date Rptd | 7,787 | 7,787 | 6,577 | Kept; occurrence date drives the analysis |
| Crime Against | 2,297 | 2,297 | 203 | Kept |
| NIBR Code | 1,149 | 1,149 | 72 | Kept and flagged; rows still count as offenses |
| Status / Status Desc | 1,044 / 1,042 | same | 36 / 36 | Kept |
| Premise Desc | 109 | 109 | 4 | Kept |
| LAT / LON | 131 | **681** | 587 | +550 because (0, 0) became missing; no replacement coordinates |

*Evidence:* `validation_summary.json` → `missing_values`.

**8. Check suspicious values.** Status: **Done**
No rows were removed; suspicious values were flagged, and (0, 0) coordinates were converted to missing.
- **Dates:** 3 occurrence dates before 1900 (out of scope). 523 reports dated before the occurrence (29 in scope).
- **Time:** `Time OCC` 0000 is heaped (15,333 rows; 10,330 in scope) and kept, with counts shown both ways. 1200 is also heaped (13,314). `Time OCC` agrees with the time inside `Date OCC` in all 489,955 rows.
- **District:** 558 area-only `RPT Dist No` values (504 in scope) are excluded from district counts and reported as unassigned.
- **Coordinates:** 550 at (0, 0); 0 non-numeric, non-finite, or outside global bounds. Review flags (not exclusions): 161 outside a rough LA box and 2,479 more than 5 km from their district median.
- **Reading the distance flag:** a `False` far-from-district flag means "not flagged", not "verified close". The 681 rows without a distance (558 area-only districts and 123 rows with non-mappable coordinates) were **not assessed**. For them, `False` does not establish that their coordinates are close to the district median.
- **Locations:** 10,412 suspected generalized locations.
- **Case totals:** case-level `TotalOffenseCount` mismatches (96 rows / 80 cases) and `TotalVictimCount` conflicts (17 cases).
- **Codes:** 16 conflicts between the description's code and `NIBR Code`.

Unusual is not treated as wrong. *Evidence:* notebook Steps 3–5; `validation_summary.json` → `flag_counts`.

**9. Verify merges.** Status: **Done**
No external dataset is merged; the Bureau of Street Lighting GIS layer will be joined later for the dashboard and validated then. The code does perform internal joins, all audited:

| Join | Key | Expected relationship | Left rows | Right rows | Result rows | Extra rows | Unmatched left | Duplicate right keys |
|---|---|---|---|---|---|---|---|---|
| District-month night counts ← month context | `occ_year_month` | many-to-one left join | 21,290 | 21 | 21,290 | 0 | 0 | 0 |
| Unassigned-district night counts ← month context | `occ_year_month` | many-to-one left join | 54 | 21 | 54 | 0 | 0 | 0 |
| In-scope month summary ← month context | `occ_year_month` | many-to-one left join | 21 | 21 | 21 | 0 | 0 | 0 |
| Rows → per-case counts (lookup) | `CaseNo` | many-to-one, built from the same rows | 489,955 | 440,121 cases | 489,955 | 0 | 0 | — |
| Rows → district median point (lookup, eligible rows only) | `RPT Dist No` | many-to-one | 489,274 eligible rows (map-eligible, 4-digit district) | 1,161 districts | 489,274 with a distance | 0 | 0 | — |

In the unassigned join, 17 of the 21 month keys are unused, because unassigned night records occur in only 4 months. That is expected for a left join and adds no rows. The per-case lookup values equal an independent recount.

**District-median lookup, rows not looked up (reported separately):**
- 558 rows with an area-only `RPT Dist No` (504 in scope).
- 123 rows with a 4-digit district but non-mappable coordinates (83 in scope).

All 681 keep a missing distance and a `False` far-from-district flag. No median is filled in. Reconciliation: 489,274 + 558 + 123 = 489,955 rows. *Evidence:* `validation_summary.json` → `join_audits`, `lookup_audits`; notebook Step 7.

**10. Reconcile changes.** Status: **Done**
- Starting rows: 489,955. Rows after cleaning: **489,955** (none removed).
- Analysis scope (`Date OCC` ≥ 2025-01-01): **380,091** rows / 344,186 distinct cases.
- Excluded from scope: 109,864 = 6,824 (`pre_2024`) + 1,351 (`2024_pre_rms`) + 101,689 (`2024_rms_transition`). These rows are kept in `nibrs_clean.csv` with a `scope_reason`.
- Important totals: in-scope night offenses are 137,415 including 0000 and 127,085 excluding it. District-month table plus unassigned: 137,243 + 172 = 137,415 and 126,919 + 166 = 127,085.

*Evidence:* notebook Steps 6–7; `validation_summary.json` → `scope_accounting`.

**11. Check calculations.** Status: **Done**
- **Records behind each metric:** in scope **and** night (Time ≥ 20:00 OR time < 06:00) **and** `district_eligible`. 137,243 records including 0000 and 126,919 excluding it; the excluding version drops 10,324 district-eligible 0000 records.
- **Distinct cases:** distinct `CaseNo` among the same records, labeled "distinct cases", not incidents.
- **Missing group keys:** `occ_year_month` and `AREA` are never missing. 504 in-scope records with an area-only district are reported as unassigned: 172 night records including 0000, 166 excluding.
- **Coordinates** do not affect counts.
- **Case-level totals** (`TotalOffenseCount`, `TotalVictimCount`) are never summed. Summing victims over in-scope rows would give 389,767 because multi-offense cases repeat the value, so no victim total is reported.
- **Absent combinations:** the table holds 21,290 observed district-month rows; a combination with no records is absent, not zero. No averages or rates are calculated.
- **Months:** September 2026 is calendar-partial; any month can still receive late reports.

*Evidence:* notebook Step 7; `district_month_night.csv`; independent raw recount of 3 cells (all matched).

**12. Verify individual records.** Status: **Done**
Expected results were written in plan.md §8 before the transformations ran. All 53 checked fields across the five records match (Part 3). *Evidence:* `outputs/record_checks.md`; notebook Step 8.

**13. Test reproducibility.** Status: **Done**
- **Notebook:** I opened `Data Cleaning.ipynb` in VS Code, chose the Python 3.14.6 kernel, and clicked **Restart**, then **Run All**. Every code cell ran in order (execution counts 1–17). The saved output shows **"Validation: 104 passed, 0 failed"** and **"Original CSV unchanged after run: True"**. The six output hashes it printed match the README.
- **Script:** `python clean_nibrs.py --outdir <separate temporary folder>` reproduced all six output files with SHA-256 identical to `outputs/`, also with 104 passed. `outputs/` was not deleted.
- The SHA-256 of the original CSV (`97a8dbad…b39e5`) was identical before and after every run.

| Output file | SHA-256 |
|---|---|
| `cleaning_decision_log.md` | `a388510bc6bf4decdecec4ad6c3b84fedd94bd75b6213052582713b77a6553ad` |
| `district_month_night.csv` | `a621b862544ff869ec5348cc66870ac867c9a0ccf767e2ff3245fe3a1675b887` |
| `nibrs_clean.csv` | `226f576c80fc87ed2580a1cf5598fff3bfeea35c5c279e97fa70976c7391923f` |
| `record_checks.md` | `5b75ad7c7377232a7a3b7c4006e264ca9e942c95eb7941f36ca32798275e44df` |
| `sample_cleaned_rows.csv` | `7af0b0dacd3d1f50bd101c7376a54afafeb0dd2f37a02783e19f2b7a7f1cc37e` |
| `validation_summary.json` | `652097e5ba4f67201a65da3e9ddaddd492870594a802164903d008edc6dcb930` |

Dependencies: `requirements.txt` (pandas 3.0.4, numpy 2.5.0, ipykernel 7.3.0); Python 3.14.6.

**14. Document remaining limitations.** Status: **Done**
- Counts are reported offenses, not rates or risk; there is no exposure denominator.
- The night window is a fixed-clock approximation.
- The 0000 and 1200 heaping is unexplained.
- Recent months have had the least time to collect late reports, and September 2026 is partial.
- 504 in-scope records lack a district; 8,217 have a suspected generalized location; 478 had (0, 0) coordinates.
- Case-level totals are inconsistent in some cases, and the meaning of the `CaseNo` prefixes is undocumented.
- Streetlight data is context only.
- The download date is unconfirmed.

*Information still needed:* LAPD documentation for 0000 times, generalized locations, and case prefixes; a reporting-district reference list; sunset times, if a solar night definition is adopted.

---

## Part 2: Cleaning decision log (rule, reason, check)

Generated by `clean_nibrs.py` from the same final run (`outputs/cleaning_decision_log.md`). Each check shows its actual result; all passed.

| # | Rule | Reason | Check (actual result) |
|---|---|---|---|
| 1 | Load all columns as text (`dtype="string"`); keep `raw` unchanged | Preserves leading zeros in codes and IDs; avoids silent type guessing. Default NA tokens still apply. | Raw CSV SHA-256 after run equals the recorded value (PASS); only empty fields became NA on load: True (PASS); non-missing values identical to literal text: True (PASS) |
| 2 | Keep all rows; one row = one offense (`UniqueNIBRNo`) | No exact duplicates or repeated IDs; repeated `CaseNo` values are multi-offense cases. | Exact duplicate rows: 0 (PASS); `UniqueNIBRNo` unique in cleaned data: True (PASS); cleaned rows = raw rows: 489,955 (PASS) |
| 3 | Strip `AREA NAME` padding; collapse repeated spaces in `NIBR Description` (no case changes) | Formatting only; meaningful category differences and leading zeros are kept. | `AREA NAME` distinct after: 21 (PASS); `NIBR Description` distinct after: 2,398 (PASS); leading-zero columns keep their lengths: True (PASS) |
| 4 | Convert dates (explicit format), counts (Int64), `LAT`/`LON` (Float64), Yes/No (boolean) | Enables validation and calculations; failures counted rather than hidden. | Failed type conversions (all columns): 0 (PASS); Yes/No True count = original Yes count: True (PASS) |
| 5 | Keep missing values as NA (weapon, group, premise, status, report date); no filling | Missing weapon is not "no weapon"; filling would invent information. | NA counts unchanged except `LAT`/`LON`: True (PASS) |
| 6 | Set (0, 0) coordinates to NA and flag `coord_zero`; no replacement coordinates | (0, 0) is not a location in Los Angeles. | `coord_zero`: 550 (PASS); `LAT` NA after cleaning (131 missing + 550 zero): 681 (PASS) |
| 7 | `map_eligible` = numeric, finite, within global bounds, not missing, not (0, 0) | Basic validity only; passing does not establish location accuracy. | Map-eligible rows finite and within global bounds: True (PASS); no (0, 0) pair in original values: 0 (PASS); `map_eligible` (in scope): 379,504 (PASS) |
| 8 | Flag rough-LA-box and >5 km-from-district-median points for review only | Unusual does not mean wrong; no point excluded on distance alone. A `False` distance flag means "not flagged"; rows without a distance were not assessed. | `coord_outside_basic_range` (review, in scope): 120 (PASS); `coord_far_from_district_review` (in scope): 1,848 (PASS) |
| 9 | Flag `LOCATION` = `RPT Dist No` as suspected generalized location | Each district shares one coordinate pair in these rows; not documented by the source. | `location_suspected_generalized` (in scope): 8,217 (PASS) |
| 10 | Flag area-only `RPT Dist No`; exclude from district counts, report as unassigned | A 2-digit value is an area, not a district; no district is guessed. | `rpt_dist_area_only` (in scope): 504 (PASS); unassigned night incl. 0000: 172 (PASS) |
| 11 | Flag case-level total mismatches and conflicts; never sum `TotalOffenseCount` or `TotalVictimCount` | They repeat on every offense row and sometimes conflict within a case. | `toc_mismatch` cases: 80 (PASS); `tvc_conflict` cases: 17 (PASS) |
| 12 | Analysis scope: `Date OCC` ≥ 2025-01-01 (occurrence, not report date) | Phase 1 scope; excludes pre-RMS and 2024 transition records without calling them wrong. | In-scope rows: 380,091 (PASS); in-scope + out-of-scope = all rows: 489,955 (PASS) |
| 13 | Night = 20:00 inclusive to 06:00 exclusive (fixed-clock approximation) | Matches the Phase 1 sketch; sunset/sunrise deferred. | Night incl. 0000 (in scope): 137,415 (PASS); night excl. 0000 (in scope): 127,085 (PASS) |
| 14 | Keep and flag `Time OCC` 0000; report night counts with and without it | Midnight values are heaped; the source does not explain why. | `Time OCC` 0000 (in scope): 10,330 (PASS) |
| 15 | `occ_year_month` from validated `Date OCC`; 2026-09 labeled calendar-partial; all observed records kept | Calendar coverage differs from reporting completeness; late reports can arrive for any month. | Only 2026-09 labeled partial (PASS); 2026-09-19 records kept: 8 (PASS) |
| 16 | Monthly table holds observed district-month combinations only (absent is not zero) | Complete grid and persistence thresholds deferred. | District-month + unassigned = in-scope night: 137,415 (PASS); independent raw recount of 3 cells matches: True (PASS) |
| 17 | Internal joins only: month context attached by many-to-one left joins on `occ_year_month`; `CaseNo` and district-median lookups audited | No external dataset is merged; joins must not add or drop rows or leave keys unmatched. | District-month join: result rows = left rows, 21,290 (PASS); unmatched left rows: 0 (PASS); `CaseNo` lookup unmatched rows: 0 (PASS); district-median lookup unmatched among eligible rows: 0 (PASS); rows not looked up with far flag True: 0 (PASS); looked up + area-only + other = all rows: 489,955 (PASS) |

*Note on rule 13:* the window wraps past midnight, so a record is night when **Time ≥ 20:00 OR time < 06:00**. In code, `occ_minute_of_day >= 1200 or occ_minute_of_day < 360`.

---

## Part 3: Five record checks

| # | UniqueNIBRNo | Original values (key) | Expected (written before) | Actual | Match |
|---|---|---|---|---|---|
| R1 | 25088246_290_2 | Time `1421`; RPT `0558`; AREA NAME `'Harbor␣×14'`; TotalOffenseCount `3`; TotalVictimCount `5`; Gang `Yes` | In scope; `2025-05`; `Harbor`; 3 rows in case, no mismatch; map-eligible, no review flags; **not night**, so no nighttime count | As expected (16/16 fields) | Yes |
| R2 | 26172245_220_0 | Date OCC `2026 Aug 31 12:00:00 AM`; Time `0000`; Weapon empty | In scope; `2026-08`, complete; 0000 flagged; night; counted **including** 0000 but **not excluding** it; weapon stays NA; report lag ≈ 1.85 days | As expected (lag 1.849) (10/10) | Yes |
| R3 | C259005916_23H_0 | RPT `10`; LAT/LON `0`/`0`; Time `1500` | Area-only district → not district-eligible; (0, 0) → NA, not map-eligible; prefix `C`; not night | As expected (11/11) | Yes |
| R4 | 25000271_13B_0 | Date OCC `2024 Dec 31 11:55:00 PM`; Date Rptd `2025 Jan 01 …` | Out of scope (`2024_rms_transition`) because occurrence sets scope; night but in no in-scope metric; `2024-12` | As expected (5/5) | Yes |
| R5 | 26173656_90D_0 | LAT/LON `34.1244`/`-117.9063` (Central, RPT `0138`); Time `0645` | Coordinates unchanged; outside LA box and >5 km review flags; still map- and district-eligible; `2026-09` partial; **not night** | As expected (11/11) | Yes |

Field-level detail: `outputs/record_checks.md`.

---

## Part 4: How I checked one AI-suggested cleaning decision

AI tools used: **ChatGPT** (OpenAI) for planning and review, and **Claude Code** (Anthropic) for implementation. Codex was not used, so I follow the handout's alternative: "explain how you checked one cleaning decision."

**Decision checked (suggested by Claude Code):** rows whose `LOCATION` equals their `RPT Dist No` are flagged `location_suspected_generalized`, on the claim that they share one district-level coordinate instead of a hundred-block location. They stay in district counts.

**How I checked it:** in my own notebook cell, I filtered `raw` to district `0984` where `LOCATION` equals `RPT Dist No`, listed the distinct coordinate pairs, and compared them with street-address records from the same district.

**What I found:**
- **5 records** match, and all 5 share one coordinate pair: **(34.149, −118.4537)**.
- The street-address records shown for district 0984 contain several coordinate pairs, unlike the five matching records, which all share one pair.

**Conclusion:** this supports keeping the suspected-generalized-location flag as a review flag. It does not prove how LAPD assigned these coordinates, which the source does not document. I checked one district only. I did not check a second district or inspect the points on a map.

---

## Part 5: Repository and access

- Branch `zayra-rwx`: https://github.com/zayra-rwx/community-safety-resource-planner/tree/zayra-rwx
- Commit ID: `06460a04e74f9cf59f9dd226c20c7c76b76bb07d`
- Instructor access: `yalimohammadi` is a collaborator on `zayra-rwx/community-safety-resource-planner`. Confirmed 2026-10-04 with `gh api repos/zayra-rwx/community-safety-resource-planner/collaborators/yalimohammadi`, which returned HTTP 204 No Content.
