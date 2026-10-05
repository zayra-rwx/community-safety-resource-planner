"""Independently validate the cleaning outputs against the raw CSV."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW = ROOT.parent / "LAPD_NIBRS_Offenses_Dataset.csv"
OUTPUTS = ROOT / "outputs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype="string", keep_default_na=False, na_filter=False, low_memory=False)


def independent_flags(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    for column in frame.columns:
        frame[column] = frame[column].str.strip().mask(lambda s: s.eq(""))
    occurred = pd.to_datetime(frame["Date OCC"], errors="coerce", format="mixed")
    time_text = frame["Time OCC"].fillna("")
    hour = pd.to_numeric(time_text.str[:2], errors="coerce")
    minute = pd.to_numeric(time_text.str[2:], errors="coerce")
    time_valid = time_text.str.fullmatch(r"\d{4}") & hour.between(0, 23) & minute.between(0, 59)
    lat = pd.to_numeric(frame["LAT"], errors="coerce")
    lon = pd.to_numeric(frame["LON"], errors="coerce")
    in_period = occurred.dt.year.ge(2025) & occurred.notna()
    night = time_valid & ((hour >= 18) | (hour < 6))
    frame["expected_Date Rptd Parsed"] = pd.to_datetime(frame["Date Rptd"], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d %H:%M:%S")
    frame["expected_Date OCC Parsed"] = occurred.dt.strftime("%Y-%m-%d")
    frame["expected_Date OCC Year <= 1900"] = occurred.dt.year.le(1900).fillna(False)
    frame["expected_Time OCC Midnight"] = time_text.eq("0000")
    frame["expected_Coordinates Missing"] = lat.isna() | lon.isna()
    frame["expected_Coordinates Double Zero"] = (lat.eq(0) & lon.eq(0)).fillna(False)
    frame["expected_Coordinates Outside Global Range"] = ((lat.notna() & ~lat.between(-90, 90)) | (lon.notna() & ~lon.between(-180, 180))).fillna(False)
    frame["expected_Analysis Period 2025 Onward"] = (in_period & frame["AREA"].notna()).fillna(False)
    frame["expected_Nighttime 18-05:59"] = (in_period & frame["AREA"].notna() & night).fillna(False)
    frame["expected_Time OCC Valid"] = time_valid.fillna(False)
    frame["expected_Time OCC Hour"] = hour.astype("Int64")
    frame["expected_Coordinates Valid For Mapping"] = (lat.notna() & lon.notna() & ~(lat.eq(0) & lon.eq(0)) & ~((lat.notna() & ~lat.between(-90, 90)) | (lon.notna() & ~lon.between(-180, 180)))).fillna(False)
    frame["expected_Nighttime Excluding 0000"] = (in_period & frame["AREA"].notna() & night & ~frame["expected_Time OCC Midnight"]).fillna(False)
    return frame


def independent_metrics(raw: pd.DataFrame, exclude_midnight: bool = False) -> pd.DataFrame:
    frame = independent_flags(raw)
    valid_time = frame["expected_Time OCC Valid"]
    if exclude_midnight:
        valid_time = valid_time & ~frame["expected_Time OCC Midnight"]
    period = frame[frame["expected_Analysis Period 2025 Onward"] & valid_time].copy()
    night = period[period["expected_Nighttime 18-05:59"]].copy()
    if exclude_midnight:
        night = night[~night["expected_Time OCC Midnight"]]
    rows = []
    for area, group in period.groupby("AREA", sort=True):
        selected = night[night["AREA"].eq(area)]
        rows.append({"AREA": area, "valid_time_offense_records_2025_onward": len(group), "nighttime_offense_records": len(selected), "nighttime_unique_cases": selected["CaseNo"].nunique(), "nighttime_share_of_valid_time_records": len(selected) / len(group), "midnight_excluded": exclude_midnight})
    return pd.DataFrame(rows)


def metrics_match(expected: pd.DataFrame, actual: pd.DataFrame) -> bool:
    """Compare counts exactly and serialized ratios within a fixed tolerance."""
    expected = expected.sort_values("AREA").reset_index(drop=True)
    actual = actual.sort_values("AREA").reset_index(drop=True)
    count_columns = [
        "valid_time_offense_records_2025_onward",
        "nighttime_offense_records",
        "nighttime_unique_cases",
    ]
    if list(expected["AREA"]) != list(actual["AREA"]):
        return False
    if any(expected[column].tolist() != actual[column].tolist() for column in count_columns):
        return False
    if expected["midnight_excluded"].tolist() != actual["midnight_excluded"].tolist():
        return False
    return bool(
        (expected["nighttime_share_of_valid_time_records"] - actual["nighttime_share_of_valid_time_records"])
        .abs()
        .le(1e-12)
        .all()
    )


def normalized(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def choose_validation_cases(raw: pd.DataFrame, independent: pd.DataFrame) -> list[dict]:
    occurred_year = pd.to_datetime(raw["Date OCC"].replace("", pd.NA), errors="coerce", format="mixed").dt.year
    masks = [
        ("leading-zero AREA code and trailing whitespace", raw["AREA NAME"].str.endswith(" ", na=False) & raw["AREA"].str.match(r"^0\d$", na=False)),
        ("same CaseNo with multiple offense records", raw["CaseNo"].duplicated(keep=False)),
        ("midnight offense record", independent["expected_Time OCC Midnight"] & independent["expected_Analysis Period 2025 Onward"]),
        ("early occurrence year", occurred_year.le(1900)),
        ("missing coordinates", raw["LAT"].eq("") | raw["LON"].eq("")),
    ]
    selected = []
    cases = []
    for reason, mask in masks:
        candidates = raw.index[mask & ~raw.index.to_series().isin(selected).to_numpy()]
        if len(candidates):
            position = int(candidates[0])
            selected.append(position)
            cases.append({"position": position, "reason": reason})
    if len(cases) != 5:
        raise AssertionError("Could not select five distinct validation cases")
    return cases


def prepare_record_expectations(raw: pd.DataFrame, independent: pd.DataFrame, cases: list[dict]) -> list[dict]:
    """Write raw-derived expectations before comparing with the cleaned CSV."""
    plans = []
    reasons = [
        "Strip only surrounding whitespace from AREA NAME; keep AREA as a two-character code with its leading zero.",
        "Keep every distinct UniqueNIBRNo sharing the CaseNo; a repeated case is not automatically a duplicate offense.",
        "Keep 0000 as a valid time, flag midnight, and exclude it only from the sensitivity numerator and denominator.",
        "Retain the unusual original occurrence date, flag year <= 1900, and exclude it from the 2025 onward analysis.",
        "Keep empty coordinates missing and flag them as unsuitable for mapping; keep the record for eligible area metrics.",
    ]
    for case, reason in zip(cases, reasons):
        row = raw.iloc[case["position"]]
        flags = independent.iloc[case["position"]]
        original = {k: str(row[k]) for k in ("Date OCC", "Time OCC", "AREA", "AREA NAME", "LAT", "LON", "CaseNo")}
        expected = {k: normalized(row[k]) for k in ("Date OCC", "Time OCC", "AREA", "AREA NAME", "LAT", "LON")}
        expected.update({k: bool(flags[f]) for k, f in {
            "Date OCC Year >= 2025": "expected_Analysis Period 2025 Onward",
            "Time OCC Midnight": "expected_Time OCC Midnight",
            "Coordinates Missing": "expected_Coordinates Missing",
            "Coordinates Double Zero": "expected_Coordinates Double Zero",
            "Date OCC Year <= 1900": "expected_Date OCC Year <= 1900",
            "Coordinates Valid For Mapping": "expected_Coordinates Valid For Mapping",
        }.items()})
        expected["case_unique_nibr_ids_retained"] = sorted(raw.loc[raw["CaseNo"].eq(row["CaseNo"]), "UniqueNIBRNo"].tolist())
        plans.append({"UniqueNIBRNo": row["UniqueNIBRNo"], "selection_reason": case["reason"], "original_values": original, "expected_values": expected, "expected_reason": reason})
    return plans


def as_bool(value) -> bool:
    return normalized(value).lower() == "true"


def compare_records(raw: pd.DataFrame, cleaned: pd.DataFrame, independent: pd.DataFrame) -> tuple[int, dict[str, int]]:
    clean_by_id = cleaned.set_index("UniqueNIBRNo", drop=False)
    expected_by_id = independent.set_index("UniqueNIBRNo", drop=False)
    flag_pairs = {
        "Date Rptd Parsed": "expected_Date Rptd Parsed",
        "Date OCC Parsed": "expected_Date OCC Parsed", "Date OCC Year <= 1900": "expected_Date OCC Year <= 1900",
        "Time OCC Valid": "expected_Time OCC Valid", "Time OCC Hour": "expected_Time OCC Hour", "Time OCC Midnight": "expected_Time OCC Midnight",
        "Coordinates Missing": "expected_Coordinates Missing", "Coordinates Double Zero": "expected_Coordinates Double Zero",
        "Coordinates Outside Global Range": "expected_Coordinates Outside Global Range", "Coordinates Valid For Mapping": "expected_Coordinates Valid For Mapping",
        "Analysis Period 2025 Onward": "expected_Analysis Period 2025 Onward", "Nighttime 18-05:59": "expected_Nighttime 18-05:59", "Nighttime Excluding 0000": "expected_Nighttime Excluding 0000",
    }
    mismatches = {field: 0 for field in raw.columns}
    mismatches.update({field: 0 for field in flag_pairs})
    for identifier, raw_row in raw.set_index("UniqueNIBRNo", drop=False).iterrows():
        clean_row = clean_by_id.loc[identifier]
        expected_row = expected_by_id.loc[identifier]
        for field in raw.columns:
            if normalized(clean_row[field]) != normalized(raw_row[field]):
                mismatches[field] += 1
        for actual_field, expected_field in flag_pairs.items():
            actual = normalized(clean_row[actual_field])
            expected = normalized(expected_row[expected_field])
            if actual.lower() in {"true", "false"}:
                if as_bool(actual) != as_bool(expected):
                    mismatches[actual_field] += 1
            elif actual != expected:
                mismatches[actual_field] += 1
    return sum(mismatches.values()), mismatches


def validate(raw_path: Path = RAW, outputs: Path = OUTPUTS) -> dict:
    raw_path = raw_path.resolve()
    outputs = outputs.resolve()
    cleaned_path = outputs / "cleaned_nibrs.csv"
    if raw_path == cleaned_path:
        raise ValueError("Output path must differ from the original CSV path")
    raw_hash_before = sha256(raw_path)
    raw = read_raw(raw_path)
    independent = independent_flags(raw)
    cases = choose_validation_cases(raw, independent)
    expectations = prepare_record_expectations(raw, independent, cases)
    # Persist predictions before reading this run's cleaned output.
    (outputs / "record_expectations.json").write_text(json.dumps(expectations, indent=2, default=str) + "\n")
    cleaned = pd.read_csv(cleaned_path, dtype="string", keep_default_na=False, na_filter=False, low_memory=False)
    raw_hash_after = sha256(raw_path)
    raw_id_set = set(raw["UniqueNIBRNo"])
    clean_id_set = set(cleaned["UniqueNIBRNo"])
    summary = {
        "raw_rows": len(raw),
        "raw_columns": len(raw.columns),
        "cleaned_rows": len(cleaned),
        "unique_nibr_raw": raw["UniqueNIBRNo"].nunique(),
        "unique_nibr_cleaned": cleaned["UniqueNIBRNo"].nunique(),
        "raw_full_duplicate_rows": int(raw.duplicated().sum()),
        "raw_sha256_before": raw_hash_before, "raw_sha256_after": raw_hash_after, "raw_sha256_unchanged": raw_hash_before == raw_hash_after,
        "cleaned_full_duplicate_rows": int(cleaned.duplicated().sum()),
        "unique_nibr_set_equal": raw_id_set == clean_id_set,
        "raw_unique_nibr": raw["UniqueNIBRNo"].is_unique,
        "cleaned_unique_nibr": cleaned["UniqueNIBRNo"].is_unique,
        "date_rptd_missing_raw": int(raw["Date Rptd"].eq("").sum()),
        "date_rptd_parse_failures_independent": int(pd.to_datetime(raw["Date Rptd"].replace("", pd.NA), errors="coerce", format="mixed").isna().sum() - raw["Date Rptd"].eq("").sum()),
        "date_occ_parse_failures_independent": int(pd.to_datetime(raw["Date OCC"].replace("", pd.NA), errors="coerce", format="mixed").isna().sum()),
        "time_invalid_independent": int((~independent["expected_Time OCC Valid"]).sum()),
        "midnight_count": int(independent["expected_Time OCC Midnight"].sum()),
        "early_date_flag_count": int(independent["expected_Date OCC Year <= 1900"].sum()),
        "coordinate_missing_count": int(independent["expected_Coordinates Missing"].sum()),
        "coordinate_double_zero_count": int(independent["expected_Coordinates Double Zero"].sum()),
        "coordinate_outside_global_count": int(independent["expected_Coordinates Outside Global Range"].sum()),
        "case_count": int(raw["CaseNo"].nunique()),
        "offense_record_count": len(raw),
        "missing_counts_raw": {column: int(raw[column].eq("").sum()) for column in raw.columns if raw[column].eq("").any()},
        "missing_counts_cleaned_original_fields": {column: int(cleaned[column].eq("").sum()) for column in raw.columns if cleaned[column].eq("").any()},
    }
    code_columns = ["AREA", "RPT Dist No", "NIBR Code", "Premise Cd", "Weapon Used Cd"]
    summary["leading_zero_preserved"] = all(
        raw[column].str.strip().eq(cleaned[column]).all()
        for column in code_columns
    )
    checks = {
        "row_count_preserved": summary["raw_rows"] == summary["cleaned_rows"],
        "unique_identifier_preserved": summary["unique_nibr_set_equal"] and summary["cleaned_unique_nibr"],
        "no_raw_full_duplicates": summary["raw_full_duplicate_rows"] == 0,
        "all_time_values_valid": summary["time_invalid_independent"] == 0,
        "raw_sha256_unchanged": summary["raw_sha256_unchanged"],
        "metrics_recomputed_independently": False,
        "boundary_dates_correct": False, "original_fields_only_documented_changes": False, "record_fields_match_by_unique_nibr": False,
    }
    for exclude in (False, True):
        expected = independent_metrics(raw, exclude).sort_values("AREA").reset_index(drop=True)
        actual_name = "metrics_by_area_excluding_midnight.csv" if exclude else "metrics_by_area.csv"
        actual = pd.read_csv(outputs / actual_name, dtype={"AREA": "string"})
        actual = actual.sort_values("AREA").reset_index(drop=True)
        checks["metrics_excluding_midnight_match" if exclude else "metrics_match"] = metrics_match(expected, actual)
    checks["metrics_recomputed_independently"] = checks["metrics_match"] and checks["metrics_excluding_midnight_match"]
    boundary_dates = pd.Series(pd.to_datetime(["2024-12-31 23:59:59", "2025-01-01 00:00:00", "2025-12-31 23:59:59", "2026-01-01 00:00:00"]))
    checks["boundary_dates_correct"] = boundary_dates.dt.year.ge(2025).tolist() == [False, True, True, True]
    record_mismatch_count, record_mismatches = compare_records(raw, cleaned, independent)
    summary["record_field_mismatch_counts"] = record_mismatches
    summary["record_field_mismatch_total"] = record_mismatch_count
    checks["original_fields_only_documented_changes"] = all(record_mismatches[column] == 0 for column in raw.columns)
    checks["record_fields_match_by_unique_nibr"] = record_mismatch_count == 0
    summary["checks"] = checks

    selected_ids = [raw.iloc[item["position"]]["UniqueNIBRNo"] for item in cases]
    double_zero_position = raw.index[raw["LAT"].eq("0") & raw["LON"].eq("0")][0]
    selected_ids.append(raw.iloc[int(double_zero_position)]["UniqueNIBRNo"])
    selected_ids = list(dict.fromkeys(selected_ids))
    remaining = cleaned[~cleaned["UniqueNIBRNo"].isin(selected_ids)]
    extra_count = max(0, min(50, len(cleaned)) - len(selected_ids))
    extra_ids = remaining.sample(n=extra_count, random_state=576)["UniqueNIBRNo"].tolist()
    sample_ids = set(selected_ids + extra_ids)
    cleaned[cleaned["UniqueNIBRNo"].isin(sample_ids)].to_csv(outputs / "sample_50.csv", index=False)
    summary["sample_selection"] = {"source": "cleaned_nibrs.csv", "seed": 576, "required_validation_ids": selected_ids, "rows": len(sample_ids), "all_cleaned_columns": list(cleaned.columns)}
    validation_rows = []
    clean_by_id = cleaned.set_index("UniqueNIBRNo", drop=False)
    boolean_fields = {"Date OCC Year >= 2025": "Analysis Period 2025 Onward", "Time OCC Midnight": "Time OCC Midnight", "Coordinates Missing": "Coordinates Missing", "Coordinates Double Zero": "Coordinates Double Zero", "Date OCC Year <= 1900": "Date OCC Year <= 1900", "Coordinates Valid For Mapping": "Coordinates Valid For Mapping"}
    for plan in expectations:
        identifier = plan["UniqueNIBRNo"]
        actual_row = clean_by_id.loc[identifier]
        actual = {k: normalized(actual_row[k]) for k in ("Date OCC", "Time OCC", "AREA", "AREA NAME", "LAT", "LON")}
        actual.update({k: as_bool(actual_row[col]) for k, col in boolean_fields.items()})
        actual["case_unique_nibr_ids_retained"] = sorted(cleaned.loc[cleaned["CaseNo"].eq(plan["original_values"]["CaseNo"]), "UniqueNIBRNo"].tolist())
        validation_rows.append({"UniqueNIBRNo": identifier, "selection_reason": plan["selection_reason"], "original_values": json.dumps(plan["original_values"]), "expected_values": json.dumps(plan["expected_values"]), "expected_reason": plan["expected_reason"], "actual_values": json.dumps(actual), "matches": plan["expected_values"] == actual})
    record_validation = pd.DataFrame(validation_rows)
    record_validation.to_csv(outputs / "record_validation.csv", index=False)
    summary["five_record_validation_count"] = len(record_validation)
    summary["five_record_validation_all_match"] = bool(len(record_validation) == 5 and record_validation["matches"].all())
    checks["leading_zero_preserved"] = summary["leading_zero_preserved"]
    checks["five_record_validation"] = summary["five_record_validation_all_match"]
    (outputs / "full_validation.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW)
    parser.add_argument("--outputs", type=Path, default=OUTPUTS)
    args = parser.parse_args()
    result = validate(args.input, args.outputs)
    print(json.dumps(result, indent=2, default=str))
    if not all(value is True for value in result["checks"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()