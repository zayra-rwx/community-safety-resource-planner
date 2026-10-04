"""Clean and validate the two LAPD project datasets without changing source files.

The script writes only small, reviewable assignment evidence by default. It keeps
the NIBRS and Legacy reporting systems separate because their rows and offense
structures are not directly comparable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


NIBRS_FILENAME = "export.csv%3FaccessType=DOWNLOAD.csv"
LEGACY_FILENAME = "export.csv%3FaccessType=DOWNLOAD (1).csv"
NIGHT_START_HOUR = 20
NIGHT_END_HOUR = 6
EARLY_DATE_CUTOFF = pd.Timestamp("2000-01-01")
LEGACY_CHUNKSIZE = 100_000


def find_source(filename: str, data_dir: Path | None) -> Path:
    candidates = []
    if data_dir is not None:
        candidates.append(data_dir / filename)
    candidates.extend([Path("../dataset") / filename, Path("dataset") / filename])
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not find {filename}. Use --data-dir to identify its folder.")


def valid_time_parts(values: pd.Series) -> tuple[pd.Series, pd.Series]:
    numeric = pd.to_numeric(values, errors="coerce")
    valid = (
        values.str.len().eq(4)
        & values.str.isdigit()
        & numeric.floordiv(100).between(0, 23)
        & numeric.mod(100).between(0, 59)
    )
    hour = numeric.floordiv(100).where(valid).astype("Int64")
    return valid, hour


def nighttime(hour: pd.Series) -> pd.Series:
    return (hour.ge(NIGHT_START_HOUR) | hour.lt(NIGHT_END_HOUR)).fillna(False)


def clean_nibrs(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    clean = raw.copy()
    trim_counts: dict[str, int] = {}
    for column in raw.columns:
        after = clean[column].str.strip()
        trim_counts[column] = int(
            clean[column].fillna("<MISSING>").ne(after.fillna("<MISSING>")).sum()
        )
        clean[column] = after

    for column in ["Date Rptd", "Date OCC"]:
        clean[column] = pd.to_datetime(
            clean[column], format="%Y %b %d %I:%M:%S %p", errors="coerce"
        )
    for column in ["TotalOffenseCount", "TotalVictimCount", "LAT", "LON"]:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    time_valid, clean["Hour OCC"] = valid_time_parts(clean["Time OCC"])
    clean["time_invalid_flag"] = ~time_valid
    clean["time_0000_flag"] = clean["Time OCC"].eq("0000")
    clean["early_date_review_flag"] = clean["Date OCC"].lt(EARLY_DATE_CUTOFF).fillna(False)
    clean["coordinate_issue_flag"] = (
        clean["LAT"].isna()
        | clean["LON"].isna()
        | clean["LAT"].eq(0)
        | clean["LON"].eq(0)
        | ~clean["LAT"].between(-90, 90)
        | ~clean["LON"].between(-180, 180)
    )
    clean["nighttime_flag"] = nighttime(clean["Hour OCC"])
    return clean, trim_counts


def clean_legacy_chunk(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    clean = raw.copy()
    trim_counts: dict[str, int] = {}
    for column in raw.columns:
        after = clean[column].str.strip()
        trim_counts[column] = int(
            clean[column].fillna("<MISSING>").ne(after.fillna("<MISSING>")).sum()
        )
        clean[column] = after

    clean["Date Rptd"] = pd.to_datetime(
        clean["Date Rptd"], format="%Y %b %d %I:%M:%S %p", errors="coerce"
    )
    clean["DATE OCC"] = pd.to_datetime(
        clean["DATE OCC"], format="%Y %b %d %I:%M:%S %p", errors="coerce"
    )
    for column in ["Vict Age", "LAT", "LON"]:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    time_valid, clean["Hour OCC"] = valid_time_parts(clean["TIME OCC"])
    clean["time_invalid_flag"] = ~time_valid
    clean["time_0000_flag"] = clean["TIME OCC"].eq("0000")
    clean["coordinate_issue_flag"] = (
        clean["LAT"].isna()
        | clean["LON"].isna()
        | clean["LAT"].eq(0)
        | clean["LON"].eq(0)
        | ~clean["LAT"].between(-90, 90)
        | ~clean["LON"].between(-180, 180)
    )
    clean["nighttime_flag"] = nighttime(clean["Hour OCC"])
    clean["additional_crime_code_flag"] = clean[["Crm Cd 2", "Crm Cd 3", "Crm Cd 4"]].notna().any(axis=1)
    return clean, trim_counts


def compact_nibrs(rows: pd.DataFrame, reasons: dict[str, str]) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "source": "NIBRS",
            "record_id": rows["UniqueNIBRNo"],
            "case_id": rows["CaseNo"],
            "date_occ": rows["Date OCC"],
            "time_occ": rows["Time OCC"],
            "area_name": rows["AREA NAME"],
            "reporting_district": rows["RPT Dist No"],
            "offense_code": rows["NIBR Code"],
            "offense_description": rows["NIBR Description"],
            "premise_description": rows["Premise Desc"],
            "location": rows["LOCATION"],
            "latitude": rows["LAT"],
            "longitude": rows["LON"],
            "early_date_review_flag": rows["early_date_review_flag"],
            "time_0000_flag": rows["time_0000_flag"],
            "coordinate_issue_flag": rows["coordinate_issue_flag"],
            "nighttime_flag": rows["nighttime_flag"],
        }
    )
    result["selection_reason"] = result["record_id"].map(reasons).fillna("deterministic context sample")
    return result


def compact_legacy(rows: pd.DataFrame, reasons: dict[str, str]) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "source": "Legacy",
            "record_id": rows["DR_NO"],
            "case_id": "Not separately established",
            "date_occ": rows["DATE OCC"],
            "time_occ": rows["TIME OCC"],
            "area_name": rows["AREA NAME"],
            "reporting_district": rows["Rpt Dist No"],
            "offense_code": rows["Crm Cd"],
            "offense_description": rows["Crm Cd Desc"],
            "premise_description": rows["Premis Desc"],
            "location": rows["LOCATION"],
            "latitude": rows["LAT"],
            "longitude": rows["LON"],
            "early_date_review_flag": False,
            "time_0000_flag": rows["time_0000_flag"],
            "coordinate_issue_flag": rows["coordinate_issue_flag"],
            "nighttime_flag": rows["nighttime_flag"],
        }
    )
    result["selection_reason"] = result["record_id"].map(reasons).fillna("deterministic context sample")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    nibrs_path = find_source(NIBRS_FILENAME, args.data_dir)
    legacy_path = find_source(LEGACY_FILENAME, args.data_dir)
    nibrs_raw = pd.read_csv(
        nibrs_path, dtype="string[pyarrow]", keep_default_na=False, na_values=[""], low_memory=False
    )
    nibrs, nibrs_trim = clean_nibrs(nibrs_raw)

    nibrs_checks = pd.DataFrame(
        {
            "check": [
                "row count preserved",
                "source columns preserved",
                "UniqueNIBRNo nonmissing",
                "UniqueNIBRNo unique",
                "CaseNo remains text",
                "Time OCC remains text",
            ],
            "passed": [
                len(nibrs) == len(nibrs_raw),
                set(nibrs_raw.columns).issubset(nibrs.columns),
                nibrs["UniqueNIBRNo"].notna().all(),
                nibrs["UniqueNIBRNo"].is_unique,
                str(nibrs["CaseNo"].dtype).startswith("string"),
                str(nibrs["Time OCC"].dtype).startswith("string"),
            ],
        }
    )
    assert nibrs_checks["passed"].all()

    missing_rows = []
    for column in nibrs_raw.columns:
        missing_rows.append(
            {
                "source": "NIBRS",
                "column": column,
                "raw_missing": int(nibrs_raw[column].isna().sum()),
                "clean_missing": int(nibrs[column].isna().sum()),
            }
        )

    legacy_rows = 0
    legacy_ids: set[str] = set()
    legacy_duplicate_ids = 0
    legacy_missing_ids = 0
    legacy_invalid_dates = 0
    legacy_invalid_times = 0
    legacy_coordinate_issues = 0
    legacy_trim_total = 0
    legacy_raw_missing: pd.Series | None = None
    legacy_clean_missing: pd.Series | None = None
    legacy_context: list[pd.DataFrame] = []
    legacy_difficult: list[pd.DataFrame] = []

    reader = pd.read_csv(
        legacy_path,
        dtype="string[pyarrow]",
        keep_default_na=False,
        na_values=[""],
        chunksize=LEGACY_CHUNKSIZE,
        low_memory=False,
    )
    for raw_chunk in reader:
        clean_chunk, trim_counts = clean_legacy_chunk(raw_chunk)
        legacy_rows += len(raw_chunk)
        legacy_trim_total += sum(trim_counts.values())
        raw_missing = raw_chunk.isna().sum()
        clean_missing = clean_chunk[raw_chunk.columns].isna().sum()
        legacy_raw_missing = raw_missing if legacy_raw_missing is None else legacy_raw_missing.add(raw_missing)
        legacy_clean_missing = clean_missing if legacy_clean_missing is None else legacy_clean_missing.add(clean_missing)

        ids = clean_chunk["DR_NO"].dropna().astype(str)
        legacy_duplicate_ids += int(ids.duplicated().sum()) + len(set(ids) & legacy_ids)
        legacy_ids.update(ids)
        legacy_missing_ids += int(clean_chunk["DR_NO"].isna().sum())
        legacy_invalid_dates += int(clean_chunk["DATE OCC"].isna().sum())
        legacy_invalid_times += int(clean_chunk["time_invalid_flag"].sum())
        legacy_coordinate_issues += int(clean_chunk["coordinate_issue_flag"].sum())

        if sum(len(frame) for frame in legacy_context) < 12:
            needed = 12 - sum(len(frame) for frame in legacy_context)
            legacy_context.append(clean_chunk.head(needed).copy())
        match = clean_chunk.loc[clean_chunk["DR_NO"].eq("201115217")]
        if not match.empty:
            legacy_difficult.append(match.copy())

    assert legacy_raw_missing is not None and legacy_clean_missing is not None
    assert legacy_rows == 1_004_894
    assert legacy_missing_ids == 0 and legacy_duplicate_ids == 0
    assert legacy_difficult, "Approved Legacy record 201115217 was not found"

    for column in legacy_raw_missing.index:
        missing_rows.append(
            {
                "source": "Legacy",
                "column": column,
                "raw_missing": int(legacy_raw_missing[column]),
                "clean_missing": int(legacy_clean_missing[column]),
            }
        )

    legacy_checks = pd.DataFrame(
        {
            "check": [
                "row count preserved",
                "all 28 source columns observed",
                "DR_NO nonmissing",
                "DR_NO unique",
                "every row processed",
            ],
            "passed": [
                legacy_rows == 1_004_894,
                len(legacy_raw_missing) == 28,
                legacy_missing_ids == 0,
                legacy_duplicate_ids == 0,
                legacy_rows == 1_004_894,
            ],
        }
    )
    assert legacy_checks["passed"].all()

    # Approved record checks: expected values were written before the actual comparisons.
    checks: list[dict[str, object]] = []
    early = nibrs.loc[nibrs["UniqueNIBRNo"].eq("25164160_11B_0")].iloc[0]
    checks.append(
        {
            "source": "NIBRS",
            "record_id": "25164160_11B_0",
            "difficult_case": "occurrence date before 2000",
            "original": str(nibrs_raw.loc[nibrs_raw["UniqueNIBRNo"].eq("25164160_11B_0"), "Date OCC"].iloc[0]),
            "expected": "parse the date, retain the row, and set early_date_review_flag=True",
            "actual": f"Date OCC={early['Date OCC']}; early_date_review_flag={early['early_date_review_flag']}",
            "matches": bool(early["Date OCC"] == pd.Timestamp("1984-02-16 13:00:00") and early["early_date_review_flag"]),
        }
    )
    zero = nibrs.loc[nibrs["UniqueNIBRNo"].eq("25161740_200_0")].iloc[0]
    checks.append(
        {
            "source": "NIBRS",
            "record_id": "25161740_200_0",
            "difficult_case": "zero coordinates",
            "original": "LAT=0; LON=0",
            "expected": "retain numeric zeros and set coordinate_issue_flag=True",
            "actual": f"LAT={zero['LAT']}; LON={zero['LON']}; coordinate_issue_flag={zero['coordinate_issue_flag']}",
            "matches": bool(zero["LAT"] == 0 and zero["LON"] == 0 and zero["coordinate_issue_flag"]),
        }
    )
    midnight = nibrs.loc[nibrs["UniqueNIBRNo"].eq("25158829_13B_0")].iloc[0]
    checks.append(
        {
            "source": "NIBRS",
            "record_id": "25158829_13B_0",
            "difficult_case": "Time OCC equals 0000",
            "original": "Time OCC=0000",
            "expected": "retain 0000, derive Hour OCC=0, and set both time_0000_flag and nighttime_flag",
            "actual": f"Time OCC={midnight['Time OCC']}; Hour OCC={midnight['Hour OCC']}; time_0000_flag={midnight['time_0000_flag']}; nighttime_flag={midnight['nighttime_flag']}",
            "matches": bool(midnight["Time OCC"] == "0000" and midnight["Hour OCC"] == 0 and midnight["time_0000_flag"] and midnight["nighttime_flag"]),
        }
    )
    multi = nibrs.loc[nibrs["CaseNo"].eq("25164452")]
    checks.append(
        {
            "source": "NIBRS",
            "record_id": "CaseNo 25164452",
            "difficult_case": "one case has multiple offense rows",
            "original": f"UniqueNIBRNo values={'; '.join(multi['UniqueNIBRNo'].tolist())}",
            "expected": "retain two offense rows while counting one distinct case",
            "actual": f"offense_rows={len(multi)}; distinct_cases={multi['CaseNo'].nunique()}",
            "matches": bool(len(multi) == 2 and multi["CaseNo"].nunique() == 1),
        }
    )
    legacy_record = legacy_difficult[0].iloc[0]
    checks.append(
        {
            "source": "Legacy",
            "record_id": "201115217",
            "difficult_case": "additional legacy crime code",
            "original": f"Crm Cd={legacy_record['Crm Cd']}; Crm Cd 1={legacy_record['Crm Cd 1']}; Crm Cd 2={legacy_record['Crm Cd 2']}",
            "expected": "retain the primary and additional codes and set additional_crime_code_flag=True",
            "actual": f"Crm Cd={legacy_record['Crm Cd']}; Crm Cd 1={legacy_record['Crm Cd 1']}; Crm Cd 2={legacy_record['Crm Cd 2']}; additional_crime_code_flag={legacy_record['additional_crime_code_flag']}",
            "matches": bool(legacy_record["Crm Cd"] == "812" and legacy_record["Crm Cd 1"] == "812" and legacy_record["Crm Cd 2"] == "860" and legacy_record["additional_crime_code_flag"]),
        }
    )
    record_checks = pd.DataFrame(checks)
    assert record_checks["matches"].all()

    nibrs_reasons = {
        "25164160_11B_0": "approved check: early occurrence date",
        "25161740_200_0": "approved check: zero coordinates",
        "25158829_13B_0": "approved check: 0000 occurrence time",
        "25164452_23G_0": "approved check: multi-offense case",
        "25164452_290_1": "approved check: multi-offense case",
    }
    nibrs_ids = list(nibrs_reasons)
    nibrs_sample_rows = pd.concat(
        [nibrs.loc[nibrs["UniqueNIBRNo"].isin(nibrs_ids)], nibrs.head(12)], ignore_index=True
    ).drop_duplicates("UniqueNIBRNo")
    legacy_context_frame = pd.concat(legacy_context, ignore_index=True)
    legacy_sample_rows = pd.concat([legacy_difficult[0], legacy_context_frame], ignore_index=True).drop_duplicates("DR_NO")
    sample = pd.concat(
        [
            compact_nibrs(nibrs_sample_rows, nibrs_reasons),
            compact_legacy(legacy_sample_rows, {"201115217": "approved check: additional crime code"}),
        ],
        ignore_index=True,
    )
    assert len(sample) <= 50

    decision_log = pd.DataFrame(
        [
            ["Preserve source files", "Source files are the audit trail", "Read-only paths; outputs written separately", "source paths and row counts recorded"],
            ["Preserve source row meanings", "NIBRS offense rows and Legacy records are not equivalent", "Clean separately; do not append", "separate validation summaries"],
            ["Trim outer whitespace", "NIBRS AREA NAME contains padding", "Trim text only; preserve internal text", f"NIBRS changed cells={sum(nibrs_trim.values()):,}; Legacy changed cells={legacy_trim_total:,}"],
            ["Preserve identifiers as text", "Leading zeros and code formatting matter", "Load all source columns as string", "identifier uniqueness and dtype checks"],
            ["Parse dates explicitly", "Analysis requires dates and failed conversions must be visible", "Use the documented source format with errors='coerce'", f"NIBRS early dates={int(nibrs['early_date_review_flag'].sum()):,}; Legacy invalid occurrence dates={legacy_invalid_dates:,}"],
            ["Keep suspicious dates", "An unusual date is not proof of error", "Flag NIBRS dates before 2000", f"flagged rows={int(nibrs['early_date_review_flag'].sum()):,}"],
            ["Validate occurrence time", "HHMM must have a valid hour and minute", "Keep source text; derive Hour OCC and flags", f"NIBRS invalid={int(nibrs['time_invalid_flag'].sum()):,}; Legacy invalid={legacy_invalid_times:,}"],
            ["Flag coordinate problems", "Missing or zero coordinates cannot support point mapping", "Keep rows; add coordinate_issue_flag", f"NIBRS flagged={int(nibrs['coordinate_issue_flag'].sum()):,}; Legacy flagged={legacy_coordinate_issues:,}"],
            ["Nighttime is an analysis rule", "Clock time is not proof of darkness", "Temporarily use 20:00-05:59 and label it", f"NIBRS nighttime rows={int(nibrs['nighttime_flag'].sum()):,}"],
            ["Preserve additional Legacy codes", "One Legacy row may contain multiple recorded codes", "Keep Crm Cd 1-4 and add a flag", "approved record 201115217 passed"],
        ],
        columns=["rule", "reason", "implementation", "check"],
    )

    summary = {
        "nibrs_source": str(nibrs_path),
        "legacy_source": str(legacy_path),
        "nighttime_definition": "20:00 through 05:59 local clock time",
        "nibrs_primary_metric": "distinct CaseNo",
        "nibrs_secondary_metric": "offense records counted by UniqueNIBRNo",
        "legacy_metric": "Legacy records counted by DR_NO and reported separately",
        "nibrs_rows_raw": len(nibrs_raw),
        "nibrs_rows_clean": len(nibrs),
        "legacy_rows_raw": legacy_rows,
        "legacy_rows_clean": legacy_rows,
        "nibrs_distinct_offense_ids": int(nibrs["UniqueNIBRNo"].nunique()),
        "nibrs_distinct_cases": int(nibrs["CaseNo"].nunique()),
        "legacy_distinct_ids": len(legacy_ids),
        "nibrs_trimmed_cells": sum(nibrs_trim.values()),
        "legacy_trimmed_cells": legacy_trim_total,
        "nibrs_early_date_rows": int(nibrs["early_date_review_flag"].sum()),
        "nibrs_coordinate_issue_rows": int(nibrs["coordinate_issue_flag"].sum()),
        "legacy_coordinate_issue_rows": legacy_coordinate_issues,
        "nibrs_time_0000_rows": int(nibrs["time_0000_flag"].sum()),
        "record_checks_passed": int(record_checks["matches"].sum()),
        "record_checks_total": len(record_checks),
        "sample_rows": len(sample),
    }

    nibrs_checks.to_csv(args.output_dir / "nibrs_validation.csv", index=False)
    legacy_checks.to_csv(args.output_dir / "legacy_validation.csv", index=False)
    pd.DataFrame(missing_rows).to_csv(args.output_dir / "missing_values_before_after.csv", index=False)
    decision_log.to_csv(args.output_dir / "cleaning_decision_log.csv", index=False)
    record_checks.to_csv(args.output_dir / "record_checks.csv", index=False)
    sample.to_csv(args.output_dir / "data_sample.csv", index=False)
    (args.output_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
