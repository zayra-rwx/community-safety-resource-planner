"""Clean the LAPD NIBRS export without changing the raw input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT.parent / "LAPD_NIBRS_Offenses_Dataset.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "cleaned_nibrs.csv"
PERIOD_START = pd.Timestamp("2025-01-01")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype="string", keep_default_na=False, na_filter=False, low_memory=False)


def clean_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw.copy()
    for column in cleaned.columns:
        cleaned[column] = cleaned[column].str.strip()
        cleaned[column] = cleaned[column].mask(cleaned[column].eq(""))

    date_reported = pd.to_datetime(cleaned["Date Rptd"], errors="coerce", format="mixed")
    date_occurred = pd.to_datetime(cleaned["Date OCC"], errors="coerce", format="mixed")
    time_text = cleaned["Time OCC"].fillna("")
    time_valid = time_text.str.fullmatch(r"\d{4}")
    hour = pd.to_numeric(time_text.str[:2], errors="coerce")
    minute = pd.to_numeric(time_text.str[2:], errors="coerce")
    time_valid = time_valid & hour.between(0, 23) & minute.between(0, 59)

    lat = pd.to_numeric(cleaned["LAT"], errors="coerce")
    lon = pd.to_numeric(cleaned["LON"], errors="coerce")
    double_zero = lat.eq(0) & lon.eq(0)
    outside_global = ((lat.notna() & ~lat.between(-90, 90)) | (lon.notna() & ~lon.between(-180, 180)))
    valid_coordinates = lat.notna() & lon.notna() & ~double_zero & ~outside_global

    cleaned["Date Rptd Parsed"] = date_reported.dt.strftime("%Y-%m-%d %H:%M:%S")
    cleaned["Date OCC Parsed"] = date_occurred.dt.strftime("%Y-%m-%d")
    cleaned["Date OCC Year <= 1900"] = date_occurred.dt.year.le(1900).fillna(False)
    cleaned["Time OCC Valid"] = time_valid.fillna(False)
    cleaned["Time OCC Hour"] = hour.astype("Int64")
    cleaned["Time OCC Midnight"] = time_text.eq("0000")
    cleaned["Coordinates Missing"] = lat.isna() | lon.isna()
    cleaned["Coordinates Double Zero"] = double_zero.fillna(False)
    cleaned["Coordinates Outside Global Range"] = outside_global.fillna(False)
    cleaned["Coordinates Valid For Mapping"] = valid_coordinates.fillna(False)

    in_period = date_occurred >= PERIOD_START
    night = time_valid & ((hour >= 18) | (hour < 6))
    night_without_midnight = night & ~time_text.eq("0000")
    valid_area = cleaned["AREA"].notna()
    cleaned["Analysis Period 2025 Onward"] = (in_period & valid_area).fillna(False)
    cleaned["Nighttime 18-05:59"] = (in_period & valid_area & night).fillna(False)
    cleaned["Nighttime Excluding 0000"] = (in_period & valid_area & night_without_midnight).fillna(False)
    return cleaned


def area_metrics(cleaned: pd.DataFrame, exclude_midnight: bool = False) -> pd.DataFrame:
    period = cleaned[cleaned["Analysis Period 2025 Onward"] & cleaned["Time OCC Valid"]].copy()
    if exclude_midnight:
        period = period[~period["Time OCC Midnight"]]
    night_column = "Nighttime Excluding 0000" if exclude_midnight else "Nighttime 18-05:59"
    rows = []
    for area, group in period.groupby("AREA", dropna=False, sort=True):
        night = group[group[night_column]]
        rows.append({
            "AREA": area,
            "valid_time_offense_records_2025_onward": len(group),
            "nighttime_offense_records": len(night),
            "nighttime_unique_cases": night["CaseNo"].nunique(),
            "nighttime_share_of_valid_time_records": len(night) / len(group) if len(group) else pd.NA,
            "midnight_excluded": exclude_midnight,
        })
    return pd.DataFrame(rows)


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> dict:
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    if input_path == output_path:
        raise ValueError("Output path must differ from the original CSV path")
    input_hash_before = sha256(input_path)
    raw = read_raw(input_path)
    cleaned = clean_dataframe(raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    input_hash_after = sha256(input_path)
    if input_hash_before != input_hash_after:
        raise RuntimeError("The original CSV changed during cleaning")
    metrics = area_metrics(cleaned)
    metrics_no_midnight = area_metrics(cleaned, exclude_midnight=True)
    metrics.to_csv(output_path.parent / "metrics_by_area.csv", index=False)
    metrics_no_midnight.to_csv(output_path.parent / "metrics_by_area_excluding_midnight.csv", index=False)

    metadata = {
        "input": str(input_path),
        "input_sha256_before": input_hash_before,
        "input_sha256_after": input_hash_after,
        "input_sha256_unchanged": input_hash_before == input_hash_after,
        "rows_read": len(raw),
        "columns_read": len(raw.columns),
        "cleaned_rows_written": len(cleaned),
        "cleaned_columns_written": len(cleaned.columns),
        "python": __import__("sys").version,
        "pandas": pd.__version__,
        "analysis_period": ["2025-01-01 inclusive", "all later dates present in the fixed team snapshot"],
        "night_definition": "18:00-05:59",
    }
    (output_path.parent / "cleaning_run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output), indent=2, default=str))


if __name__ == "__main__":
    main()