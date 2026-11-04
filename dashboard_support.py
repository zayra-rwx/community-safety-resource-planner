"""Display adapters for the existing Phase 2 backend."""
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from dataclasses import asdict

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype, is_string_dtype

from src.analysis import load_processed
from src.config import ROOT, PROCESSED, REPORTS, START_DATE, LAT_BOUNDS, LON_BOUNDS

APP_VERSION = "phase3-local-1"
LIMITATION = "Streetlight asset data was unavailable for this MVP. Rankings use reported-offense frequency and persistence; the map shows approximate offense locations, not measured lighting conditions."
WARNING = "Reported-offense patterns and mapped streetlights identify places for further assessment. They do not establish that lighting conditions caused offenses or that additional lighting will reduce them."
RUNTIME_FILES = (PROCESSED, REPORTS / "data_quality.json", REPORTS / "data_dictionary.csv")


def file_signature():
    paths = RUNTIME_FILES + (ROOT / "src/analysis.py", ROOT / "src/config.py", ROOT / "app.py", ROOT / "dashboard_support.py")
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Restore these canonical repository files: " + ", ".join(missing))
    return tuple((str(p.relative_to(ROOT)), p.stat().st_size, p.stat().st_mtime_ns) for p in paths)


def validate_data(d, quality, dictionary):
    missing = set(dictionary["column"]) - set(d.columns)
    if missing:
        raise ValueError("Canonical Parquet is missing columns: " + ", ".join(sorted(missing)))
    for row in dictionary.itertuples(index=False):
        col = d[row.column]
        kind = row.dtype.lower()
        valid = True
        if kind.startswith("datetime"):
            valid = is_datetime64_any_dtype(col)
        elif kind == "boolean":
            valid = is_bool_dtype(col)
        elif kind.startswith(("int", "float")):
            valid = is_numeric_dtype(col)
        elif kind == "string":
            valid = is_string_dtype(col)
        if not valid:
            raise ValueError(f"Canonical field {row.column} has an incompatible type.")
    if len(d) != quality["processed_rows"]:
        raise ValueError("Parquet row count disagrees with data_quality.json.")
    dates = d["Date OCC"].dt.normalize()
    if not dates.equals(d["offense_date"]):
        raise ValueError("offense_date disagrees with normalized Date OCC.")
    months = dates.dt.to_period("M").dt.to_timestamp()
    if not months.eq(d["offense_month"]).fillna(dates.isna()).all():
        raise ValueError("offense_month disagrees with occurrence dates.")
    time = d["Time OCC"].astype("string").str.zfill(4)
    hour = pd.to_numeric(time.str[:2], errors="coerce")
    minute = pd.to_numeric(time.str[2:], errors="coerce")
    valid_time = time.str.fullmatch(r"[0-9]{4}").fillna(False) & hour.between(0, 23) & minute.between(0, 59)
    expected_night = (valid_time & (hour.ge(18) | hour.lt(6))).fillna(False)
    if not d["is_night"].fillna(False).eq(expected_night).all():
        raise ValueError("Canonical nighttime flags disagree with valid HHMM.")
    if not d["has_valid_time"].fillna(False).eq(valid_time.fillna(False)).all():
        raise ValueError("Canonical time-validation flags disagree with HHMM.")
    if not d["is_midnight_code"].fillna(False).eq(time.eq("0000").fillna(False)).all():
        raise ValueError("Canonical midnight flags disagree with recorded time.")
    coordinates = (d["LAT"].between(*LAT_BOUNDS) & d["LON"].between(*LON_BOUNDS)).fillna(False)
    if not d["has_valid_coordinates"].fillna(False).eq(coordinates).all():
        raise ValueError("Canonical coordinate flags disagree with the documented screen.")
    if not d["in_analysis_scope"].fillna(False).eq(dates.ge(START_DATE).fillna(False)).all():
        raise ValueError("Canonical analysis-period flags disagree with occurrence dates.")
    if pd.isna(d["offense_date"].max()):
        raise ValueError("Canonical data has no valid occurrence dates.")


def load_bundle():
    signature = file_signature()
    d = load_processed()
    quality = json.loads((REPORTS / "data_quality.json").read_text())
    dictionary = pd.read_csv(REPORTS / "data_dictionary.csv")
    validate_data(d, quality, dictionary)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    metadata = {
        "processed_file": str(PROCESSED.relative_to(ROOT)),
        "processed_sha256": hashlib.sha256(PROCESSED.read_bytes()).hexdigest(),
        "raw_source_sha256": "97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5",
        "signature": signature,
        "rows": len(d), "columns": len(d.columns),
        "data_through": str(d["offense_date"].max().date()),
        "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend_revision": revision, "app_version": APP_VERSION,
        "app_source_sha256": hashlib.sha256((ROOT / "app.py").read_bytes()).hexdigest(),
    }
    return d, quality, dictionary, metadata


def select_scopes(universe, districts=None, minimum=1, top_n=10, sort_column="Rank", descending=False):
    eligible = universe.copy()
    if districts is not None:
        eligible = eligible.loc[eligible["RPT Dist No"].isin(districts)]
    eligible = eligible.loc[eligible["Active months"].ge(minimum)].copy()
    overview = eligible if top_n is None else eligible.head(top_n)
    overview = overview.sort_values([sort_column, "Rank"] if sort_column != "Rank" else ["Rank"],
                                    ascending=[not descending, True] if sort_column != "Rank" else [not descending],
                                    kind="stable").reset_index(drop=True)
    return eligible.reset_index(drop=True), overview


def scope_kpis(eligible):
    total = int(eligible["Nighttime reported offenses"].sum())
    mapped = int(eligible["Valid mapped nighttime offenses"].sum())
    return {"offenses": total, "districts": len(eligible), "persistence": float(eligible["Persistence rate"].mean()) if len(eligible) else 0.0,
            "mapped": mapped, "coverage": mapped / total if total else None}


def district_label(code, areas):
    kind = " (area-level source code)" if len(str(code)) < 4 else ""
    return f"{code} - {areas or 'Unknown'}{kind}"


def top_categories(summary, label, n=10):
    result = summary.head(n).copy()
    if len(summary) > n:
        result = pd.concat([result, pd.DataFrame({label: ["Other (remaining categories)"],
                           "nighttime_offenses": [int(summary.iloc[n:]["nighttime_offenses"].sum())]})], ignore_index=True)
    return result


def map_cells(mapped):
    if mapped.empty:
        return pd.DataFrame(columns=["latitude", "longitude", "Reported offenses"])
    safe = pd.DataFrame({"latitude": mapped["LAT"].round(3), "longitude": mapped["LON"].round(3),
                         "id": mapped["UniqueNIBRNo"]})
    return (safe.groupby(["latitude", "longitude"])["id"].nunique()
            .rename("Reported offenses").reset_index())


def export_payload(overview, metadata, filters, *, universe_count, eligible_count, minimum, top_n, sort_column, descending):
    info = dict(metadata)
    info.update({"filters": asdict(filters), "minimum_active_months": minimum, "top_n": top_n,
                 "sort": {"column": sort_column, "descending": descending},
                 "scope_counts": {"universe": universe_count, "eligible": eligible_count, "overview": len(overview)},
                 "nighttime": "18:00-05:59; includes recorded midnight",
                 "persistence": "active months / all intersecting calendar months, including partial endpoints",
                 "priority_score": "100 * (0.60 * frequency percentile + 0.40 * persistence percentile)",
                 "percentile_method": "ascending average rank divided by universe count; zero-night districts score zero",
                 "recent_period": "latest up to three complete calendar months; no complete months means 0 with no period",
                 "coordinate_screen": {"latitude": LAT_BOUNDS, "longitude": LON_BOUNDS},
                 "streetlights": LIMITATION,
                 "district_codes": "Import CSV district codes as text to preserve leading zeros.",
                 "recent_period_start": overview["Recent period start"].iloc[0] if len(overview) else None,
                 "recent_period_end": overview["Recent period end"].iloc[0] if len(overview) else None})
    return overview.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).encode("utf-8"), json.dumps(info, default=str, ensure_ascii=False, indent=2).encode("utf-8")
