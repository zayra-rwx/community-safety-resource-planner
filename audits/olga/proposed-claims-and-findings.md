# Proposed audit claim and findings — Olga Tovstogan

This holding document is retained as supporting detail. The actual shared claim,
request AUDIT-01 and passing numeric finding are now recorded in root
`change-requests.md`, using the recovered official historical template. That root
file is the authoritative shared record; this document is not its substitute.

## Claim

- Name: Olga Tovstogan
- Feature: Existing command-line reporting-district prioritization workflow,
  evaluated against the submitted README and backend contracts only.
- Number: District 0182's default Priority score, displayed as 87.679181.
- App version/commit: 87a892a392727cfaff176d3c0fbbf6019a60eb4a.
- New evidence contributed: executable normal/empty/reversed/repeat CLI cases;
  independent full-Parquet score reconstruction for all 1,172 districts;
  explicit average-rank tie arithmetic and daytime-only-universe fixture.
- Overlap: unknown. No teammate claim file is present in the audited tree or
  current working tree. This is not evidence that teammates have made no claims
  elsewhere. These checks add concrete evidence even if subjects overlap.
- Work attribution: Codex performed source inspection, checks, calculations and
  drafting. Olga supplied the assignment, reviewed the audit scope, and directed
  exclusion of future development requirements. Personal app use is not claimed.

## AUDIT-01 — Recommended explanation for reversed-date results

- Classification: **Pass with limitation; recommended CLI usability improvement**.
  Empty-output behavior is intentional and covered by existing tests. No explicit
  CLI validation requirement is established by the baseline documentation.
- Requirement/contract: README's documented CLI and empty-result behavior;
  `selected_interval`, `eligible_months`, and existing reversed-date test.
- Severity/impact: Low, usability recommendation rather than correctness defect.
  A manager may not know why the table is empty or how to correct the interval.
- Reproduction: `.venv/Scripts/python.exe -m src.analysis --start 2026-09-19
  --end 2025-01-01 --top 3`.
- Expected under the existing contract: empty result for a reversed interval.
  Recommended enhancement: also explain that start is later than end and show
  how to correct the dates. This enhancement is not an existing acceptance rule.
- Actual: exit code 0, `Empty DataFrame`, columns and `Index: []`, no explanation.
- Evidence: `audits/olga/feature-output.txt`, `src/analysis.py:172` and the
  `selected_interval`/`eligible_months` implementations.
- Requested change: add an explanatory CLI message for a reversed interval while
  preserving the backend's documented empty-frame behavior for callers.
- Proposed acceptance criteria for the enhancement: reversed input produces a
  clear explanation identifying start-after-end; valid empty results receive a
  distinct message; normal ranking output and backend tests remain unchanged.
- Affected component: `src/analysis.py:172`, CLI `main()` presentation.
- Version: 87a892a392727cfaff176d3c0fbbf6019a60eb4a.

## Numeric check — Pass with limitation; no corrective code change requested

Independent score 87.67918088737201 equals production exactly; CLI displays
87.679181. All 1,172 district scores match (maximum absolute difference 0.0).
The small-case tie/universe checks pass. Evidence: `check_metric.py`,
`numeric-output.txt`, `numeric_results.json`. The finding establishes consistency
with the stated formula, not the truth/completeness of source data, policy merit
of the weights, measured lighting conditions or a causal effect.

## Official shared file completed

Root `change-requests.md` was copied from the official template at
https://github.com/USC-DSO-576-YA/09-audit/blob/03e892ce5bc2f6869675a822f05b630fe8f365c1/change-requests.md

Historical source commit: `03e892ce5bc2f6869675a822f05b630fe8f365c1`.
Exact original: `audits/olga/official-change-requests-template.md`.
The historical homework confirms its shared Claims/Requests purpose. The module
removed it in commit `dbcf2ac7b8c62330726d43eb01a54630acec9ec7`.
Neither the local working tree nor origin/main nor live main contained a shared
file before creation, so no teammate entries were overwritten. Unpublished
claims remain unknown. AUDIT-01 is proposed, not implemented. Both feature and
numeric conclusions remain Pass with limitation; no numeric defect is alleged.
