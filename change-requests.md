# Team change requests

Copy this template into your team's repository if no shared change-request file exists. Do not replace an existing file. Keep your individual audit in the module folder.

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Olga Tovstogan | Existing CLI reporting-district prioritization | District 0182 default priority score, displayed as 87.679181 | Executable normal/empty/reversed/repeat CLI cases; independent score reconstruction for all 1,172 districts; explicit tie/universe examples. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |
| Yu (Ansel) Lin (anselyulin) | Date-range selection in the existing CLI, with backend category/district invariance checks | Recent nighttime offenses, focused on district 1494 | Independent source-text/calendar/set reconstruction; full-data complete/partial-month checks; CLI output checks and small predeclared fixtures. Distinct from Olga's priority-score audit. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |
| Caroline Romero (carolineromero19) | Top-10 ranked district list in the existing CLI (`--top 10`), evaluated as the planning manager would read it | Persistence rate (active months / eligible months), focused on districts 0182, 0122 and 0116 | Independent recomputation for all 1,172 districts that rebuilds nighttime from raw `Time OCC` text instead of the team's `is_night`/`offense_month` columns; hand-calculated small cases. Distinct from Olga's priority-score and Ansel's recent-offenses audits. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. | 

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

Passing numeric check (no numeric defect or corrective change requested): **Pass with limitation**. District 0182 independently recomputes to 87.67918088737201, printed as 87.679181; maximum score difference over all 1,172 districts is 0.0. Tie/universe fixtures pass. Evidence: `my-audit.md` (compact targeted ranking check; prior full-data evidence is separate), `audits/olga/numeric-output.txt`, `numeric_results.json` and `appendix-output.txt`. Agreement checks the stated formula, not source completeness, policy merit of the weights or lighting causality. Overall tested CLI workflow: **Pass with limitation**.

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

Ansel's numeric finding: **PASS** on tested cases. District 1494 independently reconstructs to 131 recent nighttime offenses for June-August 2026 (49 + 47 + 35); all-district default total is 26,646. All 10 full-data backend cases, six CLI cases and five predeclared synthetic cases agree with independent expected answers. No numerical change is requested. Remaining uncertainty and AI attribution are recorded in `my-audit.md` and `audits/anselyulin/README.md`.

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