# Team change requests

Copy this template into your team's repository if no shared change-request file exists. Do not replace an existing file. Keep your individual audit in the module folder.

## Claims

| Author | Feature | Number | Distinct scope or new evidence |
| --- | --- | --- | --- |
| Olga Tovstogan | Existing CLI reporting-district prioritization | District 0182 default priority score, displayed as 87.679181 | Executable normal/empty/reversed/repeat CLI cases; independent score reconstruction for all 1,172 districts; explicit tie/universe examples. Audited commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a. |

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

## Follow through

One teammate can ask Codex to implement open requests one at a time. For each, rerun the evidence, commit with its ID, and mark it built only after checking the result. File a request rather than undoing someone else's work.

## Source and claim coordination

Official template copied from [USC-DSO-576-YA/09-audit, change-requests.md](https://github.com/USC-DSO-576-YA/09-audit/blob/03e892ce5bc2f6869675a822f05b630fe8f365c1/change-requests.md), historical commit `03e892ce5bc2f6869675a822f05b630fe8f365c1`. The original is retained byte-for-byte in `audits/olga/official-change-requests-template.md`; headings and request fields are preserved here. It was removed from module main in commit `dbcf2ac7b8c62330726d43eb01a54630acec9ec7`; the historical homework.md explicitly references this shared template.

Before creation on October 23, 2026, neither the working tree nor local origin/main nor live remote main (87a892a392727cfaff176d3c0fbbf6019a60eb4a) had a root change-requests.md. No teammate claims were available to compare or overwrite. Overlap with unpublished claims is unknown; the independent all-district reconstruction and explicit tie/universe examples identify the new evidence if overlap later emerges. AUDIT-01 is unique in the available shared file and awaits team coordination.

Olga reviewed scope and assignment coverage, corrected the evaluation of future development requirements, and followed up until the official shared template was located and populated. Codex inspected source, executed checks, calculated results and drafted the audit. No personal app use or manual calculation by Olga is claimed. The individual report remains at repository root per Olga's assignment instructions. No follow-through implementation is authorized by this record.
