# BUILD SPEC: Community Safety Resource Planner - Streetlight Assessment

## 1. Repository

**Repository:** https://github.com/zayra-rwx/community-safety-resource-planner
**Primary branch:** `main`
The `main` branch contains the finalized Phase 2 deliverables and serves as the authoritative starting point for Phase 3 development.
Before beginning implementation, review the repository structure, `README.md`, `BUILD_SPEC.md`, the canonical cleaned dataset, the backend analysis modules in `src/`, and the existing tests.
All Phase 3 development must follow the specifications, data definitions, and backend contracts established in Phase 2.
For Phase 3 development, create a separate feature branch from the latest `main`. Keep all changes on that feature branch until they have been tested, reviewed, and explicitly approved for merging into `main`.
Do not overwrite or modify the canonical cleaned dataset or existing backend analysis logic without documenting and validating the changes.

## 2. Agent role and objective

You are the coding agent building a local Phase 3 Streamlit dashboard named
**Community Safety Resource Planner: Streetlight Assessment**. Deliver a working
MVP using the full canonical Parquet and existing backend. Implement UI,
presentation adapters and exports; do not recreate tested calculations or use
samples. Change existing backend contracts only for a demonstrated, tested defect.

Complete the nonspatial MVP even though approved streetlight GIS data is absent.
Do not implement streetlight proximity as part of this MVP. Resolve minor
implementation choices yourself; ask only about a genuine contradiction affecting
the user, decision, canonical source, analysis unit or interpretation. Missing
canonical offense data is a blocking error with an exact recovery path, not a
reason to substitute another dataset.

## 3. Current vision

The primary user is an **LA Bureau of Street Lighting planning manager**. The
decision is **which LAPD reporting districts should receive on-site lighting
assessments first**. Replace manual review of disconnected offense records with
a transparent, filterable comparison of recurring nighttime reported-offense
patterns.

This is an assessment-prioritization tool, not a predictive-policing tool. It
does not prove that poor lighting caused reported offenses or claim that
additional lighting will reduce offenses. Do not label districts as dangerous
or recommend enforcement actions. Use “reported offenses,” “assessment priority,”
and “on-site assessment.” Show this text visibly on the starting view:

> Reported-offense patterns and mapped streetlights identify places for further assessment. They do not establish that lighting conditions caused offenses or that additional lighting will reduce them.

Immediately accompany it with: **“Streetlight asset data was unavailable for
this MVP. Rankings use reported-offense frequency and persistence; the map shows
approximate offense locations, not measured lighting conditions.”**

## 4. Core use cases

Every major feature must serve a case below. Do not add unrelated demographic,
enforcement, prediction or causal-analysis features.

1. User selects a date interval and area/offense filters → Dashboard shows ranked reporting districts, key metrics and an approximate offense map → User decides which districts merit initial assessment attention.
2. User selects one reporting district → Dashboard shows monthly counts, persistence, offense composition and premise composition → User decides whether the pattern recurs or is concentrated in a short period or category.
3. User selects two to five districts → Dashboard shows comparable metrics, original ranks and monthly series → User decides their relative assessment order using consistent evidence.
4. User selects filters, a table sort and display limit → Dashboard shows the exportable district worklist and offers its CSV plus metadata → User decides which places to include in a documented field-review worklist.
5. User selects Methods and Data Quality → Dashboard shows source coverage, exclusions, definitions and limitations → User decides how much confidence to place in the screening evidence and whether additional data collection is needed.

## 5. Canonical data contract

### Paths and provenance

Use `src/config.py` as the path/constant authority. Its `ROOT` is derived from
the module location. Load `PROCESSED` through `load_processed()` at startup;
do not search for the first CSV or clean raw data on every application rerun.

| Item | Contract |
|---|---|
| Approved raw CSV (`RAW`) | `data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv` |
| Raw identity | 178,693,032 bytes; 489,956 physical lines; 489,955 parsed data rows; 31 columns |
| Raw SHA-256 | `97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5` |
| Canonical processed data (`PROCESSED`) | `data/processed/lapd_nibrs_offenses.parquet` |
| Processed baseline | Parquet/Zstandard; all 489,955 rows; 45 columns; 24,459,185 bytes |
| Quality/provenance | `reports/phase2/data_quality.json` |
| Schema and types | `reports/phase2/data_dictionary.csv` |
| Cleaning rules | `reports/phase2/cleaning_decisions.md` |
| Baseline documentation | `reports/phase2/backend_validation.json`, `reports/phase2/handoff.md`, current Phase 2 README sections |
| Frozen aggregate examples | `reports/phase2/district_ranking.csv`, `reports/phase2/example_comparison_monthly.csv`, `reports/phase2/offense_summary.csv`, `reports/phase2/premise_summary.csv` |
| Historical, not canonical | `data/raw/lapd_nibrs_offenses_raw.csv`, `data/cleaned/lapd_nibrs_cleaned_sample.csv`, `notebooks/data_cleaning.ipynb` and its old rules |

The ignored raw CSV is read-only and is not required to launch the dashboard
when committed Parquet and quality metadata exist. It is required for source
verification/reproduction. Never stage either raw CSV or configure LFS. Stop a
reproduction operation if approved-source verification fails; do not substitute
another dataset. Frozen example CSVs are regression evidence, not live filtered
app data. Compute live results through the backend.

The launch-required files are exactly the canonical Parquet,
`reports/phase2/data_quality.json` and `reports/phase2/data_dictionary.csv`.
The decision log is authoritative implementation guidance to read during the
build; handoff, validation reports and example CSVs are development evidence,
not runtime dependencies. Methods renders the agreed rules and loaded audit
without requiring those development documents to be parsed at launch.

Treat all stated counts, sizes, dates and example rankings as the **current-source
baseline**, not permanent dashboard constants. Derive displayed results and the
available end date from loaded data. A later approved update must explicitly
revise its source contract, reports and regression baseline; do not automatically
download new data or change the current source hash. Serialization byte size is
descriptive, not a version-independent Parquet identity check.

### Fields and cleaning rules

One row is one NIBRS offense, identified by `UniqueNIBRNo`. Multiple offenses may
share `CaseNo`. The ranking unit is `RPT Dist No`, persistence unit calendar month.
Never sum source `TotalOffenseCount` or `TotalVictimCount` as offense counts.

Validate schema/types against the dictionary before analysis; `load_processed()`
only checks a required column subset, not every type or derived-field invariant.
Add an application validation adapter without silently repairing canonical data.
Distinguish a missing field from a permitted null value.

| Fields | Contract |
|---|---|
| `UniqueNIBRNo`, `CaseNo` | Strings; offense ID for distinct counts, case ID for internal traceability only |
| `RPT Dist No`, `AREA`, `NIBR Code`, `Premise Cd`, `Weapon Used Cd`, `Status` | Categorical strings; preserve leading zeros in widgets, dataframes and exports |
| `AREA NAME`, `NIBR Description`, `Crime Against`, `Premise Desc` | Trimmed source labels; do not invent category mappings |
| `Date OCC`, `Date Rptd` | Parsed timestamps using `%Y %b %d %I:%M:%S %p`; unusable values become `NaT` |
| `Time OCC` | Zero-padded source HHMM string; retain invalid values for quality audit |
| `LAT`, `LON`, `LOCATION` | Nullable numeric coordinates and approximate source location text; not proof of an exact location |
| `TotalOffenseCount`, `TotalVictimCount` | Nullable nonnegative integers; not aggregation measures for this app |
| `offense_date`, `offense_month` | Normalized occurrence date and first day of its calendar month; no timezone conversion |
| `has_valid_time`, `offense_hour` | Valid HHMM flag and nullable integer hour |
| `is_midnight_code`, `is_night` | Normalized time equals `0000`; valid hour >=18 or <6, respectively |
| `has_valid_coordinates` | Inclusive latitude [33.5, 34.9], longitude [-118.9, -117.5] |
| `in_analysis_scope` | Valid occurrence date >=2025-01-01 |
| `has_repeated_offense_id` | Nonmissing ID occurs on multiple nonidentical retained rows |
| `Date OCC_source`, `Date Rptd_source`, `Time OCC_source`, `LAT_source`, `LON_source` | Trimmed original text before conversion |

Preserve these existing decisions:

- Remove only completely identical raw rows before normalization. Retain and
  flag nonidentical repeated offense IDs for review. Monthly/ranking/category
  functions reject repeated IDs in their qualifying nighttime pool; a scalar
  distinct count alone does not establish safe attribution. Never drop a record
  solely because CaseNo repeats. Surface attribution errors, do not choose a row.
- Trim surrounding whitespace, convert blanks to missing, preserve literal
  labels such as `NA`. There is no further canonical category mapping. Do not
  merge labels, collapse internal whitespace or change capitalization.
- Preserve full history in Parquet (baseline 1800-01-06 through 2026-09-19).
  Metrics start **2025-01-01**, capped at the full canonical maximum valid
  `offense_date` (**2026-09-19** currently). The current date and a filtered
  category's last record do not redefine available coverage.
- Valid times have 1-4 digits zero-padded to HHMM, hour 00-23 and minute 00-59.
  Nighttime is **18:00 through 05:59**. Include `0000` as recorded midnight and
  flag it separately. Invalid/missing times remain in quality totals but cannot
  enter nighttime metrics. Do not derive hours from `Date OCC` instead.
- Qualifying nighttime records satisfy date/category filters, `is_night=True`,
  nonmissing district and nonmissing offense ID. Missing coordinates do not
  disqualify them from district metrics.
- Missing, nonnumeric, zero or outside-box coordinates are invalid. The bounds
  above are a broad LA-region screen, not a verified city boundary/geocode.
  Map inputs must use `nighttime_offenses(..., mapped_only=True)`.
- Missing labels stay missing in Parquet. `category_summary` labels missing
  descriptions/premises `Unknown` only in its output. Display absent area labels
  as `Unknown` outside district selectors; selectors use `Area unavailable`
  as specified in section 9. Do not change district keys; retain the backend's sorted
  ` / `-joined area labels when multiple labels occur for one district.

### Streetlight integration: future extension only

No approved streetlight GIS input or proximity implementation exists. The MVP
has no streetlight layer, status selector, nearest-light distance, nearby-light
count or lighting-condition claim. It must function without these capabilities
and show the limitation in section 3. Do not display fabricated or zero-filled
proximity results.

A separately authorized future extension could validate an approved file's
`SLID` (or `STLID`), unique assets, declared CRS and geometry; preserve its raw
source; project valid offense/light geometries to EPSG:2229 (US survey feet); and
return nearest-light distance and distinct light counts within <=150 feet.
Those descriptive measures must never enter the score. No spatial implementation,
dependency or proximity acceptance test is required for this MVP.

## 6. Metric definitions

Use full canonical data plus explicit filters for backend calls (section 11).
In this section **F** means date/area/code/description/crime-against/premise
filters; **D** means district selection. E/T display scopes are defined once in
section 9. All offense metrics use distinct nonmissing offense IDs.

| Metric / question | Source fields | Calculation | Filters and backend return |
|---|---|---|---|
| Nighttime reported offenses: how many qualifying offenses? | `UniqueNIBRNo`, `offense_date`, `is_night`, `RPT Dist No`, filter columns | Distinct IDs in qualifying pool | F+D; integer from `count_nighttime_offenses`, district column from `ranked_districts` |
| Monthly counts: when does the pattern recur? | IDs, district, `offense_month` | Distinct IDs per district/month, explicit zero months | F+D; `monthly_counts` dataframe |
| Eligible months: how long is the selected period? | Full-data `offense_date`, selected endpoints | Number of calendar months intersecting resolved inclusive dates, including partial endpoints | Dates only; length of `eligible_months(*selected_interval(...))` |
| Active months: how many months have an offense? | Monthly counts | Count months with nighttime count >0 | F+D; ranked column |
| Persistence rate: how regularly does it recur? | Active/eligible months | Active / eligible; zero if denominator zero | F+D; ranked column |
| Average monthly nighttime offenses: what is average volume? | Nighttime count, eligible months | Count / eligible; zero if denominator zero | F+D; ranked column |
| Recent nighttime offenses: what is recent volume? | IDs, `offense_date`, nighttime eligibility | Distinct IDs within latest up to three complete selected months | F+D counts; period from dates/full-data availability only; `recent_period` endpoints and ranked column |
| Valid mapped nighttime offenses: how much is mappable? | Qualifying IDs, `has_valid_coordinates` | Distinct qualifying IDs whose flag is true | F+D; `count_nighttime_offenses(mapped_only=True)`, ranked column |
| Mapped coverage: how much evidence is unmapped? | Mapped and total nighttime counts | Mapped / total; display N/A if total zero | Same E or evidence district scope; presentation adapter |
| Frequency percentile: how does volume compare? | Universe district nighttime counts | Ascending average rank divided by universe district count | F only for scoring; ranked percentile column |
| Persistence percentile: how does recurrence compare? | Universe persistence rates | Ascending average rank divided by universe district count | F only for scoring; ranked percentile column |
| Priority score: which district merits earlier assessment? | Two percentile columns | `(0.60 * frequency_percentile + 0.40 * persistence_percentile) * 100`; zero when nighttime count is zero | F for scoring; D limits returned rows only; ranked column |
| Final rank: what is the deterministic order? | Score, count, persistence, district key | Sort rules below; one-based rank before display selection | F for ranking; D limits rows without renumbering; `Rank` column |

The scoring universe contains every nonmissing district represented after F,
including districts with only daytime records. Do not add districts absent from
that filtered data. Percentiles use ascending `rank(method='average', pct=True)`;
do not use min-max or `(rank-1)/(n-1)` scaling. A single positive-count district
scores 100; two equal positive-count districts score 75 each. Zero-count
districts remain in the percentile universe, but their final score is zero.

Never round before ranking/export. Sort by score descending, nighttime count
descending, persistence descending, numeric district ascending (nonnumeric last),
then original district string ascending for residual ties. Preserve original
ranks when display selections leave gaps.

`selected_interval` clamps start to >=2025-01-01 and end to the full-data maximum.
`eligible_months` returns a month-start DatetimeIndex, not an integer; take its
length. Invalid/reversed intervals yield empty months. `recent_period` excludes
partial start/end months but retains complete zero-offense months; it returns
two timestamps or `(None, None)`. No complete months means recent count zero and
label “No complete months.” Default recent period is June 1-August 31, 2026.
For February 1-April 1, 2025, recent months are February-March, while persistence
has three eligible months. Category/district selections do not change the period.

Do not calculate population-adjusted rates; no verified district denominator
exists. No spatial measure enters any MVP metric.

## 7. Starting dashboard view

Open **Priority Overview**. Show title, one-sentence purpose, the visible warning
and streetlight limitation from section 3, data-through date, loaded filename/
row count and fixed nighttime definition. Put filters in a left sidebar, ranked
table in the primary area, approximate offense map beside/below it, and an
expandable data-quality summary. These serve use cases 1, 4 and 5.

Defaults: January 1, 2025 through the loaded maximum (currently September 19,
2026); All areas/districts/codes/descriptions/crime-against/premises; minimum
active months 1; top 10 districts; default rank sort; no evidence or comparison
selection. There is no streetlight-status filter.

KPI cards answer “How much evidence is in the eligible selected scope?” Show
nighttime count, number of districts, unweighted mean district persistence and
mapped nighttime count. Use E's ranked rows (section 9) before top-N: sum count
columns, count rows and average persistence in a presentation adapter. All use
F+D+minimum-active-months, not top-N. Empty E shows zero KPIs and an empty state;
coverage ratios with no denominator show N/A. Label that scope beside the KPIs.

## 8. Dashboard sections or tabs

| View / use cases | Question and metrics | Controls, selection and empty state |
|---|---|---|
| Priority Overview / 1, 4, 5 | Which districts merit assessment first? E KPIs, T ranked table and map, quality context | Global filters, table sort, row selection, clear selection, CSV/metadata download; empty E/T keeps filters and helpful empty message |
| District Evidence / 2 | Is one district's pattern recurring or concentrated? Original rank/score, count, active/eligible months, persistence, coverage, monthly and composition charts | Dropdown from E or table row sets shared active district; none selected prompts selection; zero mapped points leaves metrics/charts usable |
| Compare Districts / 3 | How do selected districts compare on the same evidence? Core ranked metrics and zero-filled monthly series | Pick 2-5 districts from E, including those outside top-N; enforce count in UI; fewer than two available explains why comparison is unavailable |
| Methods and Data Quality / 5 | How reliable and interpretable is this screening evidence? Definitions, provenance, exclusions, coverage, limitations | Expandable definitions/audit; full-source audit is labeled separately from current E coverage; missing required metadata is a named data error |

The ranked table displays the backend's first 11 columns in order: `Rank`,
`RPT Dist No` (label “Reporting district”), `AREA NAME`, `Priority score`,
`Nighttime reported offenses`, `Active months`, `Eligible months`,
`Persistence rate`, `Average monthly nighttime offenses`,
`Recent nighttime offenses`, `Valid mapped nighttime offenses`.
Show recent-period endpoints in the heading/help and exports; expose both
percentiles in expandable score detail. No streetlight columns appear.

District Evidence shows its area, original rank, score and coverage, plus the
visuals defined in section 10. Generate a deterministic evidence sentence from
returned values, not an LLM: district, offense count and active/eligible months.
Do not imply measured lighting conditions or statistical significance.

Methods shows filenames, source hash, loaded rows, available date range, backend/
app revision, and timestamp of last successful load. Show the quality report's
full-source duplicate/pre-2025/date/time/ID/district/coordinate audit and midnight
treatment. Do not sum overlapping exclusion flags as disjoint removals. Separately
label E's filtered mapped coverage. Include all limitations in section 15.

## 9. Filters

Use immutable `Filters` from `src.analysis`: optional `start`, `end` date strings
and tuple-of-string fields `areas`, `districts`, `codes`, `descriptions`,
`crime_against`, `premises`. `None` means All, `()` means no records. Values
within a field are OR-ed; different fields intersect. Provide an explicit All
state; clearing an explicit selection means none, never silently All. All includes
missing categories. Offer actual nonmissing source values as options; summary
label `Unknown` is not a new source filter value.

Provide inclusive dates, area/district multiselects, separate code and description
selectors, crime-against and premise selectors. Code and description selections
intersect; do not assume one-to-one labels. District options derive from the
non-district-filtered universe. Date controls reject reversed/out-of-scope inputs;
if no valid dates exist, show a data error and disable date-dependent controls.

All district selectors (global filters, District Evidence and Compare Districts)
must display both options and selected values as the four-digit reporting district
code followed by the actual LAPD area name: `0182 — Central`, `1494 — Pacific`,
`0636 — Hollywood`. Preserve leading zeros. Derive a stable district-to-area label
mapping from `RPT Dist No` and `AREA NAME` in the full canonical data, before
applying filters; do not invent neighborhood names. Retain the sorted ` / `-joined
area names when a district has multiple names, as specified in section 5. If an
area name is missing or blank, display `0182 — Area unavailable`, substituting the
actual district code. Keep original district IDs as underlying selection values;
labels are presentation only and must not change filtering, scoring, ranks,
comparisons or exports. Filter changes must not rename labels or reset otherwise
valid selections. Preserve the All/none, clear, invalidated-selection and reset
behavior specified in this section and section 10.

Minimum-active-months (1 to eligible-month count) and top-N (5/10/20/all) are
**Phase 3 display logic**, not existing `Filters` fields. Apply this scope order:

1. **U, scoring universe:** call `ranked_districts` with full data and a Filters
   copy whose `districts=None`, preserving F. U is that complete ranked return;
   its row count is the universe count in export metadata. A direct call with D
   set also scores correctly but returns fewer rows, so it cannot supply the U
   count. Never pass district-prefiltered data to scoring or date availability.
2. **E, eligible display scope:** select D's rows from U (All retains every row;
   an empty district tuple retains none), then retain
   `Active months >= minimum_active_months`. District selection and threshold
   cannot recalculate scores/ranks. E supplies KPIs and evidence/comparison choices.
3. **T, overview rows:** take E's top N by original rank (or all), then reorder
   those rows by user table sort. T supplies overview table/map/export. Top-N and
   user sorting cannot change E, scores, original ranks or top-N membership.
4. Row/evidence and comparison choices are view state, not scoring filters.
   Evidence calls use the full dataframe with the same F and the selected district
   tuple. E/T record calls use their explicit ID tuples, including `()` when empty.
   `compare_districts` replaces `filters.districts`; the UI must constrain its
   chosen IDs to E first. All other filters and date availability remain intact.

Label “KPIs: all eligible selected districts,” “Overview: top N of E districts,”
and “Rank: all districts after non-district filters.” Remove evidence/comparison
selections no longer in E when filters change; preserve valid ones. Intersect
explicit district selections with updated choices; an empty intersection stays
none with an explanation. Clamp minimum-active-months to a new positive eligible
maximum; zero eligible months disables that control. Reset restores section 7
defaults, sorting and empty view selections.

## 10. Visuals and interactions

Use Streamlit, Pandas, Plotly and an appropriate map renderer. Keep styling
restrained, accessible and consistent; do not rely on color alone. Every chart
needs title, period, units, useful hover and empty state. Counts display as
integers; rates as percentages; scores may display two decimals. Stored/exported
values remain unrounded.

| Visual / question | Source and calculation | Filters / backend object |
|---|---|---|
| Ranked table: which comes first and why? | District metrics and ordering from section 6, no local reranking | T; `ranked_districts` output, display adapter |
| Overview/evidence map: where are qualifying mapped reports concentrated? | Valid `LAT`/`LON`, district, `offense_month`; deterministic generalized point/cell counts | F + T IDs normally, or active evidence ID; `nighttime_offenses(mapped_only=True)` |
| Monthly line: sustained or concentrated in time? | `offense_month`, district, `nighttime_offenses`; include zero months | F + active district; `monthly_counts` |
| Offense bars: which categories drive the count? | `NIBR Description`, distinct nighttime counts; top 10 + remainder | F + active district; `category_summary` |
| Premise bars: in what types of places? | `Premise Desc`, distinct nighttime counts; top 10 + remainder, missing labeled Unknown | F + active district; `category_summary(..., column='Premise Desc')` |
| Comparison table/panels: how do selected districts differ? | Existing district metrics, separate aligned panels for offense counts and active months | F + 2-5 chosen E IDs; `compare_districts()['districts']` |
| Comparison monthly lines: do patterns recur together? | One zero-filled monthly count series per chosen district | Same comparison scope; `compare_districts()['monthly']` |
| Quality panel: what evidence is missing? | Full-source report counts; current E mapped/total count ratio separately | Full-source audit is unfiltered; E coverage from ranked rows |

Top-10 composition bars follow backend count-descending/label-ascending ordering.
Sum remaining counts in a presentation adapter as “Other (remaining categories)”
to distinguish a literal source label. Totals must reconcile to district counts.
Charts consume adapter outputs; they do not recalculate metrics.

Table-row selection and the evidence dropdown share one active district from E.
The overview map normally shows T. An active evidence district focuses the map
on that district even if it is outside T; label the focused scope. Clearing
selection restores T without changing filters. No district polygon input exists;
use approximate offense aggregation, not invented district boundaries.

Generalize map coordinates deterministically (for example round lat/lon to three
decimal places and aggregate by cell), labeling them approximate. Do not send
original precise coordinates, `LOCATION`, `CaseNo` or `UniqueNIBRNo` to map
hover/custom-data payloads or public downloads. Backend calculations retain
original valid coordinates. Aggregate hover shows counts/period; category-specific
hover may show month, district, area, description and premise, never IDs/addresses.
Rendering aggregation/reduction cannot change analytical counts; label any
reduced rendering. No valid points means a map empty state while tables remain.
Tile/network failure must not disable metrics/charts/export.

Export a UTF-8 CSV of **exactly T**, in current table sort order, before display
rounding, with original ranks, all 15 backend columns and string district IDs.
Provide separate JSON metadata: source filename/hash, processed file signature,
app/backend revision, data-through date, resolved dates, all filter states,
minimum-active-months, top-N, sort, U/E/T counts, recent period, formulas and
percentile method, coordinate rules and streetlight-unavailable statement.
No individual offense identifiers/addresses/precise coordinates. CSV consumers
must import district codes as text to retain leading zeros; do not add spreadsheet
formulas to force formatting. Frozen aggregate examples are not export payloads.

## 11. Application architecture

Reuse these existing public contracts. Unless specified otherwise, functions
are in `src.analysis`; `d` is the full canonical processed dataframe and default
filters are `Filters()`.

| Existing entry point | Inputs → returned output / side effects |
|---|---|
| `src.config` | Repository root → paths `RAW`, `PROCESSED`, `REPORTS`, `START_DATE`, approved source identity/schema, date format, bounds and weights |
| `src.clean_data.verify_source(path=RAW)` | Approved raw path → verification metadata dict; raises on mismatch |
| `src.clean_data.clean_offenses(raw)` | Raw string dataframe with `SOURCE_COLUMNS` → `(processed_dataframe, quality_dict)` without input mutation |
| `load_processed(path=PROCESSED)` | Parquet path → dataframe with required column subset checked |
| `selected_interval(d, filters)` | Full data + dates → `(start, end)` timestamps; end may be NaT with no valid dates |
| `eligible_months(start, end)` | Resolved endpoints → month-start DatetimeIndex, empty for invalid/reversed range |
| `filter_offenses(d, filters, *, include_districts=True)` | Full data + filters → copied date/category-filtered frame, still including daytime/unmapped records |
| `nighttime_offenses(d, filters, *, mapped_only=False)` | Full data + filters → qualifying nighttime copy, optionally mapped only |
| `count_nighttime_offenses(d, filters, *, mapped_only=False)` | Same → integer distinct count |
| `monthly_counts(d, filters)` | Same → `RPT Dist No`, `offense_month`, `nighttime_offenses` dataframe, zero-filled across represented selected districts and eligible months |
| `recent_period(d, filters)` | Full data + dates → complete-month endpoints or `(None, None)` |
| `ranked_districts(d, filters)` | Full data + filters → 15-column ranked table, scoring before district selection |
| `category_summary(d, column='NIBR Description', filters=Filters())` | Column must be description or premise → category and `nighttime_offenses` dataframe, count descending then label ascending |
| `compare_districts(d, districts, filters)` | Full data + chosen district sequence + F → dict with `districts` ranked dataframe and `monthly` dataframe; replaces filters.districts; does not enforce UI 2-5 limit |

The ranked output has the first 11 columns listed in section 8, followed by
`Frequency percentile`, `Persistence percentile`, `Recent period start`,
`Recent period end`. These names, including spaces/capitalization, are exact.
Core functions return values/copies and do not mutate caller data. CLI wrappers
print results; do not use their printed text as an application API.

Add separate Phase 3 components with these contracts; filenames may follow
repository conventions and must be documented:

| Component | Responsibility | Explicit inputs → returned outputs |
|---|---|---|
| Configuration | Reuse constants/paths; centralize display labels/defaults | Repository configuration → settings |
| Data loading | Cached canonical Parquet/quality loading | Paths/file signatures → full frame, report, load metadata |
| Schema validation | Check fields/types/eligibility invariants and metadata consistency | Loaded objects → validated objects or named error |
| Filtering | Translate widget All/none to immutable Filters | UI values → Filters + resolved dates |
| Metrics/presentation adapters | Call backend; construct E/T, KPI summaries, top-category grouping | Full data, Filters, threshold/top-N/sort → named frames/scalars |
| Charts | Render precomputed series/tables with labels | Adapter outputs → Plotly figures or empty state |
| Map | Generalize valid coordinates for display only | Mapped qualifying frame + scope → safe display layer/figure |
| UI/state | Controls, tabs, active/comparison IDs, reset and errors | Settings + returned objects + user events → view/session state |
| Export | Assemble the displayed worklist and metadata | T + scope/provenance → CSV bytes + JSON bytes |
| Tests | Fixtures, adapter/UI invariance and full-data smoke checks | Deterministic inputs → assertions/results |

No hidden global dataframes or private formula copies in charts/UI. Styling
changes must not require editing analysis; metric-definition changes belong in
one tested backend layer, not across visuals. New adapters return objects rather
than only print. Do not implement the dashboard in a cleaning notebook.

## 12. Technical design

Use Python >=3.11. Preserve pinned backend requirements in
`requirements-phase2.txt` (Pandas 3.0.6, PyArrow 23.0.1, pytest 9.0.2).
Add `requirements-phase3.txt` including `-r requirements-phase2.txt` plus pinned
compatible Streamlit, Plotly and any selected map-rendering package. Resolve
versions during implementation and test installation. GIS packages/data are not
required for this MVP. Historical `requirements.txt` is for notebook work.

Existing commands from repository root (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m src.analysis --top 10
```

Reproduction commands, only with approved raw input available:

```powershell
.venv\Scripts\python.exe -m src.clean_data
.venv\Scripts\python.exe -m src.validate_phase2
```

The cleaner verifies source identity before writing Parquet, quality JSON and
dictionary; it does not rewrite the decision log. Validation reconciles the full
data and rewrites aggregate examples and `backend_validation.json`. Neither
command is required on each app launch.

Deliver root `app.py` and the Phase 3 requirements file, then document and test:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-phase3.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m streamlit run app.py
```

These Phase 3 files/commands are deliverables, not files already in the backend
baseline. On macOS/Linux use `.venv/bin/python`. Preserve an existing environment;
if it was created by uv without pip, install with `uv pip install --python
.venv/Scripts/python.exe -r requirements-phase3.txt` as one command, or create a
documented fresh environment. Paths must be repository-relative, not tied to
one Windows user's home directory.

Cache loading by resolved path, size and modification signature; include hashes
in provenance. Cache full-universe aggregates by data signature and immutable F
values. Store widget selections only in session state; apply D, threshold,
top-N, sort and evidence/comparison selection locally to cached universe results.
Do not place mutable selection state or user-specific selected results in a
shared global cache. Invalidate results when input signatures or relevant
settings change. Use grouped/vectorized full-
data calculations and rendering-only map aggregation. Show initial-load progress.
Measure warmed filter changes, targeting median <2 seconds on the development
machine; report actual timings and shortfalls. Do not sample analytical inputs.

Missing Parquet/required metadata/schema produces a blocking named relative-path
error with recovery instructions. Empty filters are valid empty results, not
errors. Map failure leaves metrics/export usable. Keep stack traces, machine
paths and raw IDs out of public errors; use local diagnostics. Update README
with actual setup/run/test commands, definitions and troubleshooting.

## 13. Build order

1. Inspect repository/branch/status, baseline source/tests, dictionary, decisions,
   quality report and Parquet. Preserve unrelated work and run existing tests.
2. Load and validate full Parquet/metadata. With raw available, verify/reconcile
   the approved source; otherwise report raw-verification unavailability while
   continuing processed-data and UI checks. Do not re-clean on app startup.
3. Implement loading/schema adapters, Filters translation, E/T/KPI/composition
   adapters and export contracts. Test against existing backend returns.
4. Build shell, filters and overview, then evidence, comparison and methods views.
   Connect them only to backend/adapter outputs. Show the streetlight limitation.
5. Connect shared selection, clear/reset, map scope, empty/error states, export
   and cache invalidation. Test interactions and data privacy.
6. Run all automated tests and the app with full data, complete acceptance checks,
   measure performance and update README. Fix important failures before handoff.
   Do not merge into `main`.

## 14. Acceptance checks

Use existing core tests and add Phase 3 adapter/UI tests. Distinguish source
regression checks from dynamic filtered UI expectations; do not hard-code totals
into application results. No streetlight proximity test is an MVP requirement.

1. Load the exact canonical Parquet and quality metadata with no raw CSV needed
   at launch. Current baseline has 489,955 rows/45 columns. Missing required
   files/fields gives actionable errors and never falls back to a sample.
2. If raw is available, its size/hash/lines/rows/schema verify exactly. Historical
   raw CSV, notebooks and editor settings remain unchanged.
3. Different offense IDs sharing CaseNo remain separate. Exact source duplicates
   follow cleaning decisions. Repeated qualifying IDs raise attribution errors.
4. `1800`, `2359`, `0000`, `0559` are nighttime; `0600`, `1759` are not. Midnight
   is flagged and included; invalid times do not enter nighttime calculations.
5. Invalid coordinates do not remove district offenses and never enter map data.
   Missing district/ID/date/time eligibility follows backend rules.
6. Monthly output has explicit zero months. Three active of four eligible months
   gives .75; partial selected months count as eligible.
7. Recent period covers three/two/one/zero complete months and partial endpoints;
   sparse categories/districts do not redefine availability. Current default is
   June-August 2026, with 26,646 recent nighttime offenses.
8. Percentile/weight fixtures distinguish 60% frequency and 40% persistence;
   equal positive districts score 75 each; one positive district scores 100.
   Deterministic ties follow numeric district, then source string ordering.
9. Display district selection, comparisons, minimum months and top-N preserve
   retained scores/original ranks from the non-district universe, including its
   represented daytime-only districts. For the same district IDs and other
   filters, readable selector labels leave scores and original ranks unchanged.
10. Full-source regression totals match 179,209 nighttime and 178,921 mapped
    offenses (99.84% coverage), 1,172 districts, 21 eligible months and 24,612
    district-month rows. Quality has 682 retained invalid-coordinate records,
    zero duplicate offenses and zero invalid occurrence dates/times. These are
    unthresholded baseline checks, not top-10 display expectations.
11. All/none states differ; multiple categorical filters intersect. Missing
    categories remain in All. Empty selections show zero/empty states without
    silently reverting to full data. Single and multiple district selections use
    the original district IDs and filter the same records with readable labels.
12. KPIs reconcile to E; table/map/export to T; evidence/comparison to selected E
    districts. Top-N cannot change KPIs. User sorting cannot change T membership.
13. Row/dropdown selections show the same district without changing filters;
    clearing restores T. Invalidated selections clear. Reset restores all defaults.
    All district-selector options and selected values show the section 9 labels,
    including leading-zero codes and the `Area unavailable` fallback for missing
    or blank area names without errors. Changing filters preserves labels and
    otherwise valid selected IDs.
14. Comparison enforces 2-5 E districts, allows choices outside T, and preserves
    common periods and original ranks. Too few choices gives an explanatory state.
15. Export matches T rows/order before rounding, with all 15 columns and accurate
    metadata. Leading-zero codes remain strings. No offense IDs, exact addresses
    or original precise coordinates appear in exports or client map payloads.
16. No fabricated light locations, proximity values or lighting-condition claims
    appear. The streetlight-unavailable note is visible and no status control is
    required; the complete MVP operates without GIS data/packages.
17. Every major feature serves a listed use case. A new user can explain rank,
    recurrence/composition, coverage and limitations, compare and export without
    reading source code. Non-causality and approximate-location notes are visible.
18. Clean setup installs pinned dependencies; tests pass and documented Streamlit
    command works with full data. Cache invalidation, empty/error cases and map
    performance are exercised. No core formula is duplicated in chart/UI code.

## 15. Required final handoff

Provide each created/changed file and responsibility; exact setup/test/run
commands; tested dependency versions; full-data filenames/hash/counts/coverage;
automated results; an acceptance table with pass/fail/unavailable and evidence;
measured performance and remaining limitations. Do not claim unrun checks passed.
Separate delivered MVP functionality from the future streetlight extension.

Explain that reported offenses differ from actual incidents; historical anomalies,
reporting-system changes/delays and partial current months limit comparisons;
locations are approximate and the coordinate box only a screen; midnight source
conventions may be imperfect; streetlight assets are unavailable; and no verified
district population denominator exists. Preserve the non-causal interpretation.

Show Git status, branch and proposed commit contents. Exclude raw CSVs, `.vscode/`,
unrelated notebook work and temporary caches. Await explicit approval before
committing/pushing; do not merge into `main`.
