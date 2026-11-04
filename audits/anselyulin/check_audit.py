"""Reproduce Yu (Ansel) Lin's Module 9 audit without changing team inputs.

Run from the repository root: python audits/anselyulin/check_audit.py
The oracle uses preserved source text, Python datetime/calendar and sets. It
does not call production filtering, time, month-window or counting helpers.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.analysis import Filters, ranked_districts, recent_period
from src.clean_data import clean_offenses
from src.config import SOURCE_COLUMNS

AUDITED_COMMIT = "87a892a392727cfaff176d3c0fbbf6019a60eb4a"
DISTRICT = "1494"
PARQUET = ROOT / "data/processed/lapd_nibrs_offenses.parquet"
SOURCE_FIELDS = ["UniqueNIBRNo", "Date OCC_source", "Time OCC_source",
                 "RPT Dist No", "AREA NAME", "NIBR Description"]
MONTHS = {name: number for number, name in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def text_or_none(value):
    return None if pd.isna(value) else str(value)


def reference_records(frame):
    """Independently derive occurrence dates and nighttime from source text."""
    records = []
    for values in frame[SOURCE_FIELDS].itertuples(index=False, name=None):
        identity, source_date, source_time, district, area, description = map(text_or_none, values)
        try:
            parts = source_date.split()
            occurrence = date(int(parts[0]), MONTHS[parts[1]], int(parts[2]))
        except (AttributeError, KeyError, IndexError, ValueError):
            occurrence = None
        clock = (source_time or "").strip()
        valid = 1 <= len(clock) <= 4 and clock.isascii() and clock.isdigit()
        padded = clock.zfill(4)
        hour = int(padded[:2]) if valid else -1
        minute = int(padded[2:]) if valid else -1
        valid = valid and 0 <= hour <= 23 and 0 <= minute <= 59
        night = valid and (hour >= 18 or hour < 6)
        records.append((identity, occurrence, night, district, area, description))
    return records


def reference(records, filters):
    """Use calendar enumeration and ID sets, never production metric helpers."""
    maximum = max(r[1] for r in records if r[1] is not None)
    start = max(date.fromisoformat(filters.get("start") or "2025-01-01"), date(2025, 1, 1))
    end = min(date.fromisoformat(filters["end"]) if filters.get("end") else maximum, maximum)
    intersecting, complete = [], []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        intersecting.append(cursor)
        if cursor >= start and last <= end:
            complete.append((cursor, last))
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    recent = complete[-3:]
    lower, upper = (recent[0][0], recent[-1][1]) if recent else (None, None)
    selected = []
    for row in records:
        identity, occurrence, night, district, area, description = row
        if occurrence is None or not start <= occurrence <= end:
            continue
        if filters.get("areas") is not None and area not in filters["areas"]:
            continue
        if filters.get("descriptions") is not None and description not in filters["descriptions"]:
            continue
        if filters.get("districts") is not None and district not in filters["districts"]:
            continue
        selected.append(row)
    districts = sorted({r[3] for r in selected if r[3] is not None})
    counts = {district: set() for district in districts}
    totals = {district: set() for district in districts}
    monthly = {district: {m.isoformat(): set() for m in intersecting} for district in districts}
    for identity, occurrence, night, district, area, description in selected:
        if not night or district is None or identity is None:
            continue
        totals[district].add(identity)
        monthly[district][date(occurrence.year, occurrence.month, 1).isoformat()].add(identity)
        if lower is not None and lower <= occurrence <= upper:
            counts[district].add(identity)
    return {
        "resolved_start": start.isoformat(), "resolved_end": end.isoformat(),
        "recent_start": lower.isoformat() if lower else None,
        "recent_end": upper.isoformat() if upper else None,
        "eligible_months": len(intersecting),
        "recent_by_district": {k: len(v) for k, v in counts.items()},
        "total_by_district": {k: len(v) for k, v in totals.items()},
        "monthly": {k: {m: len(ids) for m, ids in v.items()} for k, v in monthly.items()},
    }


def date_text(value):
    return None if value is None or pd.isna(value) else value.date().isoformat()


def check_backend(frame, records, name, filters):
    expected = reference(records, filters)
    f = Filters(**filters)
    actual_period = tuple(date_text(v) for v in recent_period(frame, f))
    assert actual_period == (expected["recent_start"], expected["recent_end"]), (name, actual_period)
    actual = ranked_districts(frame, f)
    actual_counts = dict(zip(actual["RPT Dist No"], actual["Recent nighttime offenses"].map(int)))
    assert actual_counts == expected["recent_by_district"], name
    assert all(int(v) == expected["eligible_months"] for v in actual["Eligible months"]), name
    assert all(date_text(v) == expected["recent_start"] for v in actual["Recent period start"]), name
    assert all(date_text(v) == expected["recent_end"] for v in actual["Recent period end"]), name
    for row in actual.to_dict("records"):
        count = int(row["Recent nighttime offenses"])
        total = expected["total_by_district"][row["RPT Dist No"]]
        assert 0 <= count <= total, name
    target = actual.loc[actual["RPT Dist No"].eq(DISTRICT)]
    result = {
        "name": name, "filters": filters, "status": "PASS",
        "recent_start": expected["recent_start"], "recent_end": expected["recent_end"],
        "eligible_months": expected["eligible_months"], "districts_checked": len(actual),
        "reference_recent_total": sum(expected["recent_by_district"].values()),
        "actual_recent_total": int(actual["Recent nighttime offenses"].sum()),
        "district_1494_reference": expected["recent_by_district"].get(DISTRICT),
        "district_1494_actual": int(target.iloc[0]["Recent nighttime offenses"]) if len(target) else None,
    }
    return result, expected


def check_cli(records, name, filters, transcript):
    command = [sys.executable, "-m", "src.analysis", "--top", "3"]
    for option in ("start", "end"):
        if option in filters:
            command.extend(["--" + option, filters[option]])
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    transcript.extend(["CASE: " + name, "COMMAND: python " + " ".join(command[1:]),
                       "EXIT: " + str(completed.returncode), "STDOUT:", completed.stdout,
                       "STDERR:", completed.stderr, ""])
    assert completed.returncode == 0, name
    expected = reference(records, filters)
    lines = completed.stdout.strip().splitlines()
    assert "Recent nighttime offenses" in lines[0], name
    assert "Recent period start" in lines[0] and "Recent period end" in lines[0], name
    parsed = []
    for line in lines[1:]:
        tokens = line.split()
        district = tokens[1]
        count = int(tokens[-6])
        period = [None if v in ("None", "NaT") else v for v in tokens[-2:]]
        assert count == expected["recent_by_district"][district], (name, district)
        assert period == [expected["recent_start"], expected["recent_end"]], name
        parsed.append({"district": district, "recent_nighttime_offenses": count})
    assert len(parsed) == min(3, len(expected["recent_by_district"])), name
    return {"name": name, "filters": filters, "status": "PASS", "exit_code": 0,
            "recent_start": expected["recent_start"], "recent_end": expected["recent_end"],
            "displayed_rows": parsed,
            "no_complete_months_explanation": "No complete months" in completed.stdout}


def fixture():
    defaults = dict.fromkeys(SOURCE_COLUMNS, pd.NA)
    defaults.update({"CaseNo": "synthetic-case", "Date Rptd": "2025 Apr 30 12:00:00 AM",
        "RPT Dist No": DISTRICT, "AREA NAME": "Pacific", "NIBR Code": "23A",
        "NIBR Description": "Synthetic offense", "Crime Against": "Property",
        "Premise Desc": "Street", "LAT": "34.05", "LON": "-118.25"})
    inputs = [("F01", "Feb 01", "0000", DISTRICT), ("F02", "Feb 28", "2359", DISTRICT),
              ("F03", "Mar 01", "0559", DISTRICT), ("F04", "Mar 31", "1800", DISTRICT),
              ("F05", "Apr 01", "1800", DISTRICT), ("F06", "Mar 15", "0600", DISTRICT),
              ("F07", "Mar 16", "1759", DISTRICT), ("F08", "Mar 20", "2400", DISTRICT),
              ("F09", "Mar 20", "1900", DISTRICT), ("F10", "Mar 20", "1800", "0101"),
              ("F11", "Apr 30", "1200", DISTRICT)]
    rows = []
    for identity, day, time, district in inputs:
        row = dict(defaults, UniqueNIBRNo=identity,
                   **{"Date OCC": "2025 " + day + " 12:00:00 AM", "Time OCC": time,
                      "RPT Dist No": district})
        if identity == "F03":
            row["LAT"] = row["LON"] = pd.NA
        rows.append(row)
    return pd.DataFrame(rows, dtype="string")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert git("rev-parse", AUDITED_COMMIT) == AUDITED_COMMIT
    # Audited source and inputs must still match the baseline, even after an
    # audit-only commit. No baseline reports are regenerated.
    baseline_paths = git("ls-tree", "-r", "--name-only", AUDITED_COMMIT).splitlines()
    protected = {}
    for name in baseline_paths:
        expected_blob = git("rev-parse", AUDITED_COMMIT + ":" + name)
        assert git("hash-object", "--path=" + name, name) == expected_blob, name
        protected[name] = digest(ROOT / name)
    frame = pd.read_parquet(PARQUET)
    assert frame.shape == (489955, 45)
    records = reference_records(frame)
    cases = [
        ("default", {}),
        ("february_through_partial_april", {"start": "2025-02-01", "end": "2025-04-01"}),
        ("partial_start_and_end", {"start": "2025-02-02", "end": "2025-04-01"}),
        ("no_complete_months", {"start": "2026-09-01", "end": "2026-09-19"}),
        ("one_complete_month", {"start": "2026-08-01", "end": "2026-08-31"}),
        ("end_capped_to_available_data", {"start": "2025-01-01", "end": "2026-12-31"}),
        ("start_clamped_to_scope", {"start": "2024-01-01", "end": "2026-09-19"}),
        ("pacific_area", {"areas": ("Pacific",)}),
        ("district_1494", {"districts": (DISTRICT,)}),
        ("sparse_category", {"descriptions": ("10 886 - US - F - Absence Without Leave - Absent From Place Of Duty - 90Z",)}),
    ]
    results, default_reference = [], None
    for name, filters in cases:
        result, expected = check_backend(frame, records, name, filters)
        results.append(result)
        if name == "default":
            default_reference = expected
        print("PASS backend:", name, result["districts_checked"], "district rows")
    with (out / "district-1494-monthly.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["reporting_district", "month", "reference_nighttime_offenses", "in_default_recent_window"])
        for month, count in default_reference["monthly"][DISTRICT].items():
            writer.writerow([DISTRICT, month, count,
                             default_reference["recent_start"] <= month <= default_reference["recent_end"]])
    transcript, cli = [], []
    for name, filters in cases[:6]:
        cli.append(check_cli(records, name, filters, transcript))
        print("PASS CLI:", name)
    (out / "cli-output.txt").write_text("\n".join(transcript).rstrip() + "\n", encoding="utf-8")
    raw = fixture()
    raw.to_csv(out / "synthetic-input.csv", index=False)
    cleaned, _ = clean_offenses(raw)
    # This reference frame takes the actual source strings, not cleaner-derived
    # dates/times. All four expected results below were specified before execution.
    reference_frame = raw.rename(columns={"Date OCC": "Date OCC_source", "Time OCC": "Time OCC_source"})
    synthetic_records = reference_records(reference_frame)
    synthetic = []
    handwritten = [
        ("fixture_feb1_apr1", "2025-02-01", "2025-04-01", "2025-02-01", "2025-03-31", 5),
        ("fixture_feb2_apr1", "2025-02-02", "2025-04-01", "2025-03-01", "2025-03-31", 3),
        ("fixture_march", "2025-03-01", "2025-03-31", "2025-03-01", "2025-03-31", 3),
        ("fixture_no_complete_month", "2025-04-01", "2025-04-01", None, None, 0),
    ]
    for name, start, end, lower, upper, number in handwritten:
        result, expected = check_backend(cleaned, synthetic_records, name,
                                          {"start": start, "end": end, "districts": (DISTRICT,)})
        assert result["district_1494_reference"] == number
        assert (result["recent_start"], result["recent_end"]) == (lower, upper)
        result["predeclared_expected_count"] = number
        synthetic.append(result)
        print("PASS fixture:", name, number)
    zero_raw = raw.loc[raw["UniqueNIBRNo"].isin(["F01", "F05", "F11"])].copy()
    zero_data, _ = clean_offenses(zero_raw)
    zero_reference = reference_records(zero_raw.rename(columns={"Date OCC": "Date OCC_source", "Time OCC": "Time OCC_source"}))
    result, expected = check_backend(zero_data, zero_reference, "fixture_zero_offense_complete_month",
        {"start": "2025-02-02", "end": "2025-04-01", "districts": (DISTRICT,)})
    assert (result["recent_start"], result["recent_end"], result["district_1494_reference"]) == ("2025-03-01", "2025-03-31", 0)
    result["predeclared_expected_count"] = 0
    synthetic.append(result)
    print("PASS fixture: fixture_zero_offense_complete_month 0")
    assert all(digest(ROOT / name) == sha for name, sha in protected.items())
    manifest = {
        "audited_commit": AUDITED_COMMIT, "execution_commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "executed_at_los_angeles": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
        "check_script_sha256": digest(Path(__file__)),
        "processed_rows": len(frame), "processed_columns": len(frame.columns),
        "processed_sha256": protected["data/processed/lapd_nibrs_offenses.parquet"],
        "baseline_files_unchanged": True, "baseline_file_sha256": protected,
        "environment": {"python": platform.python_version(), **{
            package: importlib.metadata.version(package) for package in ["pandas", "pyarrow", "pytest", "numpy"]}},
        "backend_cases": results, "cli_cases": cli, "synthetic_cases": synthetic,
        "overall_numeric_status": "PASS", "all_checks_passed": True,
        "limitations": ["Source-derived oracle reads preserved text from the committed Parquet; it does not reverify the original raw download.",
            "CLI/API audit only; no dashboard exists in the audited baseline.",
            "Execution and fixture arithmetic were performed by Codex; no human manual verification is claimed."]}
    (out / "results.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: 10 full-data backend scenarios, 6 CLI scenarios and 5 predeclared fixtures; baseline files unchanged.")


if __name__ == "__main__":
    main()
