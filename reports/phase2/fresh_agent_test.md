# BUILD_SPEC fresh-agent test

Date: October 18, 2026. Repository: `community-safety-resource-planner`.
Branch: `Olga`. Backend reference: `9e170fccde1a5a7bc2e479428b42e5fd02ecc015`.

## Scope and isolation

Two separate agents reviewed the repository specification using the collaboration
fresh-session mechanism with `fork_turns="none"`. Neither received conversation
history, the user's extended request, prior review findings, or hidden product
clarifications. Each received only the repository location, the instruction to
read its root `BUILD_SPEC.md`, permission to inspect repository files, and the
review task below. Both were instructed not to implement a dashboard or edit
files. Both reported that they made no file changes.

The review task was to explain the product, identify canonical data/backend
entry points, list views/metrics/filters/interactions, describe a build order,
and identify every important question, guess or contradiction. Reviewers were
asked to distinguish material ambiguity from normal implementation discretion
and check the specification against actual backend contracts.

This was a specification comprehension and consistency test, not a dashboard
implementation or usability test. No Phase 3 app was built or tested.

## Source draft and inspection

Exactly one file named `BUILD_SPEC.md` was found under Downloads:
`C:\Users\Olga Tovstogan\Downloads\BUILD_SPEC.md` (32,009 bytes, modification
time reported by the filesystem: October 17, 2026, 7:29:30 PM).
It was copied into the repository root, then only the repository copy was revised.
The Downloads SHA-256 remained:

`fb312a583a1fac5e55b224baeba4f0b6cbe21106a0ef101483a5c90af004d657`

Before revision, the primary agent read the actual README, handoff, configuration,
cleaning/analysis/validation modules, tests, data dictionary, decision log,
quality report, dependency file and processed-data documentation. HEAD matched
the reference commit; no tracked implementation changes were present.

The revision uses the required 15 sections and addresses a future coding agent.
It specifies the actual public APIs and paths, full-data versus display scopes,
date/month/time/ranking rules, mapping/export behavior, runtime dependencies,
architecture, build order and concrete acceptance checks. The current-source
totals are regression evidence, not hard-coded app results. Streetlight integration
is a separate future extension, not required MVP functionality.

## Round 1: fresh_spec_review

The reviewer correctly described a nonspatial local Streamlit assessment tool for
an LA Bureau of Street Lighting planning manager. It identified the canonical
Parquet, metadata, optional raw reproduction input and exact backend entry points.
It reconstructed all four views, immutable filters, nighttime/persistence/recent
definitions, scoring rules and E/T interactions without conversational help.

Its initial verdict was that no question blocked starting and no actual backend
contradiction existed, but it recommended these three consequential clarifications:

| Issue found | Why the wording allowed a guess | Correction made | Retest outcome |
|---|---|---|---|
| U count could accidentally use the D-restricted return | The U step called ranking with the ordinary Filters object; the backend scores across U but returns only D rows when districts are selected | Section 9 now explicitly obtains U with `districts=None`, counts that full return, then applies D and the threshold to derive E | Round 2 reconstructed U/E/T correctly and found no ambiguity |
| Shared caching versus per-user district state | “Cache immutable filter/display values” and “keep selected districts out of global caches” could suggest different cache boundaries | Section 12 caches full-universe results by data signature and non-district filters; D, threshold, top-N, sort and view selections apply locally; widget state stays in session state | Round 2 accepted the cache/state separation |
| Launch-required metadata not exhaustively named | The spec mentioned quality, dictionary, decisions, handoff and example outputs without a single runtime dependency list | Section 5 now names exactly Parquet, quality JSON and dictionary as launch-required files; decision log is build guidance, other reports/examples are development evidence | Round 2 identified the exact runtime set |

No cleaning/backend defect was identified, so no implementation changes were
made. Normal discretion remained for filenames, styling, map renderer,
generalization details, sort controls, metadata serialization and dependency
versions resolved during the future build.

The reviewer independently executed read-only backend calls against the full
Parquet and confirmed its shape, available end date, ranked-table shape,
nighttime/mapped totals and recent endpoints. It explicitly did not claim to
have run the whole test suite or raw-source verification.

## Round 2: fresh_spec_retest

A different isolated agent reviewed the revised file without Round 1 context.
Its verdict was:

> A new agent can begin correctly without material clarification.

It found no material contradiction with the actual backend. Its independent
interpretation covered:

- Product: an assessment-prioritization MVP using reported-offense recurrence,
  with visible non-causality and streetlight-unavailable notices.
- Inputs: canonical Parquet through `load_processed`, quality JSON and dictionary
  required at runtime; raw needed only for verification/reproduction.
- APIs: `Filters`, `selected_interval`, `eligible_months`, `filter_offenses`,
  `nighttime_offenses`, `count_nighttime_offenses`, `monthly_counts`,
  `recent_period`, `ranked_districts`, `category_summary`, `compare_districts`.
- Views: Priority Overview, District Evidence, Compare Districts, Methods and
  Data Quality. U is the non-district universe, E applies district/threshold
  selection, T chooses top-N membership before display sorting. KPIs use E;
  overview/export use T; active evidence selection can override map focus.
- Behavior: preserve original ranks, distinguish All from none, compare 2-5 E
  districts, include zero months, preserve midnight, generalize map coordinates
  only for rendering, and exclude IDs/addresses/precise coordinates from public
  payloads. No GIS implementation is required.
- Build order: inspect/test baseline, validate full Parquet/metadata, build
  adapters, build views, connect state/maps/exports/caching, validate and document.

The reviewer independently ran full-data analytical smoke checks:

| Check | Observed result |
|---|---:|
| Processed shape | 489,955 rows x 45 columns |
| Scoring universe districts | 1,172 |
| Eligible months | 21 |
| District-month rows | 24,612 |
| Nighttime offenses | 179,209 |
| Mapped nighttime offenses | 178,921 |
| Recent nighttime offenses | 26,646 |
| Recent period | June 1-August 31, 2026 |

Remaining choices were explicitly classified as ordinary implementation
discretion: module names, compatible UI dependency versions, renderer/layout,
All/none widget design, sort-control presentation, deterministic coordinate
grid, metadata serialization/revision labels, validation internals, and optional
cascading of non-district category choices without changing filter semantics.
No important product, data, metric, architecture or interaction decision required
guessing. A genuinely missing/corrupt future input or conflicting offense ID is
a documented failure path, not an unresolved question in this specification.

## Final validation

| Validation | Result |
|---|---|
| Root file and repository URL | `BUILD_SPEC.md` exists at repository root with the correct team URL |
| Required organization | All 15 numbered sections present in order |
| Use-case syntax | Five use cases each follow User selects ... → Dashboard shows ... → User decides ... |
| Metrics and visuals | Compact tables specify questions, fields, calculations, filters and backend returns; features map to use cases |
| Backend contracts | Both reviewers checked actual source; all public analysis entry points documented; no contradictory implementation change needed |
| Streetlights | Absent, unimplemented and future-only; no required proximity/status feature or spatial acceptance check |
| Automated regression suite | `.venv\Scripts\python.exe -m pytest -q`: **40 passed in 3.33 seconds** |
| Markdown | No markdownlint executable installed; available Mistune 3.3.4 parsed the spec successfully, including all seven tables with consistent row widths |
| Structural/text checks | Balanced fences, correct headings, no embedded Python implementations, no unresolved TODO/TBD/placeholder markers, no trailing whitespace |
| Source preservation | Downloads hash unchanged; Phase 2 implementation/tests/data/README unchanged from reference commit |
| Git whitespace | `git diff --check` and staged whitespace checks passed |
| Proposed changes | Only root `BUILD_SPEC.md` and this review report; `.vscode/` remains untracked; raw files, notebook work and other files excluded |

The final reviewed specification SHA-256 is:

`b49d2d0e214c92ce9bf842cecc0d9c9eb05d7ed540f2ad0b4682029b33ef3e93`

This records the working-file bytes reviewed before Git line-ending normalization.
No commit, push, merge, or manual PR edit was performed for this documentation
task. Proposed commit contents await owner approval.
