# Team change requests

Copy this template into your team's repository if no shared change-request file exists. Do not replace an existing file. Keep your individual audit in the module folder.

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Olga Tovstogan | Existing CLI reporting-district prioritization | District 0182 default priority score, displayed as 87.679181 | Executable normal/empty/reversed/repeat CLI cases; independent score reconstruction for all 1,172 districts; explicit tie/universe examples. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |
| Yu (Ansel) Lin (anselyulin) | Date-range selection in the existing CLI, with backend category/district invariance checks | Recent nighttime offenses, focused on district 1494 | Independent source-text/calendar/set reconstruction; full-data complete/partial-month checks; CLI output checks and small predeclared fixtures. Distinct from Olga's priority-score audit. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |
| Caroline Romero (carolineromero19) | Top-10 ranked district list in the existing CLI (`--top 10`), evaluated as the planning manager would read it | Persistence rate (active months / eligible months), focused on districts 0182, 0122 and 0116 | Independent recomputation for all 1,172 districts that rebuilds nighttime from raw `Time OCC` text instead of the team's `is_night`/`offense_month` columns; hand-calculated small cases. Distinct from Olga's priority-score and Ansel's recent-offenses audits. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. | 
| Zayra Martinez (zayra-rwx) | District composition (`category_summary` offense/premise breakdown, use case 2) as the planning manager would use it | Valid mapped nighttime offenses, focused on district 0182 (1,167) | Independent recount from raw CSV text with the `csv` module only (no cleaning code, Parquet or derived flags); hand-built boundary fixture; new plausibility check of "valid" coordinates against each district's own median location; investigation of 2-digit area-level district codes. Distinct from Olga, Ansel and Caroline. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |

## Requests

Copy the following block for each actionable finding. Agree on a unique ID with your team. A check that finds no defect can stay in the individual audit; do not invent a bug to fill a request.

### AUDIT-01 Explain reversed-date empty results in the CLI

- Author: Olga Tovstogan. Technical inspection, execution and drafting by Codex.
- Status: proposed; not implemented. Recommended CLI usability improvement, not a demonstrated contract violation.
- App version or commit checked: 87a892a392727cfaff176d3c0fbbf6019a60eb4a.
- Feature and intended behavior: existing CLI reporting-district prioritization. The documented backend returns an empty result for reversed intervals; preserve that behavior.
- Inputs and reproduction steps: from the repository root, run `.venv/Scripts/python.exe -m src.analysis --start 2026-09-19 --end 2025-01-01 --top 3`.
- Expected result: under the existing contract, an empty result. Recommended enhancement: also explain that start is later than end and how to correct the dates. No explicit CLI rejection requirement is asserted.
- Actual result: exit code 0; `Empty DataFrame`, column names and `Index: []`, without an explanation.
- Evidence and likely cause, if established: `audits/olga/feature-output.txt` and `check_feature.py`; `src/analysis.py:172`, `main()`, prints the ranking frame without a contextual empty-result message. Practical impact: the manager may not distinguish reversed input from a valid empty selection. Low-severity usability limitation.
- Requested change: add an explanatory CLI message for reversed dates while preserving documented backend empty-frame behavior and existing valid ranking results.
- Verification check: repeat the command and confirm a clear start-after-end explanation; check that valid empty selections receive a distinct message; normal `--top 3` output and existing backend tests remain unchanged.
- Implementation commit and verification result, when built: not implemented; no implementation commit or post-change verification. Audit evidence only. Request awaits team review.

Passing numeric check (no numeric defect or corrective change requested): **Pass with limitation**. District 0182 independently recomputes to 87.67918088737201, printed as 87.679181; maximum score difference over all 1,172 districts is 0.0. Tie/universe fixtures pass. Evidence: `audits/olga/my-audit.md` (compact targeted ranking check; prior full-data evidence is separate), `audits/olga/numeric-output.txt`, `numeric_results.json` and `appendix-output.txt`. Agreement checks the stated formula, not source completeness, policy merit of the weights or lighting causality. Overall tested CLI workflow: **Pass with limitation**.

### AUDIT-ANSEL-01 Explain when the CLI has no complete recent months

- Author: Yu (Ansel) Lin. Technical inspection, execution and initial drafting by Codex at the student's request.
- Status: proposed; not implemented. Low-severity CLI usability enhancement, not a numerical defect or an assertion that the future dashboard already exists.
- App version or commit checked: `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
- Feature and intended behavior: a planning manager selects an occurrence-date interval and interprets Recent nighttime offenses. The current backend correctly uses the latest up to three complete calendar months; no complete months means zero with no period.
- Inputs and reproduction steps: from the repository root run `python -m src.analysis --start 2026-09-01 --end 2026-09-19 --top 3` with the pinned team environment and canonical Parquet.
- Expected result: under the backend contract, each displayed recent count is 0 and both recent endpoints are absent. Recommended CLI presentation: additionally explain `No complete months in the selected available interval; recent counts are 0 by convention.` Keep the ordinary selected-period nighttime count visible.
- Actual result: exit code 0. The three displayed districts (0646, 1258, 0162) have selected-period nighttime counts 28, 28, 25, while recent counts are all 0 and both recent endpoint columns display `None`. The CLI does not explain why a recent count of zero can coexist with positive selected-period counts.
- Evidence and likely cause, if established: `audits/anselyulin/cli-output.txt`, case `no_complete_months`, and `results.json`. At the audited commit `src/analysis.py:179` directly prints the ranking DataFrame, exposing backend sentinel values without a contextual explanation. `recent_period` at lines 94-105 correctly excludes partial months. The current CLI has no explicit human-readable-label contract; the dashboard spec's `No complete months` label is a useful design precedent, not a delivered-UI obligation applied retroactively.
- Requested change: add the explanatory sentence in CLI presentation when no complete calendar month is available. Preserve `(None, None)` at the backend API and preserve the zero recent-count convention. Do not describe the selected interval as having no offenses.
- Verification check: repeat the September command and confirm the explanation, zero recent counts, and unchanged selected-period counts; repeat the default command and confirm June 1-August 31, 2026 plus unchanged recent counts; a fixture with an eligible zero-offense month must keep a valid period rather than trigger the no-complete-months message. Existing regression tests must still pass.
- Implementation commit and verification result, when built: not implemented. Audit evidence and recommendation only; no production files changed.

Ansel's numeric finding: **PASS** on tested cases. District 1494 independently reconstructs to 131 recent nighttime offenses for June-August 2026 (49 + 47 + 35); all-district default total is 26,646. All 10 full-data backend cases, six CLI cases and five predeclared synthetic cases agree with independent expected answers. No numerical change is requested. Remaining uncertainty and AI attribution are recorded in `audits/anselyulin/my-audit.md` and `audits/anselyulin/README.md`.

### AUDIT-CAROLINE-01 Make the default ranked CLI output readable for the planning manager

- Author: Caroline Romero. Check script written by Claude (AI) at the student's request; the student ran it, reviewed it, did the hand calculations and made the judgments.
- Status: proposed; not implemented. Low-severity CLI usability enhancement, not a numerical defect.
- App version or commit checked: `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
- Feature and intended behavior: the planning manager runs the default ranking and reads which districts come first and why. BUILD_SPEC section 8 lists the ranked table's columns; counts should read as integers and rates/scores at sensible precision.
- Inputs and reproduction steps: from the repository root, run `.venv/bin/python -m src.analysis --top 10` in a standard-width terminal.
- Expected result: one readable row per district with values clearly aligned to column headers; no number split across lines.
- Actual result: exit code 0 and correct values, but each district's row wraps across about three lines. District 0182's valid mapped nighttime offenses (1167) appears as "11" at the end of one line and "67" at the start of the next. Scores and percentiles print with six decimal places (e.g., 87.679181). The output does not state the nighttime definition (18:00–05:59) or how the priority score is formed.
- Evidence and likely cause, if established: steps and observations in `audits/caroline/my-audit.md`. Likely the same root cause noted in AUDIT-01 and AUDIT-ANSEL-01: `main()` in `src/analysis.py` prints the raw ranking DataFrame. Practical impact: the manager may misread values or need to piece rows together.
- Requested change: in CLI presentation only, print a narrower or vertically formatted table (or fewer default columns with an option to show all), round display values (counts as integers, rates and scores to two decimals), and print a one-line note with the nighttime definition and score formula. Keep backend values and exports unrounded.
- Verification check: rerun the command and confirm each district appears on one line or in a clearly labeled block, no number is split, display rounding is applied, and backend tests and stored values are unchanged.
- Implementation commit and verification result, when built: not implemented. Audit evidence only.

Caroline's numeric finding: **PASS** on tested cases. Persistence rate independently recomputes for all 1,172 districts with 0 disagreements (eligible months = 21; data through 2026-09-19). Hand checks: 0122 = 18/21 = 0.857143; 0116 = 1/21 = 0.047619; 0182 = 21/21 = 1.0, all matching the tool. Not tested: filtered views. Both checks share the canonical Parquet, so an upstream cleaning error would affect both. Evidence: `audits/caroline/check_persistence.py` and `audits/caroline/my-audit.md`. No numerical change is requested.

### AUDIT-ZAYRA-01 Flag "valid" coordinates that are far from their own district

- Author: Zayra Martinez. Check script written and run by Claude Code (AI) at the student's request; the student reviewed it and made the judgments.
- Status: open. Data-quality and map-accuracy issue, not a formula defect.
- App version or commit checked: `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
- Feature and intended behavior: Valid mapped nighttime offenses, plus the planned approximate offense map (BUILD_SPEC §6, §10). A "valid mapped" offense should be one the manager can trust to appear roughly where it occurred.
- Inputs and reproduction steps: `python audits/zayra/check_mapped.py --raw data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv`, Check 3.
- Expected result: few or no mapped points far outside their own reporting district.
- Actual result: 499 valid mapped nighttime points are more than 10 km from their district's median location, and 265 are more than 20 km away (398 districts have at least one point more than 5 km off). Example: 0331 Southwest "3000 S Westview St" is plotted at 34.5683, −118.0878 (Palmdale area). Wilshire 0785 is plotted near Pomona.
- Evidence and likely cause, if established: `audits/zayra/check-output.txt`. `src/clean_data.py:70-71` tests only the broad box (33.5–34.9, −118.9 to −117.5), which covers much of LA, Orange, San Bernardino and Riverside counties. Likely source geocoding errors. The count itself is computed as specified: an independent raw-text recount shows 0 disagreements over 1,172 districts.
- Requested change: add a separate audit flag (for example, `coordinates_far_from_district`, more than 10 km from the district median) and report its count in `data_quality.json`. In the Phase 3 map, exclude or visually mark flagged points and say so in Methods. Keep `has_valid_coordinates` and the current count definition unchanged unless the team agrees to redefine it.
- Verification check: rerun Check 3. The flag count should equal the script's 10 km count, flagged points should not plot as ordinary points, and existing tests and ranking values should be unchanged.
- Implementation commit and verification result, when built: not implemented.

### AUDIT-ZAYRA-02 Label 2-digit area-level district codes instead of ranking them as districts

- Author: Zayra Martinez (AI-assisted as above).
- Status: open. Interpretation issue; low effect on top ranks.
- App version or commit checked: `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
- Feature and intended behavior: Ranked reporting districts. The ranking unit is `RPT Dist No` (BUILD_SPEC §5).
- Inputs and reproduction steps: same script, Check 3; or look at `RPT Dist No` values shorter than 4 characters in `ranked_districts(load_processed())`.
- Expected result: every ranked row is a real reporting district, or area-level records are clearly labeled.
- Actual result: 21 codes (`01`–`21`) equal the AREA code. Their LOCATION is often just the area number, and their coordinates are 0/0 (216) or blank (35). They hold 251 nighttime offenses, which is 87% of the 288 unmapped nighttime offenses. They are scored and ranked (for example, `06` is rank 1087) and count in the 1,172-district percentile universe.
- Evidence and likely cause, if established: `audits/zayra/check-output.txt`. The source records offenses with only area-level location; cleaning keeps the code as a district key.
- Requested change: the team should decide on and document one rule. Either keep these records out of the district ranking and report them as "area-level, no reporting district", or keep them but label them in outputs and Methods. Do not delete source rows.
- Verification check: rerun the ranking. Short codes are either absent and reported separately, or visibly labeled. Universe count and percentiles change only as documented; tests are updated accordingly.
- Implementation commit and verification result, when built: not implemented.

### AUDIT-ZAYRA-03 Make district composition reachable and readable for the manager

- Author: Zayra Martinez (AI-assisted as above).
- Status: open. Usability gap for use case 2. The calculation passes.
- App version or commit checked: `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
- Feature and intended behavior: for one district, show offense and premise composition so the manager can tell whether the pattern is concentrated (BUILD_SPEC §4 use case 2, §8 District Evidence).
- Inputs and reproduction steps: `python -m src.analysis --help` (`audits/zayra/cli-help.txt`); Check 4 of the script.
- Expected result: the manager can request one district's composition and see counts, shares and the period.
- Actual result: the CLI exposes only `--start`, `--end` and `--top`, so composition needs Python code. When called, `category_summary` is correct: for 0182, 146 offense categories and 78 premises, each adding to 1,167. But it has no share column or period label. Across all districts it shows `Location Unknown` (546, a source label) and `Unknown` (1, a missing value) as separate rows that look alike.
- Evidence and likely cause, if established: `src/analysis.py:172-179` (`main()` prints only the ranking); `src/analysis.py:155-163`.
- Requested change: add a `--district` CLI option (or deliver it in the Phase 3 District Evidence view) that prints the top offense and premise categories with counts, percent of the district's nighttime total and the date period. Display missing values as "Missing (no premise recorded)" to separate them from the source label `Location Unknown`. Keep backend output unchanged.
- Verification check: run with `--district 0182`. Counts match `category_summary`, shares add to 100%, the period is shown, and the two unknown labels are distinguishable. Existing tests pass.
- Implementation commit and verification result, when built: not implemented.

Zayra's numeric finding: **PASS** on the formula. Valid mapped nighttime offenses for 0182 = 1,167; the independent raw-text recount matches all 1,172 districts with 0 disagreements (total 178,921 of 179,209 = 99.84%); the 11-row boundary fixture passes. Limitations are in AUDIT-ZAYRA-01/02. Evidence: `audits/zayra/my-audit.md`, `check_mapped.py`, `check-output.txt`.

## Follow through

One teammate can ask Codex to implement open requests one at a time. For each, rerun the evidence, commit with its ID, and mark it built only after checking the result. File a request rather than undoing someone else's work.

## Source and claim coordination

Official template copied from [USC-DSO-576-YA/09-audit, change-requests.md](https://github.com/USC-DSO-576-YA/09-audit/blob/03e892ce5bc2f6869675a822f05b630fe8f365c1/change-requests.md), historical commit `03e892ce5bc2f6869675a822f05b630fe8f365c1`. The original is retained byte-for-byte in `audits/olga/official-change-requests-template.md`; headings and request fields are preserved here. It was removed from module main in commit `dbcf2ac7b8c62330726d43eb01a54630acec9ec7`; the historical homework.md explicitly references this shared template.

Before creation on October 23, 2026, neither the working tree nor local origin/main nor live remote main (87a892a392727cfaff176d3c0fbbf6019a60eb4a) had a root change-requests.md. No teammate claims were available to compare or overwrite. Overlap with unpublished claims is unknown; the independent all-district reconstruction and explicit tie/universe examples identify the new evidence if overlap later emerges. AUDIT-01 is unique in the available shared file and awaits team coordination.

Olga reviewed scope and assignment coverage, corrected the evaluation of future development requirements, and followed up until the official shared template was located and populated. Codex inspected source, executed checks, calculated results and drafted the audit. No personal app use or manual calculation by Olga is claimed. The individual report remains at repository root per Olga's assignment instructions. No follow-through implementation is authorized by this record.

## Ansel audit branch coordination

This branch starts from main at `87a892a392727cfaff176d3c0fbbf6019a60eb4a`. The existing shared record above was copied from Olga commit `0415a24443decaa3f5811cd4bfffa7de358a8c51`; Olga's claim, request and wording are retained. Her evidence files remain on [her branch at that commit](https://github.com/zayra-rwx/community-safety-resource-planner/tree/0415a24443decaa3f5811cd4bfffa7de358a8c51/audits/olga). All relative references in Olga's retained entry refer to her version, including [her individual report](https://github.com/zayra-rwx/community-safety-resource-planner/blob/0415a24443decaa3f5811cd4bfffa7de358a8c51/my-audit.md). Ansel's additions are confined to this individual audit branch pending team coordination. No merge or implementation is performed.

## Caroline audit branch coordination

This branch (`caroline-module9-audit`) starts from main at `87a892a392727cfaff176d3c0fbbf6019a60eb4a`. The shared record above was copied from Ansel's branch `codex/module9-ansel-audit`; Olga's and Ansel's claims, requests and wording are retained unchanged. Caroline's additions are her claim row, AUDIT-CAROLINE-01 and her numeric finding. No merge or implementation is performed.

## Zayra audit coordination

Zayra's audit starts from Caroline's branch `caroline-module9-audit` (`4375dfb`), so Olga's, Ansel's and Caroline's entries are retained unchanged. It is merged into branch `zayra-rwx`. Zayra's additions are her claim row, AUDIT-ZAYRA-01 to 03, her numeric finding and `audits/zayra/`. No production code is changed.