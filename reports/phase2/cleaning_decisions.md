# Canonical Phase 2 decisions

This pipeline supersedes the older notebook's analysis definitions. The notebook,
its outputs, and the former raw file remain historical artifacts, unchanged.

1. Verify the approved filename's exact size, SHA-256, physical lines, parsed CSV
   rows and schema before output. Read all fields initially as strings. Empty
   fields and whitespace-only text become missing; literal category labels such
   as `NA` are not automatically converted to null. Trim surrounding whitespace;
   do not invent category mappings or merge labels.
2. Drop only rows identical across all raw columns, before normalization. Retain
   all nonidentical repeated offense IDs and flag them. Analysis refuses such
   conflicting IDs until adjudicated. Retain repeated CaseNo values. Report both
   repeated values and all rows belonging to repeated values.
3. Parse source date strings using `%Y %b %d %I:%M:%S %p`. Retain source text in
   audit columns. Retain historical and unusable dates in processed data. Analyze
   only dates >= 2025-01-01; timestamps normalize to inclusive calendar dates.
4. Zero-pad digit times to HHMM, validate hour 00-23 and minute 00-59. Preserve
   invalid values and source text. `0000` is midnight, flagged separately, and
   INCLUDED in nighttime metrics. Nighttime is 18:00 through 05:59, superseding
   the notebook's 20:00 start and exclusion of midnight from its main measure.
5. Keep identifiers and categorical codes as strings, preserving leading zeros.
   Convert counts to nullable nonnegative integers, coordinates to nullable
   floating point, dates to timestamps and derived flags to booleans. Missing
   values are not imputed. Source CSV preserves all original values.
6. Coordinates pass a broad inclusive LA-region box: latitude 33.5 to 34.9,
   longitude -118.9 to -117.5. Missing, nonnumeric, zero and out-of-box coordinates
   are invalid. This is screening, not proof of an in-city location. Coordinate
   issues never remove otherwise qualifying district records. Spatial/map inputs
   must use `nighttime_offenses(..., mapped_only=True)`.
7. Save the full-history canonical dataset to Parquet; no sampling or date-based
   deletions. Quality counts refer to processed records unless labeled raw or
   duplicate counts. Qualifying nighttime coverage uses the 2025-forward valid
   date/time, nonmissing district and offense-ID pool. Coordinate issue categories
   are reported separately; total invalid coverage is the authoritative union.
8. No approved streetlight asset file exists in this checkout. Do not calculate
   invented distances, zero-fill unavailable proximity, or download alternatives.
   Future processing must validate SLID/STLID and geometry, use EPSG:2229 in US
   feet, and count lights within 150 feet, separately from the priority score.

See data_quality.json for measured counts and data_dictionary.csv for every
source, derived and audit column. No source record is deleted on CaseNo alone.
