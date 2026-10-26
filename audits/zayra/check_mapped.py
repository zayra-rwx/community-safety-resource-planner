"""Zayra's Module 9 audit checks: valid mapped nighttime offenses + district composition.

Run from the repository root:
    python audits/zayra/check_mapped.py --raw <path to LAPD_NIBRS_Offenses_Dataset_20261004.csv>

Check 1 rebuilds the number from the raw CSV text with the csv module only. It does
not use clean_data.py, the Parquet file or the derived is_night/has_valid_coordinates
columns, so it is an independent second calculation.
"""
import argparse
import csv
import math
import statistics
from collections import defaultdict
from datetime import datetime, date

import pandas as pd

from src.analysis import Filters, load_processed, ranked_districts, category_summary, count_nighttime_offenses
from src.clean_data import clean_offenses
from src.config import RAW, SOURCE_COLUMNS

START = date(2025, 1, 1)


def is_night_text(text):
    t = (text or '').strip()
    if not t.isdigit() or len(t) > 4:
        return False
    t = t.zfill(4)
    hour, minute = int(t[:2]), int(t[2:])
    return 0 <= hour <= 23 and 0 <= minute <= 59 and (hour >= 18 or hour < 6)


def coords_text(lat_text, lon_text):
    try:
        lat, lon = float(lat_text), float(lon_text)
    except (TypeError, ValueError):
        return None
    if 33.5 <= lat <= 34.9 and -118.9 <= lon <= -117.5:
        return lat, lon
    return None


def check_1_independent(raw_path, ranking):
    print('== Check 1: independent recount from raw CSV text')
    rows = []
    with open(raw_path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            try:
                day = datetime.strptime(r['Date OCC'].strip(), '%Y %b %d %I:%M:%S %p').date()
            except ValueError:
                continue
            rows.append((day, r))
    max_day = max(day for day, _ in rows)
    mapped = defaultdict(set)
    for day, r in rows:
        dist, oid = r['RPT Dist No'].strip(), r['UniqueNIBRNo'].strip()
        if START <= day <= max_day and dist and oid and is_night_text(r['Time OCC']) \
                and coords_text(r['LAT'], r['LON']):
            mapped[dist].add(oid)
    mine = pd.Series({k: len(v) for k, v in mapped.items()}, name='mine')
    app = ranking.set_index('RPT Dist No')['Valid mapped nighttime offenses']
    joined = pd.concat([app.rename('app'), mine], axis=1).fillna(0).astype(int)
    diff = joined[joined['app'] != joined['mine']]
    print(f'max date {max_day}; districts compared {len(joined)}; disagreements {len(diff)}')
    print(f"total app {joined['app'].sum()}  mine {joined['mine'].sum()}")
    print('district 0182: app', joined.loc['0182', 'app'], 'mine', joined.loc['0182', 'mine'])


def check_2_fixture():
    print('== Check 2: hand-built fixture through clean_offenses + backend')
    # (id, district, date, time, lat, lon) -> expected mapped nighttime? (hand reasoning)
    cases = [
        ('A1', '0100', '2025 Jan 05 12:00:00 AM', '2200', '34.05', '-118.25', True),   # normal night
        ('A2', '0100', '2025 Jan 05 12:00:00 AM', '0000', '34.05', '-118.25', True),   # midnight counts
        ('A3', '0100', '2025 Jan 05 12:00:00 AM', '0559', '33.5', '-118.9', True),     # inclusive corner
        ('A4', '0100', '2025 Jan 05 12:00:00 AM', '1800', '34.9', '-117.5', True),     # inclusive corner
        ('A5', '0100', '2025 Jan 05 12:00:00 AM', '0600', '34.05', '-118.25', False),  # daytime
        ('A6', '0100', '2025 Jan 05 12:00:00 AM', '2300', '34.9001', '-118.25', False),  # just outside
        ('A7', '0100', '2025 Jan 05 12:00:00 AM', '2300', '0', '0', False),            # zero
        ('A8', '0100', '2025 Jan 05 12:00:00 AM', '2300', '', '', False),              # missing
        ('A9', '0100', '2025 Jan 05 12:00:00 AM', '2300', 'abc', '-118.25', False),    # nonnumeric
        ('B1', '0100', '2024 Dec 31 12:00:00 AM', '2300', '34.05', '-118.25', False),  # before 2025
        ('B2', '0200', '2025 Jan 06 12:00:00 AM', '0100', '34.05', '-118.25', True),   # 2nd district
    ]
    raw = pd.DataFrame([{c: 'x' for c in SOURCE_COLUMNS} for _ in cases])
    for i, (oid, dist, day, tm, lat, lon, _) in enumerate(cases):
        raw.loc[i, ['UniqueNIBRNo', 'CaseNo', 'RPT Dist No', 'Date OCC', 'Time OCC', 'LAT', 'LON']] = \
            [oid, oid, dist, day, tm, lat, lon]
    raw = raw.replace('', pd.NA).astype('string')
    d, _ = clean_offenses(raw)
    expected = {'0100': 4, '0200': 1}
    got = ranked_districts(d).set_index('RPT Dist No')['Valid mapped nighttime offenses'].to_dict()
    total = count_nighttime_offenses(d, mapped_only=True)
    print('expected', expected, 'total 5; got', got, 'total', total,
          'PASS' if got == expected and total == 5 else 'FAIL')


def check_3_plausibility(d):
    print('== Check 3: are "valid" coordinates plausible for their own district?')
    from src.analysis import nighttime_offenses
    night = nighttime_offenses(d, Filters())
    m = night[night['has_valid_coordinates']]
    km = []
    for _, g in m.groupby('RPT Dist No'):
        lat0, lon0 = statistics.median(g['LAT']), statistics.median(g['LON'])
        for lat, lon in zip(g['LAT'], g['LON']):
            dy = (lat - lat0) * 111.0
            dx = (lon - lon0) * 111.0 * math.cos(math.radians(34.05))
            km.append(math.hypot(dx, dy))
    km = pd.Series(km)
    for k in (10, 20):
        print(f'valid mapped nighttime points > {k} km from own district median: {int((km > k).sum())}')
    ex = m[(m['RPT Dist No'] == '0331')][['RPT Dist No', 'AREA NAME', 'LOCATION', 'LAT', 'LON']]
    print(ex[ex['LAT'] > 34.3].to_string())
    short = night[night['RPT Dist No'].str.len() < 4]
    unmapped = night[~night['has_valid_coordinates']]
    print(f"short (area-level) district codes: {sorted(short['RPT Dist No'].unique())}")
    print(f'nighttime offenses in them: {len(short)}; unmapped nighttime total: {len(unmapped)}; '
          f"unmapped in short codes: {int((unmapped['RPT Dist No'].str.len() < 4).sum())}")


def check_4_feature(d, ranking):
    print('== Check 4: district composition feature (category_summary), district 0182')
    f = Filters(districts=('0182',))
    count = int(ranking.set_index('RPT Dist No').loc['0182', 'Nighttime reported offenses'])
    for col in ('NIBR Description', 'Premise Desc'):
        s = category_summary(d, col, f)
        print(f'{col}: {len(s)} categories, sum {s.nighttime_offenses.sum()} vs district count {count}')
        print(s.head(3).to_string(index=False))
    s = category_summary(d, 'Premise Desc', Filters())
    print(s[s['Premise Desc'].isin(['Unknown', 'Location Unknown'])].to_string(index=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', default=str(RAW))
    args = parser.parse_args()
    d = load_processed()
    ranking = ranked_districts(d, Filters())
    check_1_independent(args.raw, ranking)
    check_2_fixture()
    check_3_plausibility(d)
    check_4_feature(d, ranking)


if __name__ == '__main__':
    main()
