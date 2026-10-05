"""Reusable cleaning logic for the LAPD NIBRS Offenses dataset (DSO 576, Module 6).

Project: Community Safety Resource Planner: Streetlight Assessment.

The rules implemented here are documented in plan.md. The notebook
"Data Cleaning.ipynb" calls these same functions, and the command line runs
the whole pipeline:

    python clean_nibrs.py --input data/LAPD_NIBRS_Offenses_Dataset_20261004.csv --outdir outputs

Principles:
- The original CSV is only read, never written. Its SHA-256 is checked before
  and after each run.
- Cleaning keeps all rows. Analysis scope and eligibility are recorded as
  columns (in_scope, district_eligible, night, map_eligible).
- Suspicious values are flagged, not corrected. No coordinates, districts,
  weapons or other values are invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (decisions recorded in plan.md, section 16)
# ---------------------------------------------------------------------------
RAW_PATH = Path("data") / "LAPD_NIBRS_Offenses_Dataset_20261004.csv"
EXPECTED_SHA256 = "97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5"
DATE_FORMAT = "%Y %b %d %I:%M:%S %p"

YEAR_2024_START = pd.Timestamp("2024-01-01")
RMS_START = pd.Timestamp("2024-03-07")  # LAPD NIBRS-aligned RMS go-live
SCOPE_START = pd.Timestamp("2025-01-01")  # analysis scope uses Date OCC
IMPLAUSIBLE_BEFORE_YEAR = 1900

# Nighttime: 20:00 inclusive to 06:00 exclusive (fixed-clock approximation).
NIGHT_START_MINUTE = 20 * 60
NIGHT_END_MINUTE = 6 * 60

# Rough City of Los Angeles box, used only as a review flag.
LA_BOX = {"lat_min": 33.70, "lat_max": 34.35, "lon_min": -118.70, "lon_max": -118.15}
# Distance from district median beyond which a point is flagged for review only.
FAR_FROM_DISTRICT_KM = 5.0
KM_PER_DEG_LAT = 111.0
KM_PER_DEG_LON = 111.0 * math.cos(math.radians(34.0))

SAMPLE_SEED = 576
SAMPLE_MAX_ROWS = 50

YES_NO_COLUMNS = [
    "Victim Shot",
    "Domestic Violence Crime",
    "Hate Crime",
    "Gang-related Crime",
    "Transit-related Crime",
    "Homeless-Victim Crime",
    "Homeless-Suspect Crime",
    "Homeless-Arrestee Crime",
]
LEADING_ZERO_COLUMNS = ["AREA", "RPT Dist No", "Premise Cd", "Weapon Used Cd", "Time OCC"]
CASE_LEVEL_COLUMNS = ["Date OCC", "Time OCC", "AREA", "RPT Dist No", "LOCATION", "LAT", "LON"]

# Values measured on the full CSV during planning (plan.md). Validation compares
# the cleaned results against these; a mismatch is reported, never hidden.
PLANNING_EXPECTATIONS = {
    "raw_rows": 489_955,
    "raw_columns": 31,
    "exact_duplicate_rows": 0,
    "distinct_caseno": 440_121,
    "area_name_changed_cells": 489_955,
    "area_name_distinct_after": 21,
    "nibr_desc_changed_cells": 82_058,
    "nibr_desc_distinct_before": 2_409,
    "nibr_desc_distinct_after": 2_398,
    "occ_implausible_year": 3,
    "rpt_before_occ": 523,
    "rpt_before_occ_in_scope": 29,
    "rpt_dist_area_only": 558,
    "rpt_dist_area_only_in_scope": 504,
    "toc_mismatch_rows": 96,
    "toc_mismatch_cases": 80,
    "tvc_conflict_cases": 17,
    "nibr_code_missing": 1_149,
    "nibr_code_missing_in_scope": 72,
    "nibr_desc_code_conflict": 16,
    "location_suspected_generalized": 10_412,
    "location_suspected_generalized_in_scope": 8_217,
    "coord_missing": 131,
    "coord_missing_in_scope": 109,
    "coord_zero": 550,
    "coord_zero_in_scope": 478,
    "coord_nonnumeric": 0,
    "coord_nonfinite": 0,
    "coord_out_of_global_bounds": 0,
    "coord_outside_basic_range": 161,
    "coord_outside_basic_range_in_scope": 120,
    "coord_far_from_district_review": 2_479,
    "coord_far_from_district_review_in_scope": 1_848,
    "map_eligible_in_scope": 379_504,
    # Measured 2026-10-04 (after implementation, before the lookup audit was revised).
    "district_not_map_eligible": 123,
    "lat_lon_na_after": 681,
    "scope_pre_2024": 6_824,
    "scope_2024_pre_rms": 1_351,
    "scope_2024_rms_transition": 101_689,
    "in_scope_rows": 380_091,
    "in_scope_cases": 344_186,
    "district_eligible_in_scope": 379_587,
    "time_0000_in_scope": 10_330,
    "night_incl_0000_in_scope": 137_415,
    "night_excl_0000_in_scope": 127_085,
    "same_code_repeat_in_case_in_scope": 8_380,
    "identical_except_id_in_scope": 1_374,
    "district_month_rows": 21_290,
    "district_month_districts": 1_140,
    "district_month_night_incl_0000": 137_243,
    "district_month_night_excl_0000": 126_919,
    "unassigned_night_incl_0000": 172,
    "unassigned_night_excl_0000": 166,
    "sep_2026_in_scope_rows": 10_097,
    "sep_2026_night_incl_0000": 3_643,
    "sep_2026_night_excl_0000": 3_446,
    "occ_2026_09_19_rows": 8,
}

# Five record checks. Expected results were written in plan.md section 8
# before any transformation was run.
RECORD_CHECKS = [
    {
        "id": "R1",
        "uid": "25088246_290_2",
        "why": "Multi-offense case (3 rows); case-level totals repeated; daytime",
        "expected": {
            "in_scope": True,
            "occ_year_month": "2025-05",
            "RPT Dist No": "0558",
            "AREA NAME": "Harbor",
            "TotalOffenseCount": 3,
            "TotalVictimCount": 5,
            "case_rows_in_file": 3,
            "toc_mismatch": False,
            "Gang-related Crime": True,
            "map_eligible": True,
            "coord_outside_basic_range": False,
            "coord_far_from_district_review": False,
            "location_suspected_generalized": False,
            "district_eligible": True,
            "night": False,
            "counts_in_night_incl_0000": False,
        },
    },
    {
        "id": "R2",
        "uid": "26172245_220_0",
        "why": "Time OCC 0000; month 2026-08; weapon missing",
        "expected": {
            "in_scope": True,
            "occ_year_month": "2026-08",
            "calendar_coverage": "complete",
            "time_is_0000": True,
            "night": True,
            "counts_in_night_incl_0000": True,
            "counts_in_night_excl_0000": False,
            "Weapon Used Cd": None,
            "Weapon Desc": None,
            "report_lag_days": ("approx", 1.85, 0.005),
        },
    },
    {
        "id": "R3",
        "uid": "C259005916_23H_0",
        "why": "Area-only RPT Dist No; (0, 0) coordinates; C-prefixed case",
        "expected": {
            "in_scope": True,
            "RPT Dist No": "10",
            "rpt_dist_area_only": True,
            "district_eligible": False,
            "coord_zero": True,
            "LAT": None,
            "LON": None,
            "map_eligible": False,
            "case_prefix": "C",
            "night": False,
            "counts_in_night_incl_0000": False,
        },
    },
    {
        "id": "R4",
        "uid": "25000271_13B_0",
        "why": "Scope boundary: occurred 2024-12-31 23:55, reported 2025-01-01",
        "expected": {
            "in_scope": False,
            "scope_reason": "2024_rms_transition",
            "night": True,
            "counts_in_night_incl_0000": False,
            "occ_year_month": "2024-12",
        },
    },
    {
        "id": "R5",
        "uid": "26173656_90D_0",
        "why": "Coordinates ~32 km from district median; partial month; 06:45",
        "expected": {
            "in_scope": True,
            "LAT": 34.1244,
            "LON": -117.9063,
            "coord_outside_basic_range": True,
            "coord_far_from_district_review": True,
            "map_eligible": True,
            "district_eligible": True,
            "occ_year_month": "2026-09",
            "calendar_coverage": "partial",
            "night": False,
            "counts_in_night_incl_0000": False,
        },
    },
]

# Source column(s) each record-check field is based on (to show original values).
_FIELD_BASIS = {
    "in_scope": ["Date OCC"],
    "scope_reason": ["Date OCC"],
    "occ_year_month": ["Date OCC"],
    "calendar_coverage": ["Date OCC"],
    "case_rows_in_file": ["CaseNo"],
    "toc_mismatch": ["TotalOffenseCount"],
    "map_eligible": ["LAT", "LON"],
    "coord_outside_basic_range": ["LAT", "LON"],
    "coord_far_from_district_review": ["LAT", "LON", "RPT Dist No"],
    "coord_zero": ["LAT", "LON"],
    "location_suspected_generalized": ["LOCATION", "RPT Dist No"],
    "district_eligible": ["RPT Dist No"],
    "rpt_dist_area_only": ["RPT Dist No"],
    "night": ["Time OCC"],
    "time_is_0000": ["Time OCC"],
    "counts_in_night_incl_0000": ["Date OCC", "Time OCC", "RPT Dist No"],
    "counts_in_night_excl_0000": ["Date OCC", "Time OCC", "RPT Dist No"],
    "report_lag_days": ["Date Rptd", "Date OCC"],
    "case_prefix": ["CaseNo"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _flag(series: pd.Series) -> pd.Series:
    """Nullable comparison result -> plain bool (NA treated as False)."""
    return series.fillna(False).astype(bool)


def _case_distinct_count(df: pd.DataFrame, column: str) -> pd.Series:
    """Number of distinct values (NA counts as a value) of `column` within each CaseNo.

    A many-to-one lookup on CaseNo, built from the same frame. Every key must match.
    """
    pairs = df[["CaseNo", column]].drop_duplicates()
    counts = df["CaseNo"].map(pairs.groupby("CaseNo").size())
    if counts.isna().any():
        raise ValueError(f"CaseNo lookup for {column!r} left unmatched rows")
    return counts


def audited_left_join(left: pd.DataFrame, right: pd.DataFrame, on: str, name: str) -> tuple[pd.DataFrame, dict]:
    """Many-to-one left join with an audit of keys, row counts and unmatched keys."""
    merged = left.merge(right, on=on, how="left", validate="many_to_one", indicator=True)
    unmatched = merged["_merge"] == "left_only"
    audit = {
        "join": name,
        "key": on,
        "expected_relationship": "many-to-one left join (each left row matches at most one right row)",
        "left_rows": len(left),
        "right_rows": len(right),
        "right_duplicate_keys": int(right[on].duplicated().sum()),
        "result_rows": len(merged),
        "extra_rows": len(merged) - len(left),
        "unmatched_left_rows": int(unmatched.sum()),
        "unmatched_left_keys": sorted(merged.loc[unmatched, on].astype(str).unique().tolist()),
        "right_keys_not_in_left": sorted(set(right[on].astype(str)) - set(left[on].astype(str))),
    }
    return merged.drop(columns="_merge"), audit


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
def load_raw(path: Path | str = RAW_PATH) -> pd.DataFrame:
    """Load every column as text so leading zeros are kept.

    read_csv still applies its default missing-value tokens (empty fields,
    "NA", "NULL", ...). check_missing_tokens() reports which raw tokens became NA.
    """
    return pd.read_csv(path, dtype="string")


def check_missing_tokens(path: Path | str, raw: pd.DataFrame) -> dict:
    """Compare default loading with a literal load (no NA conversion)."""
    literal = pd.read_csv(path, dtype="string", keep_default_na=False)
    tokens = {}
    non_missing_identical = True
    for column in raw.columns:
        na = raw[column].isna()
        if na.any():
            counts = literal.loc[na, column].value_counts()
            tokens[column] = {("<empty field>" if k == "" else k): int(v) for k, v in counts.items()}
        if not (literal.loc[~na, column] == raw.loc[~na, column]).all():
            non_missing_identical = False
    only_empty = all(set(t) == {"<empty field>"} for t in tokens.values())
    return {
        "tokens_converted_to_na": tokens,
        "only_empty_fields_became_na": only_empty,
        "non_missing_values_identical_to_literal_text": non_missing_identical,
    }


def standardize_text(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Strip AREA NAME padding and collapse repeated whitespace in NIBR Description.

    No case changes and no category merges beyond whitespace.
    """
    out = df.copy()
    out["AREA NAME"] = df["AREA NAME"].str.strip()
    out["NIBR Description"] = df["NIBR Description"].str.replace(r"\s+", " ", regex=True).str.strip()

    report = {}
    for column in ["AREA NAME", "NIBR Description"]:
        changed = _flag(out[column] != df[column])
        report[column] = {
            "changed_cells": int(changed.sum()),
            "distinct_before": int(df[column].nunique()),
            "distinct_after": int(out[column].nunique()),
            "examples": [
                {"before": b, "after": a}
                for b, a in pd.DataFrame({"b": df.loc[changed, column], "a": out.loc[changed, column]})
                .drop_duplicates()
                .head(5)
                .itertuples(index=False)
            ],
        }
    pairs = pd.DataFrame({"before": df["NIBR Description"], "after": out["NIBR Description"]}).drop_duplicates()
    merged = pairs[pairs.groupby("after")["before"].transform("size") > 1].sort_values(["after", "before"])
    report["NIBR Description"]["merged_values"] = {
        after: list(group["before"]) for after, group in merged.groupby("after", sort=True)
    }
    report["leading_zero_lengths_unchanged"] = {
        c: bool(_flag(out[c].str.len() == df[c].str.len()).where(df[c].notna(), True).all())
        for c in LEADING_ZERO_COLUMNS
    }
    return out, report


def convert_types(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Convert dates, counts, coordinates and Yes/No flags. Count failed conversions."""
    out = df.copy()
    failed = {}

    for column in ["Date Rptd", "Date OCC"]:
        converted = pd.to_datetime(df[column], format=DATE_FORMAT, errors="coerce")
        failed[column] = int((df[column].notna() & converted.isna()).sum())
        out[column] = converted

    for column in ["TotalOffenseCount", "TotalVictimCount"]:
        converted = pd.to_numeric(df[column], errors="coerce")
        failed[column] = int((df[column].notna() & converted.isna()).sum())
        out[column] = converted.astype("Int64")

    for column in ["LAT", "LON"]:
        converted = pd.to_numeric(df[column], errors="coerce").astype("Float64")
        failed[column] = int((df[column].notna() & converted.isna()).sum())
        out[column] = converted
    out["coord_nonnumeric"] = (df["LAT"].notna() & out["LAT"].isna()) | (df["LON"].notna() & out["LON"].isna())

    yes_no = {}
    for column in YES_NO_COLUMNS:
        unexpected = sorted(set(df[column].dropna().unique()) - {"Yes", "No"})
        out[column] = df[column].map({"Yes": True, "No": False}).astype("boolean")
        failed[column] = int((df[column].notna() & out[column].isna()).sum())
        yes_no[column] = {
            "yes_before": int((df[column] == "Yes").sum()),
            "true_after": int(out[column].sum()),
            "unexpected_values": unexpected,
        }
    return out, {"failed_conversions": failed, "yes_no": yes_no}


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add record-level and case-level quality flags. No values are changed."""
    out = df.copy()
    out["case_prefix"] = df["CaseNo"].str.extract(r"^([A-Za-z]*)", expand=False).replace("", "numeric")

    lag_days = (df["Date Rptd"] - df["Date OCC"]).dt.total_seconds() / 86400
    out["report_lag_days"] = lag_days.round(4).astype("Float64")
    out["rpt_before_occ"] = _flag(df["Date Rptd"] < df["Date OCC"])
    out["occ_implausible_year"] = _flag(df["Date OCC"].dt.year < IMPLAUSIBLE_BEFORE_YEAR)

    out["rpt_dist_area_only"] = _flag(df["RPT Dist No"].str.fullmatch(r"\d{2}"))
    out["district_eligible"] = _flag(df["RPT Dist No"].str.fullmatch(r"\d{4}"))

    rows_per_case = df.groupby("CaseNo")["CaseNo"].transform("size")
    out["case_rows_in_file"] = rows_per_case.astype("Int64")
    out["toc_mismatch"] = _flag(df["TotalOffenseCount"] != rows_per_case)
    out["tvc_conflict"] = _case_distinct_count(df, "TotalVictimCount") > 1

    out["nibr_code_missing"] = df["NIBR Code"].isna()
    desc_code = df["NIBR Description"].str.extract(r"- ([0-9A-Z]{3})$", expand=False)
    out["nibr_desc_code_conflict"] = _flag(desc_code.notna() & df["NIBR Code"].notna() & (desc_code != df["NIBR Code"]))
    out["same_code_repeat_in_case"] = df.duplicated(["CaseNo", "NIBR Code"], keep=False) & df["NIBR Code"].notna()

    inconsistent = pd.Series(False, index=df.index)
    for column in CASE_LEVEL_COLUMNS:
        inconsistent |= _case_distinct_count(df, column) > 1
    out["case_field_inconsistent"] = inconsistent

    out["location_suspected_generalized"] = _flag(df["LOCATION"] == df["RPT Dist No"])
    return out


def add_time_fields(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Derive occurrence date, year-month, minute of day, 0000/1200 flags and night."""
    out = df.copy()
    time_text = df["Time OCC"]
    valid = _flag(time_text.str.fullmatch(r"([01]\d|2[0-3])[0-5]\d"))
    minute = (time_text.str.slice(0, 2).astype("Int64") * 60 + time_text.str.slice(2, 4).astype("Int64")).where(valid)

    out["occ_date"] = df["Date OCC"].dt.normalize()
    out["occ_year_month"] = df["Date OCC"].dt.strftime("%Y-%m")
    out["occ_minute_of_day"] = minute.astype("Int64")
    out["time_is_0000"] = _flag(time_text == "0000")
    out["time_is_1200"] = _flag(time_text == "1200")
    out["time_conflict"] = _flag(df["Date OCC"].dt.strftime("%H%M") != time_text)
    out["night"] = _flag((minute >= NIGHT_START_MINUTE) | (minute < NIGHT_END_MINUTE))

    report = {
        "invalid_hhmm": int((~valid).sum()),
        "time_matches_date_occ": int((~out["time_conflict"]).sum()),
        "minute_min": int(minute.min()),
        "minute_max": int(minute.max()),
    }
    return out, report


def add_coordinate_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Separate coordinate flags. (0, 0) becomes NA; nothing is replaced or moved."""
    out = df.copy()
    lat = df["LAT"].to_numpy(dtype="float64", na_value=np.nan)
    lon = df["LON"].to_numpy(dtype="float64", na_value=np.nan)
    nonnumeric = df["coord_nonnumeric"].to_numpy()

    present = ~np.isnan(lat) & ~np.isnan(lon)
    missing = ~present & ~nonnumeric
    finite = np.isfinite(lat) & np.isfinite(lon)
    in_global = (lat >= -90) & (lat <= 90) & (lon >= -180) & (lon <= 180)
    zero = present & (lat == 0) & (lon == 0)
    map_eligible = present & finite & in_global & ~zero

    in_box = (
        (lat >= LA_BOX["lat_min"]) & (lat <= LA_BOX["lat_max"])
        & (lon >= LA_BOX["lon_min"]) & (lon <= LA_BOX["lon_max"])
    )

    # Median point of each district, from mappable street-address rows only.
    reference = map_eligible & df["district_eligible"].to_numpy() & ~df["location_suspected_generalized"].to_numpy()
    medians = (
        pd.DataFrame({"lat": lat, "lon": lon, "district": df["RPT Dist No"].to_numpy()})[reference]
        .groupby("district")[["lat", "lon"]]
        .median()
    )
    lat_med = df["RPT Dist No"].map(medians["lat"]).to_numpy(dtype="float64", na_value=np.nan)
    lon_med = df["RPT Dist No"].map(medians["lon"]).to_numpy(dtype="float64", na_value=np.nan)
    distance = np.hypot((lat - lat_med) * KM_PER_DEG_LAT, (lon - lon_med) * KM_PER_DEG_LON)
    distance = np.where(map_eligible & df["district_eligible"].to_numpy(), distance, np.nan)

    out["coord_missing"] = missing
    out["coord_nonfinite"] = present & ~finite
    out["coord_out_of_global_bounds"] = present & finite & ~in_global
    out["coord_zero"] = zero
    out["map_eligible"] = map_eligible
    out["coord_outside_basic_range"] = map_eligible & ~in_box
    out["dist_km_from_district_median"] = pd.Series(np.round(distance, 3), index=df.index).astype("Float64")
    # False means "not flagged". Where the distance is missing the row was not
    # assessed, so False does not mean the point is close to its district.
    out["coord_far_from_district_review"] = np.nan_to_num(distance, nan=0.0) > FAR_FROM_DISTRICT_KM
    out["LAT"] = df["LAT"].mask(zero)
    out["LON"] = df["LON"].mask(zero)
    return out


def apply_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Label analysis scope (Date OCC >= 2025-01-01) and calendar coverage. No rows removed."""
    out = df.copy()
    occ = df["Date OCC"]
    out["scope_reason"] = pd.Series(
        np.select(
            [occ < YEAR_2024_START, occ < RMS_START, occ < SCOPE_START],
            ["pre_2024", "2024_pre_rms", "2024_rms_transition"],
            default="in_scope",
        ),
        index=df.index,
        dtype="string",
    )
    out["in_scope"] = _flag(occ >= SCOPE_START)

    # A month is calendar-partial only if the data ends before the month does.
    last_occ = occ.max().normalize()
    last_month = last_occ.strftime("%Y-%m")
    last_month_is_partial = last_occ < (last_occ + pd.offsets.MonthEnd(0))
    coverage = pd.Series("complete", index=df.index, dtype="string")
    if last_month_is_partial:
        coverage = coverage.mask(df["occ_year_month"] == last_month, "partial")
    out["calendar_coverage"] = coverage.where(out["in_scope"])
    return out


def _summarize_night(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    grouped = frame.groupby(keys, sort=True)
    summary = grouped.agg(
        night_offenses_incl_0000=("UniqueNIBRNo", "size"),
        night_offenses_0000=("time_is_0000", "sum"),
        night_distinct_cases_incl_0000=("CaseNo", "nunique"),
    )
    summary["night_offenses_excl_0000"] = summary["night_offenses_incl_0000"] - summary["night_offenses_0000"]
    excl_cases = frame[~frame["time_is_0000"]].groupby(keys, sort=True)["CaseNo"].nunique()
    summary["night_distinct_cases_excl_0000"] = excl_cases.reindex(summary.index, fill_value=0)
    return summary.reset_index()


def month_context(df: pd.DataFrame) -> pd.DataFrame:
    """Per in-scope month: calendar coverage and days from month end to the last report date."""
    in_scope = df[df["in_scope"]]
    last_report = df["Date Rptd"].max().normalize()
    months = in_scope.groupby("occ_year_month", sort=True)["calendar_coverage"].first().reset_index()
    month_end = pd.to_datetime(months["occ_year_month"] + "-01") + pd.offsets.MonthEnd(0)
    days = (last_report - month_end).dt.days.astype("Int64")
    months["days_since_month_end_to_last_report"] = days.where(months["calendar_coverage"] == "complete")
    return months


def build_district_month(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Observed (district, month) combinations of in-scope night offenses, plus unassigned rows.

    Month context is attached with audited many-to-one joins on occ_year_month.
    """
    night = df[df["in_scope"] & df["night"]]
    assigned = night[night["district_eligible"]]
    unassigned = night[~night["district_eligible"]]

    areas_per_district = assigned.groupby("RPT Dist No")[["AREA", "AREA NAME"]].nunique()
    if (areas_per_district > 1).any().any():
        raise ValueError("A reporting district maps to more than one AREA")

    context = month_context(df)
    columns = [
        "calendar_coverage",
        "days_since_month_end_to_last_report",
        "night_offenses_incl_0000",
        "night_offenses_excl_0000",
        "night_offenses_0000",
        "night_distinct_cases_incl_0000",
        "night_distinct_cases_excl_0000",
    ]
    district_month = _summarize_night(assigned, ["RPT Dist No", "AREA", "AREA NAME", "occ_year_month"])
    district_month, audit_dm = audited_left_join(
        district_month, context, "occ_year_month", "district-month night counts <- month context"
    )
    district_month = district_month[["RPT Dist No", "AREA", "AREA NAME", "occ_year_month"] + columns]

    unassigned_month = _summarize_night(unassigned, ["AREA", "AREA NAME", "occ_year_month"])
    unassigned_month, audit_un = audited_left_join(
        unassigned_month, context, "occ_year_month", "unassigned-district night counts <- month context"
    )
    unassigned_month = unassigned_month[["AREA", "AREA NAME", "occ_year_month"] + columns]
    return district_month, unassigned_month, [audit_dm, audit_un]


def build_month_summary(df: pd.DataFrame, context: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per in-scope month: all offenses, night counts with/without 0000, plus month context."""
    in_scope = df[df["in_scope"]]
    month = (
        in_scope.groupby("occ_year_month", sort=True)
        .agg(
            in_scope_offenses=("UniqueNIBRNo", "size"),
            night_incl_0000=("night", "sum"),
            time_0000=("time_is_0000", "sum"),
        )
        .reset_index()
    )
    excl = in_scope[in_scope["night"] & ~in_scope["time_is_0000"]].groupby("occ_year_month").size()
    month["night_excl_0000"] = excl.reindex(month["occ_year_month"]).fillna(0).astype(int).values
    return audited_left_join(month, context, "occ_year_month", "in-scope month summary <- month context")


def audit_lookups(df: pd.DataFrame) -> list[dict]:
    """Audit the two many-to-one lookups used while flagging (not table merges, but joins in effect)."""
    group_size = df.groupby("CaseNo")["CaseNo"].transform("size")
    case_audit = {
        "join": "rows -> per-CaseNo counts (case_rows_in_file, tvc_conflict, case_field_inconsistent)",
        "key": "CaseNo",
        "expected_relationship": "many-to-one lookup built from the same rows; every key must match",
        "left_rows": len(df),
        "right_rows": int(df["CaseNo"].nunique()),
        "result_rows": len(df),
        "extra_rows": 0,
        "unmatched_left_rows": int(df["case_rows_in_file"].isna().sum()),
        "values_consistent_with_recount": bool((df["case_rows_in_file"] == group_size).all()),
    }
    # Only map-eligible rows with a 4-digit district are looked up. Other rows are
    # reported separately; their distance stays missing (no median is filled in).
    distance = df["dist_km_from_district_median"]
    far = df["coord_far_from_district_review"]
    eligible = df["map_eligible"] & df["district_eligible"]
    reference = eligible & ~df["location_suspected_generalized"]
    reference_districts = set(df.loc[reference, "RPT Dist No"])
    unmatched = eligible & ~df["RPT Dist No"].isin(reference_districts)
    area_only = ~eligible & df["rpt_dist_area_only"]
    other = ~eligible & ~df["rpt_dist_area_only"]

    def not_looked_up(mask: pd.Series, description: str) -> dict:
        return {
            "description": description,
            "rows": int(mask.sum()),
            "rows_in_scope": int((mask & df["in_scope"]).sum()),
            "distance_missing": int(distance[mask].isna().sum()),
            "far_flag_true": int(far[mask].sum()),
        }

    median_audit = {
        "join": "rows -> district median point (coord_far_from_district_review)",
        "key": "RPT Dist No",
        "expected_relationship": (
            "many-to-one lookup for map-eligible rows with a 4-digit district; "
            "districts without street-address reference rows would have no median"
        ),
        "left_rows": int(eligible.sum()),
        "right_rows": len(reference_districts),
        "result_rows": int((eligible & distance.notna()).sum()),
        "extra_rows": int((eligible & distance.notna()).sum() - eligible.sum()),
        "unmatched_left_rows": int(unmatched.sum()),
        "unmatched_left_keys": sorted(df.loc[unmatched, "RPT Dist No"].unique().tolist()),
        "not_looked_up": {
            "area_only_rpt_dist_no": not_looked_up(area_only, "RPT Dist No holds only the 2-digit area code"),
            "other_not_mappable": not_looked_up(
                other, "4-digit district but coordinates missing, (0, 0) or otherwise not map-eligible"
            ),
        },
        "reconciliation": {
            "looked_up": int(eligible.sum()),
            "area_only_not_looked_up": int(area_only.sum()),
            "other_not_looked_up": int(other.sum()),
            "sum": int(eligible.sum() + area_only.sum() + other.sum()),
            "all_rows": len(df),
        },
        "interpretation": (
            "coord_far_from_district_review = False means 'not flagged'. Rows without a distance were not "
            "assessed; False does not establish that their coordinates are close to the district median."
        ),
    }
    return [case_audit, median_audit]


def select_sample(df: pd.DataFrame, seed: int = SAMPLE_SEED) -> pd.DataFrame:
    """Deterministic sample of up to 50 cleaned rows, emphasising difficult cases."""
    chosen: list[int] = []
    reasons: list[str] = []

    def take(mask: pd.Series, n: int, reason: str) -> None:
        pool = df[mask & ~df.index.isin(chosen)]
        if pool.empty or len(chosen) >= SAMPLE_MAX_ROWS:
            return
        picked = pool.sample(n=min(n, len(pool), SAMPLE_MAX_ROWS - len(chosen)), random_state=seed)
        for index in picked.index.sort_values():
            chosen.append(index)
            reasons.append(reason)

    uid = df["UniqueNIBRNo"]
    for check in RECORD_CHECKS:
        take(uid == check["uid"], 1, f"record check {check['id']}: {check['why']}")
    take(df["CaseNo"] == "25088246", 2, "same case as R1 (multi-offense case)")

    ins = df["in_scope"]
    time = df["Time OCC"]
    weapon = df["Weapon Used Cd"]
    categories = [
        (ins & df["time_is_0000"], 2, "Time OCC 0000 (night window)"),
        (ins & df["time_is_1200"], 1, "Time OCC 1200 (heaped value)"),
        (ins & (time == "1959"), 1, "night boundary: 1959 (not night)"),
        (ins & (time == "2000"), 1, "night boundary: 2000 (night)"),
        (ins & (time == "0559"), 1, "night boundary: 0559 (night)"),
        (ins & (time == "0600"), 1, "night boundary: 0600 (not night)"),
        (df["occ_date"] == pd.Timestamp("2026-09-19"), 1, "observed record on last occurrence date 2026-09-19"),
        (ins & df["rpt_before_occ"], 1, "Date Rptd earlier than Date OCC"),
        (ins & df["Date Rptd"].isna(), 1, "Date Rptd missing"),
        (ins & df["rpt_dist_area_only"], 2, "RPT Dist No holds only the area code"),
        (ins & df["coord_missing"], 2, "coordinates missing"),
        (ins & df["coord_zero"], 1, "coordinates (0, 0)"),
        (ins & df["coord_outside_basic_range"], 1, "outside rough LA box (review flag)"),
        (ins & df["coord_far_from_district_review"] & ~df["coord_outside_basic_range"], 2,
         "over 5 km from district median, inside LA box (review flag)"),
        (ins & df["location_suspected_generalized"], 2, "LOCATION equals RPT Dist No (suspected generalized)"),
        (ins & df["nibr_code_missing"], 2, "NIBR Code missing"),
        (df["nibr_desc_code_conflict"], 1, "description code differs from NIBR Code"),
        (ins & df["toc_mismatch"], 2, "TotalOffenseCount differs from rows in file"),
        (ins & df["tvc_conflict"], 2, "TotalVictimCount conflicts within case"),
        (ins & df["same_code_repeat_in_case"], 2, "same NIBR Code repeated within case"),
        (ins & weapon.isna(), 1, "weapon missing (not 'no weapon')"),
        (ins & _flag(weapon.str.contains(",")), 1, "multiple weapon codes"),
        (ins & _flag(weapon == "00"), 1, "weapon code 00 (Unknown)"),
        (df["occ_implausible_year"], 1, "out of scope: occurrence year before 1900"),
        ((df["scope_reason"] == "pre_2024") & ~df["occ_implausible_year"], 1, "out of scope: pre_2024"),
        (df["scope_reason"] == "2024_pre_rms", 1, "out of scope: 2024_pre_rms"),
        (df["scope_reason"] == "2024_rms_transition", 1, "out of scope: 2024_rms_transition"),
    ]
    for mask, n, reason in categories:
        take(mask, n, reason)

    flag_columns = [
        "time_is_0000", "time_is_1200", "time_conflict", "rpt_before_occ", "rpt_dist_area_only",
        "toc_mismatch", "tvc_conflict", "nibr_code_missing", "nibr_desc_code_conflict",
        "same_code_repeat_in_case", "case_field_inconsistent", "location_suspected_generalized",
        "coord_outside_basic_range", "coord_far_from_district_review",
    ]
    typical = ins & df["map_eligible"] & df["district_eligible"] & ~df[flag_columns].any(axis=1) & df["Date Rptd"].notna()
    take(typical, SAMPLE_MAX_ROWS - len(chosen), "typical in-scope row with no flags")

    sample = df.loc[chosen].copy()
    sample.insert(0, "sample_reason", reasons)
    sample.insert(0, "sample_order", range(1, len(sample) + 1))
    return sample.reset_index(names="source_row_index")


def _matches(expected, actual) -> bool:
    if expected is None:
        return bool(pd.isna(actual))
    if pd.isna(actual):
        return False
    if isinstance(expected, tuple) and expected[0] == "approx":
        return abs(float(actual) - expected[1]) <= expected[2]
    if isinstance(expected, float):
        return abs(float(actual) - expected) < 1e-9
    if isinstance(expected, bool):
        return bool(actual) is expected
    return actual == expected


def _show(value) -> str:
    if isinstance(value, tuple) and value[0] == "approx":
        return f"≈{value[1]}"
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return "NA"
    return str(value)


def check_records(raw: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    """Compare the five record checks (expectations fixed in advance) with actual results."""
    rows = []
    for check in RECORD_CHECKS:
        raw_row = raw.loc[raw["UniqueNIBRNo"] == check["uid"]].iloc[0]
        row = clean.loc[clean["UniqueNIBRNo"] == check["uid"]].iloc[0]
        derived = {
            "counts_in_night_incl_0000": bool(row["in_scope"] and row["night"] and row["district_eligible"]),
            "counts_in_night_excl_0000": bool(
                row["in_scope"] and row["night"] and row["district_eligible"] and not row["time_is_0000"]
            ),
        }
        for field, expected in check["expected"].items():
            actual = derived[field] if field in derived else row[field]
            basis = _FIELD_BASIS.get(field, [field])
            original = "; ".join(f"{c}={raw_row[c]!r}" if pd.notna(raw_row[c]) else f"{c}=NA" for c in basis)
            rows.append(
                {
                    "record": check["id"],
                    "UniqueNIBRNo": check["uid"],
                    "field": field,
                    "original": original,
                    "expected": _show(expected),
                    "actual": _show(actual if not isinstance(actual, (np.floating, float)) else round(float(actual), 4)),
                    "match": _matches(expected, actual),
                }
            )
    return pd.DataFrame(rows)


def independent_recount(raw: pd.DataFrame, district_month: pd.DataFrame, seed: int = SAMPLE_SEED) -> list[dict]:
    """Recount 3 district-month cells directly from raw text, without the cleaning code."""
    results = []
    for cell in district_month.sample(n=3, random_state=seed).itertuples(index=False):
        district, month = cell[0], cell[3]
        prefix = pd.Timestamp(month + "-01").strftime("%Y %b ")
        time = raw["Time OCC"]
        mask = (
            (raw["RPT Dist No"] == district)
            & raw["Date OCC"].str.startswith(prefix)
            & ((time >= "2000") | (time < "0600"))
        ).fillna(False)
        incl = int(mask.sum())
        excl = int((mask & (time != "0000")).sum())
        results.append(
            {
                "RPT Dist No": district,
                "occ_year_month": month,
                "raw_recount_incl_0000": incl,
                "table_incl_0000": int(cell.night_offenses_incl_0000),
                "raw_recount_excl_0000": excl,
                "table_excl_0000": int(cell.night_offenses_excl_0000),
                "match": incl == int(cell.night_offenses_incl_0000) and excl == int(cell.night_offenses_excl_0000),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate(results: dict) -> list[dict]:
    """Automated checks. Expected values come from planning; failures are reported, not hidden."""
    raw, clean = results["raw"], results["clean"]
    dm, un = results["district_month"], results["unassigned_month"]
    exp = PLANNING_EXPECTATIONS
    ins = clean["in_scope"]
    checks: list[dict] = []

    def add(name, expected, actual, note=""):
        checks.append({"check": name, "expected": expected, "actual": actual, "passed": expected == actual, "note": note})

    add("raw CSV SHA-256 before run", EXPECTED_SHA256, results["sha256_before"])
    add("raw CSV SHA-256 after run (file unchanged)", EXPECTED_SHA256, results["sha256_after"])
    add("raw rows", exp["raw_rows"], len(raw))
    add("raw columns", exp["raw_columns"], raw.shape[1])
    add("only empty fields became NA on load", True, results["missing_tokens"]["only_empty_fields_became_na"])
    add("non-missing values identical to literal text", True,
        results["missing_tokens"]["non_missing_values_identical_to_literal_text"])
    add("exact duplicate rows", exp["exact_duplicate_rows"], int(raw.duplicated().sum()))
    add("UniqueNIBRNo unique in cleaned data", True, bool(clean["UniqueNIBRNo"].is_unique))
    add("cleaned rows = raw rows (no rows removed by cleaning)", len(raw), len(clean))
    add("distinct CaseNo", exp["distinct_caseno"], int(clean["CaseNo"].nunique()))

    text = results["text_report"]
    add("AREA NAME changed cells", exp["area_name_changed_cells"], text["AREA NAME"]["changed_cells"])
    add("AREA NAME distinct after", exp["area_name_distinct_after"], text["AREA NAME"]["distinct_after"])
    add("NIBR Description changed cells", exp["nibr_desc_changed_cells"], text["NIBR Description"]["changed_cells"])
    add("NIBR Description distinct before", exp["nibr_desc_distinct_before"], text["NIBR Description"]["distinct_before"])
    add("NIBR Description distinct after", exp["nibr_desc_distinct_after"], text["NIBR Description"]["distinct_after"])
    add("leading-zero columns keep their lengths", True, all(text["leading_zero_lengths_unchanged"].values()))
    add("AREA -> AREA NAME one-to-one after cleaning", True,
        bool((clean.groupby("AREA")["AREA NAME"].nunique() == 1).all() and clean["AREA NAME"].nunique() == 21))

    types = results["type_report"]
    add("failed type conversions (all columns)", 0, sum(types["failed_conversions"].values()))
    add("Yes/No columns: True count = original Yes count", True,
        all(v["yes_before"] == v["true_after"] and not v["unexpected_values"] for v in types["yes_no"].values()))
    na_before = raw.isna().sum()
    na_after = clean[raw.columns].isna().sum()
    unchanged = [c for c in raw.columns if c not in ("LAT", "LON")]
    add("NA counts unchanged except LAT/LON", True, bool((na_before[unchanged] == na_after[unchanged]).all()))
    add("LAT NA after cleaning (131 missing + 550 zero)", exp["lat_lon_na_after"], int(na_after["LAT"]))
    add("LON NA after cleaning (131 missing + 550 zero)", exp["lat_lon_na_after"], int(na_after["LON"]))

    timing = results["time_report"]
    add("Time OCC invalid HHMM", 0, timing["invalid_hhmm"])
    add("Time OCC equals Date OCC HH:MM", exp["raw_rows"], timing["time_matches_date_occ"])
    add("minute of day within 0-1439", True, timing["minute_min"] >= 0 and timing["minute_max"] <= 1439)

    def count(col, scope=False):
        return int((clean[col] & ins).sum()) if scope else int(clean[col].sum())

    add("occ_implausible_year", exp["occ_implausible_year"], count("occ_implausible_year"))
    add("rpt_before_occ", exp["rpt_before_occ"], count("rpt_before_occ"))
    add("rpt_before_occ (in scope)", exp["rpt_before_occ_in_scope"], count("rpt_before_occ", True))
    add("rpt_dist_area_only", exp["rpt_dist_area_only"], count("rpt_dist_area_only"))
    add("rpt_dist_area_only (in scope)", exp["rpt_dist_area_only_in_scope"], count("rpt_dist_area_only", True))
    add("toc_mismatch rows", exp["toc_mismatch_rows"], count("toc_mismatch"))
    add("toc_mismatch cases", exp["toc_mismatch_cases"], int(clean.loc[clean["toc_mismatch"], "CaseNo"].nunique()))
    add("tvc_conflict cases", exp["tvc_conflict_cases"], int(clean.loc[clean["tvc_conflict"], "CaseNo"].nunique()))
    add("nibr_code_missing", exp["nibr_code_missing"], count("nibr_code_missing"))
    add("nibr_code_missing (in scope)", exp["nibr_code_missing_in_scope"], count("nibr_code_missing", True))
    add("nibr_desc_code_conflict", exp["nibr_desc_code_conflict"], count("nibr_desc_code_conflict"))
    add("location_suspected_generalized", exp["location_suspected_generalized"], count("location_suspected_generalized"))
    add("location_suspected_generalized (in scope)", exp["location_suspected_generalized_in_scope"],
        count("location_suspected_generalized", True))
    add("same_code_repeat_in_case (in scope)", exp["same_code_repeat_in_case_in_scope"], count("same_code_repeat_in_case", True))
    identical = raw.duplicated(subset=[c for c in raw.columns if c != "UniqueNIBRNo"], keep=False)
    add("rows identical except UniqueNIBRNo (in scope, kept)", exp["identical_except_id_in_scope"], int((identical & ins).sum()))

    add("coord_missing", exp["coord_missing"], count("coord_missing"))
    add("coord_missing (in scope)", exp["coord_missing_in_scope"], count("coord_missing", True))
    add("coord_zero", exp["coord_zero"], count("coord_zero"))
    add("coord_zero (in scope)", exp["coord_zero_in_scope"], count("coord_zero", True))
    add("coord_nonnumeric", exp["coord_nonnumeric"], count("coord_nonnumeric"))
    add("coord_nonfinite", exp["coord_nonfinite"], count("coord_nonfinite"))
    add("coord_out_of_global_bounds", exp["coord_out_of_global_bounds"], count("coord_out_of_global_bounds"))
    add("coord_outside_basic_range (review)", exp["coord_outside_basic_range"], count("coord_outside_basic_range"))
    add("coord_outside_basic_range (review, in scope)", exp["coord_outside_basic_range_in_scope"],
        count("coord_outside_basic_range", True))
    add("coord_far_from_district_review", exp["coord_far_from_district_review"], count("coord_far_from_district_review"))
    add("coord_far_from_district_review (in scope)", exp["coord_far_from_district_review_in_scope"],
        count("coord_far_from_district_review", True))
    add("map_eligible (in scope)", exp["map_eligible_in_scope"], count("map_eligible", True))
    eligible = clean["map_eligible"]
    lat_e, lon_e = clean.loc[eligible, "LAT"], clean.loc[eligible, "LON"]
    raw_lat_e = pd.to_numeric(raw.loc[eligible, "LAT"], errors="coerce")
    raw_lon_e = pd.to_numeric(raw.loc[eligible, "LON"], errors="coerce")
    add("map_eligible rows: coordinates present (no NA)", True, bool(lat_e.notna().all() and lon_e.notna().all()))
    add("map_eligible rows: finite and within global bounds", True,
        bool(np.isfinite(lat_e.to_numpy(dtype="float64")).all() and np.isfinite(lon_e.to_numpy(dtype="float64")).all()
             and lat_e.between(-90, 90).all() and lon_e.between(-180, 180).all()))
    add("map_eligible rows: no (0, 0) pair in cleaned values", 0, int(((lat_e == 0) & (lon_e == 0)).sum()))
    add("map_eligible rows: no (0, 0) pair in original values", 0, int(((raw_lat_e == 0) & (raw_lon_e == 0)).sum()))
    add("map_eligible rows: none flagged missing/zero/nonnumeric/nonfinite/out of bounds", 0, int(
        clean.loc[eligible, ["coord_missing", "coord_zero", "coord_nonnumeric", "coord_nonfinite",
                             "coord_out_of_global_bounds"]].any(axis=1).sum()))

    reasons = clean["scope_reason"].value_counts()
    add("scope: pre_2024", exp["scope_pre_2024"], int(reasons.get("pre_2024", 0)))
    add("scope: 2024_pre_rms", exp["scope_2024_pre_rms"], int(reasons.get("2024_pre_rms", 0)))
    add("scope: 2024_rms_transition", exp["scope_2024_rms_transition"], int(reasons.get("2024_rms_transition", 0)))
    add("scope: in scope rows", exp["in_scope_rows"], int(ins.sum()))
    add("scope: in-scope + out-of-scope = all rows", exp["raw_rows"], int(ins.sum() + (~ins).sum()))
    add("scope: in-scope distinct cases", exp["in_scope_cases"], int(clean.loc[ins, "CaseNo"].nunique()))
    add("district_eligible (in scope)", exp["district_eligible_in_scope"], count("district_eligible", True))

    night = clean["night"] & ins
    zero = clean["time_is_0000"] & ins
    add("Time OCC 0000 (in scope)", exp["time_0000_in_scope"], int(zero.sum()))
    add("night incl. 0000 (in scope)", exp["night_incl_0000_in_scope"], int(night.sum()))
    add("night excl. 0000 (in scope)", exp["night_excl_0000_in_scope"], int((night & ~clean["time_is_0000"]).sum()))

    add("district-month rows (observed combinations)", exp["district_month_rows"], len(dm))
    add("district-month distinct districts", exp["district_month_districts"], int(dm["RPT Dist No"].nunique()))
    add("district-month night incl. 0000 total", exp["district_month_night_incl_0000"], int(dm["night_offenses_incl_0000"].sum()))
    add("district-month night excl. 0000 total", exp["district_month_night_excl_0000"], int(dm["night_offenses_excl_0000"].sum()))
    add("unassigned night incl. 0000", exp["unassigned_night_incl_0000"], int(un["night_offenses_incl_0000"].sum()))
    add("unassigned night excl. 0000", exp["unassigned_night_excl_0000"], int(un["night_offenses_excl_0000"].sum()))
    add("reconcile incl.: district-month + unassigned = in-scope night", int(night.sum()),
        int(dm["night_offenses_incl_0000"].sum() + un["night_offenses_incl_0000"].sum()))
    add("reconcile excl.: district-month + unassigned = in-scope night excl. 0000",
        int((night & ~clean["time_is_0000"]).sum()),
        int(dm["night_offenses_excl_0000"].sum() + un["night_offenses_excl_0000"].sum()))
    add("no zero-count rows in observed district-month table", 0, int((dm["night_offenses_incl_0000"] == 0).sum()))
    add("independent raw recount of 3 cells matches", True, all(r["match"] for r in results["recount"]))

    sep = ins & (clean["occ_year_month"] == "2026-09")
    add("2026-09 in-scope rows kept", exp["sep_2026_in_scope_rows"], int(sep.sum()))
    add("2026-09 night incl. 0000", exp["sep_2026_night_incl_0000"], int((sep & clean["night"]).sum()))
    add("2026-09 night excl. 0000", exp["sep_2026_night_excl_0000"], int((sep & clean["night"] & ~clean["time_is_0000"]).sum()))
    add("2026-09-19 records kept", exp["occ_2026_09_19_rows"], int((clean["occ_date"] == pd.Timestamp("2026-09-19")).sum()))
    add("only 2026-09 labeled partial", ["2026-09"],
        sorted(clean.loc[clean["calendar_coverage"] == "partial", "occ_year_month"].unique().tolist()))

    for audit in results["join_audits"]:
        name = audit["join"]
        add(f"join [{name}]: result rows = left rows (no extra rows)", audit["left_rows"], audit["result_rows"])
        add(f"join [{name}]: unmatched left rows", 0, audit["unmatched_left_rows"])
        add(f"join [{name}]: duplicate keys on right side", 0, audit["right_duplicate_keys"])
    case_lookup, median_lookup = results["lookup_audits"]
    add("lookup [CaseNo counts]: unmatched rows", 0, case_lookup["unmatched_left_rows"])
    add("lookup [CaseNo counts]: values equal an independent recount", True, case_lookup["values_consistent_with_recount"])
    skipped = median_lookup["not_looked_up"]
    recon = median_lookup["reconciliation"]
    not_looked_up_rows = skipped["area_only_rpt_dist_no"]["rows"] + skipped["other_not_mappable"]["rows"]
    add("lookup [district median]: eligible rows before = eligible rows with a distance after",
        median_lookup["left_rows"], median_lookup["result_rows"],
        "eligible = map-eligible and 4-digit district")
    add("lookup [district median]: unmatched among eligible rows", 0, median_lookup["unmatched_left_rows"])
    add("lookup [district median]: area-only rows not looked up", exp["rpt_dist_area_only"],
        skipped["area_only_rpt_dist_no"]["rows"])
    add("lookup [district median]: other non-mappable rows not looked up", exp["district_not_map_eligible"],
        skipped["other_not_mappable"]["rows"])
    add("lookup [district median]: rows not looked up with missing distance", not_looked_up_rows,
        skipped["area_only_rpt_dist_no"]["distance_missing"] + skipped["other_not_mappable"]["distance_missing"])
    add("lookup [district median]: rows not looked up with far flag True", 0,
        skipped["area_only_rpt_dist_no"]["far_flag_true"] + skipped["other_not_mappable"]["far_flag_true"],
        "False here means not assessed, not close to the district median")
    add("lookup [district median]: looked up + area-only + other = all rows", recon["all_rows"], recon["sum"])

    sample = results["sample"]
    add("sample rows <= 50", True, len(sample) <= SAMPLE_MAX_ROWS)
    add("sample UniqueNIBRNo unique", True, bool(sample["UniqueNIBRNo"].is_unique))
    add("sample includes R1-R5", True, set(c["uid"] for c in RECORD_CHECKS) <= set(sample["UniqueNIBRNo"]))
    record_checks = results["record_checks"]
    add("record checks: all fields match expectations", True, bool(record_checks["match"].all()),
        f"{int(record_checks['match'].sum())}/{len(record_checks)} fields match")
    return checks


# ---------------------------------------------------------------------------
# Orchestration and outputs
# ---------------------------------------------------------------------------
def finalize(path, raw, sha256_before, missing_tokens, text_report, type_report, time_report, clean) -> dict:
    """Build summaries, sample, record checks and validation from the cleaned frame."""
    district_month, unassigned_month, join_audits = build_district_month(clean)
    context = month_context(clean)
    month_summary, month_audit = build_month_summary(clean, context)
    results = {
        "raw": raw,
        "clean": clean,
        "sha256_before": sha256_before,
        "missing_tokens": missing_tokens,
        "text_report": text_report,
        "type_report": type_report,
        "time_report": time_report,
        "district_month": district_month,
        "unassigned_month": unassigned_month,
        "month_context": context,
        "month_summary": month_summary,
        "join_audits": join_audits + [month_audit],
        "lookup_audits": audit_lookups(clean),
        "sample": select_sample(clean),
        "record_checks": check_records(raw, clean),
        "recount": independent_recount(raw, district_month),
    }
    results["sha256_after"] = sha256_file(path)
    results["validation"] = validate(results)
    return results


def run_pipeline(path: Path | str = RAW_PATH) -> dict:
    """Run every step in order, exactly as the notebook does."""
    sha256_before = sha256_file(path)
    raw = load_raw(path)
    missing_tokens = check_missing_tokens(path, raw)
    nibrs, text_report = standardize_text(raw)
    nibrs, type_report = convert_types(nibrs)
    nibrs = add_quality_flags(nibrs)
    nibrs, time_report = add_time_fields(nibrs)
    nibrs = add_coordinate_flags(nibrs)
    nibrs = apply_scope(nibrs)
    return finalize(path, raw, sha256_before, missing_tokens, text_report, type_report, time_report, nibrs)


def _json_ready(value):
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def summary_tables(results: dict) -> dict:
    raw, clean = results["raw"], results["clean"]
    ins = clean["in_scope"]
    na_before = raw.isna().sum()
    na_after = clean[raw.columns].isna().sum()
    na_in_scope = clean.loc[ins, raw.columns].isna().sum()
    missing = [
        {"column": c, "na_before": int(na_before[c]), "na_after": int(na_after[c]), "na_after_in_scope": int(na_in_scope[c])}
        for c in raw.columns
        if na_before[c] or na_after[c]
    ]
    scope = clean["scope_reason"].value_counts().reindex(
        ["pre_2024", "2024_pre_rms", "2024_rms_transition", "in_scope"], fill_value=0
    )
    month = results["month_summary"]
    flag_columns = [
        "occ_implausible_year", "rpt_before_occ", "rpt_dist_area_only", "district_eligible", "toc_mismatch",
        "tvc_conflict", "nibr_code_missing", "nibr_desc_code_conflict", "same_code_repeat_in_case",
        "case_field_inconsistent", "location_suspected_generalized", "coord_missing", "coord_zero",
        "coord_nonnumeric", "coord_nonfinite", "coord_out_of_global_bounds", "map_eligible",
        "coord_outside_basic_range", "coord_far_from_district_review", "time_is_0000", "time_is_1200",
        "time_conflict", "night",
    ]
    flags = [
        {"flag": f, "all_rows": int(clean[f].sum()), "in_scope": int((clean[f] & ins).sum())} for f in flag_columns
    ]
    return {
        "missing_values": missing,
        "scope_accounting": {k: int(v) for k, v in scope.items()},
        "flag_counts": flags,
        "in_scope_months": month.to_dict(orient="records"),
        "join_audits": results["join_audits"],
        "lookup_audits": results["lookup_audits"],
        "unassigned_district_night_by_area_month": results["unassigned_month"].to_dict(orient="records"),
    }


DECISION_LOG = [
    ("Load all columns as text (dtype='string'); keep `raw` unchanged",
     "Preserves leading zeros in codes and IDs; avoids silent type guessing. Default NA tokens still apply.",
     ["raw CSV SHA-256 after run (file unchanged)", "only empty fields became NA on load",
      "non-missing values identical to literal text"]),
    ("Keep all rows; one row = one offense (UniqueNIBRNo)",
     "No exact duplicates or repeated IDs; repeated CaseNo values are multi-offense cases.",
     ["exact duplicate rows", "UniqueNIBRNo unique in cleaned data", "cleaned rows = raw rows (no rows removed by cleaning)"]),
    ("Strip AREA NAME padding; collapse repeated spaces in NIBR Description (no case changes)",
     "Formatting only; meaningful category differences and leading zeros are kept.",
     ["AREA NAME distinct after", "NIBR Description distinct after", "leading-zero columns keep their lengths"]),
    ("Convert dates (explicit format), counts (Int64), LAT/LON (Float64), Yes/No (boolean)",
     "Enables validation and calculations; failures counted rather than hidden.",
     ["failed type conversions (all columns)", "Yes/No columns: True count = original Yes count"]),
    ("Keep missing values as NA (weapon, group, premise, status, report date); no filling",
     "Missing weapon is not 'no weapon'; filling would invent information.",
     ["NA counts unchanged except LAT/LON"]),
    ("Set (0, 0) coordinates to NA and flag coord_zero; no replacement coordinates",
     "(0, 0) is not a location in Los Angeles.",
     ["coord_zero", "LAT NA after cleaning (131 missing + 550 zero)"]),
    ("map_eligible = numeric, finite, within global bounds, not missing, not (0, 0)",
     "Basic validity only; passing does not establish location accuracy.",
     ["map_eligible rows: finite and within global bounds", "map_eligible rows: no (0, 0) pair in original values",
      "map_eligible (in scope)"]),
    ("Flag rough-LA-box and >5 km-from-district-median points for review only",
     "Unusual does not mean wrong; no point excluded on distance alone. A False distance flag means "
     "'not flagged'; rows without a distance were not assessed.",
     ["coord_outside_basic_range (review, in scope)", "coord_far_from_district_review (in scope)"]),
    ("Flag LOCATION = RPT Dist No as suspected generalized location",
     "Each district shares one coordinate pair in these rows; not documented by the source.",
     ["location_suspected_generalized (in scope)"]),
    ("Flag area-only RPT Dist No; exclude from district counts, report as unassigned",
     "A 2-digit value is an area, not a district; no district is guessed.",
     ["rpt_dist_area_only (in scope)", "unassigned night incl. 0000"]),
    ("Flag case-level total mismatches/conflicts; never sum TotalOffenseCount or TotalVictimCount",
     "They repeat on every offense row and sometimes conflict within a case.",
     ["toc_mismatch cases", "tvc_conflict cases"]),
    ("Analysis scope: Date OCC >= 2025-01-01 (occurrence, not report date)",
     "Phase 1 scope; excludes pre-RMS and 2024 transition records without calling them wrong.",
     ["scope: in scope rows", "scope: in-scope + out-of-scope = all rows"]),
    ("Night = 20:00 inclusive to 06:00 exclusive (fixed-clock approximation)",
     "Matches the Phase 1 sketch; sunset/sunrise deferred.",
     ["night incl. 0000 (in scope)", "night excl. 0000 (in scope)"]),
    ("Keep and flag Time OCC 0000; report night counts with and without it",
     "Midnight values are heaped; the source does not explain why.",
     ["Time OCC 0000 (in scope)"]),
    ("occ_year_month from validated Date OCC; 2026-09 labeled calendar-partial; all observed records kept",
     "Calendar coverage differs from reporting completeness; late reports can arrive for any month.",
     ["only 2026-09 labeled partial", "2026-09-19 records kept"]),
    ("Monthly table holds observed district-month combinations only (absent is not zero)",
     "Complete grid and persistence thresholds deferred.",
     ["reconcile incl.: district-month + unassigned = in-scope night", "independent raw recount of 3 cells matches"]),
    ("Internal joins only: month context attached by many-to-one left joins on occ_year_month; "
     "CaseNo and district-median lookups audited",
     "No external dataset is merged; joins must not add or drop rows or leave keys unmatched.",
     ["join [district-month night counts <- month context]: result rows = left rows (no extra rows)",
      "join [district-month night counts <- month context]: unmatched left rows",
      "lookup [CaseNo counts]: unmatched rows",
      "lookup [district median]: unmatched among eligible rows",
      "lookup [district median]: rows not looked up with far flag True",
      "lookup [district median]: looked up + area-only + other = all rows"]),
]


def decision_log_markdown(validation: list[dict]) -> str:
    by_name = {c["check"]: c for c in validation}
    lines = [
        "# Cleaning decision log",
        "",
        "Generated by `clean_nibrs.py` from the validation results of the same run.",
        "",
        "| # | Rule | Reason | Check (result) |",
        "|---|---|---|---|",
    ]
    for number, (rule, reason, check_names) in enumerate(DECISION_LOG, start=1):
        parts = []
        for name in check_names:
            c = by_name[name]
            status = "PASS" if c["passed"] else "FAIL"
            parts.append(f"{name}: {c['actual']} ({status})")
        lines.append(f"| {number} | {rule} | {reason} | {'<br>'.join(parts)} |")
    return "\n".join(lines) + "\n"


def record_checks_markdown(record_checks: pd.DataFrame) -> str:
    lines = [
        "# Record checks",
        "",
        "Expected results were written in plan.md (section 8) before the transformations were run.",
        "",
    ]
    for check in RECORD_CHECKS:
        subset = record_checks[record_checks["record"] == check["id"]]
        lines += [
            f"## {check['id']}: `{check['uid']}`",
            "",
            f"Why difficult: {check['why']}",
            "",
            "| Field | Original value(s) | Expected | Actual | Match |",
            "|---|---|---|---|---|",
        ]
        for row in subset.itertuples(index=False):
            lines.append(f"| {row.field} | {row.original} | {row.expected} | {row.actual} | {'Yes' if row.match else 'No'} |")
        lines.append("")
    return "\n".join(lines)


def write_outputs(results: dict, outdir: Path | str) -> dict:
    """Write all output files. Contents are deterministic (no timestamps or absolute paths)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    files = {
        "nibrs_clean.csv": lambda p: results["clean"].to_csv(p, index=False, lineterminator="\n"),
        "district_month_night.csv": lambda p: results["district_month"].to_csv(p, index=False, lineterminator="\n"),
        "sample_cleaned_rows.csv": lambda p: results["sample"].to_csv(p, index=False, lineterminator="\n"),
    }
    for name, writer in files.items():
        writer(outdir / name)

    summary = {
        "source_file": RAW_PATH.as_posix(),
        "source_sha256_expected": EXPECTED_SHA256,
        "source_sha256_before_run": results["sha256_before"],
        "source_sha256_after_run": results["sha256_after"],
        "load_missing_tokens": results["missing_tokens"],
        "text_standardization": results["text_report"],
        "type_conversion": results["type_report"],
        "time_checks": results["time_report"],
        "validation": results["validation"],
        "validation_passed": sum(c["passed"] for c in results["validation"]),
        "validation_failed": sum(not c["passed"] for c in results["validation"]),
        "independent_recount": results["recount"],
        **summary_tables(results),
    }
    (outdir / "validation_summary.json").write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    (outdir / "cleaning_decision_log.md").write_text(decision_log_markdown(results["validation"]), encoding="utf-8")
    (outdir / "record_checks.md").write_text(record_checks_markdown(results["record_checks"]), encoding="utf-8")
    return {p.name: sha256_file(p) for p in sorted(outdir.iterdir()) if p.is_file()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean the LAPD NIBRS Offenses CSV (DSO 576 Module 6).")
    parser.add_argument("--input", default=str(RAW_PATH), help="path to the original CSV")
    parser.add_argument("--outdir", default="outputs", help="folder for output files")
    args = parser.parse_args(argv)

    results = run_pipeline(args.input)
    hashes = write_outputs(results, args.outdir)
    failed = [c for c in results["validation"] if not c["passed"]]
    print(f"Validation: {len(results['validation']) - len(failed)} passed, {len(failed)} failed")
    for c in failed:
        print(f"  FAILED: {c['check']}: expected {c['expected']!r}, actual {c['actual']!r} {c['note']}")
    print("Output SHA-256:")
    for name, digest in hashes.items():
        print(f"  {digest}  {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
