"""Run with python -m src.clean_data. Raw files are never written."""
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

from .config import (RAW, PROCESSED, REPORTS, START_DATE, EXPECTED_BYTES,
                     EXPECTED_SHA256, EXPECTED_ROWS, SOURCE_COLUMNS,
                     DATE_FORMAT, LAT_BOUNDS, LON_BOUNDS)


def verify_source(path=RAW):
    path = Path(path)
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        columns = next(reader)
        rows = 0
        for row in reader:
            if len(row) != len(SOURCE_COLUMNS):
                raise ValueError(f'CSV record {rows + 2} has {len(row)} columns')
            rows += 1
    with path.open(encoding='utf-8-sig') as f:
        lines = sum(1 for _ in f)
    actual = (path.stat().st_size, digest, rows, lines, columns)
    expected = (EXPECTED_BYTES, EXPECTED_SHA256, EXPECTED_ROWS,
                EXPECTED_ROWS + 1, SOURCE_COLUMNS)
    if actual != expected:
        raise ValueError(f'Approved source verification failed: {actual}')
    return dict(filename=path.name, bytes=actual[0], sha256=digest,
                data_rows=rows, physical_lines=lines, columns=columns)


def clean_offenses(raw):
    """Return a new full-history frame and audit; remove only exact source copies."""
    missing = set(SOURCE_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing source columns: {sorted(missing)}')
    duplicate_count = int(raw.duplicated().sum())
    d = raw.drop_duplicates().copy().reset_index(drop=True)
    for col in SOURCE_COLUMNS:
        d[col] = d[col].astype('string').str.strip().replace('', pd.NA)
    for col in ['Date OCC', 'Date Rptd', 'Time OCC', 'LAT', 'LON']:
        d[col + '_source'] = d[col].copy()
    for col in ['Date OCC', 'Date Rptd']:
        d[col] = pd.to_datetime(d[col], format=DATE_FORMAT, errors='coerce')
    d['offense_date'] = d['Date OCC'].dt.normalize()
    d['offense_month'] = d['offense_date'].dt.to_period('M').dt.to_timestamp()
    t = d['Time OCC'].str.zfill(4)
    hour = pd.to_numeric(t.str[:2], errors='coerce')
    minute = pd.to_numeric(t.str[2:], errors='coerce')
    valid = (t.str.fullmatch(r'\d{4}') & hour.between(0, 23)
             & minute.between(0, 59)).fillna(False)
    d['Time OCC'] = t
    d['has_valid_time'] = valid
    d['offense_hour'] = hour.where(valid).astype('Int64')
    d['is_midnight_code'] = t.eq('0000').fillna(False)
    d['is_night'] = (valid & (hour.ge(18) | hour.lt(6))).fillna(False)
    for col in ['TotalOffenseCount', 'TotalVictimCount']:
        values = pd.to_numeric(d[col], errors='coerce')
        d[col] = values.where(values.mod(1).eq(0) & values.ge(0)).astype('Int64')
    for col in ['LAT', 'LON']:
        d[col] = pd.to_numeric(d[col], errors='coerce').astype('Float64')
    coord_missing = d[['LAT_source', 'LON_source']].isna().any(axis=1)
    coord_nonnumeric = (~coord_missing & d[['LAT', 'LON']].isna().any(axis=1))
    coord_zero = (d['LAT'].eq(0) | d['LON'].eq(0)).fillna(False)
    d['has_valid_coordinates'] = (d['LAT'].between(*LAT_BOUNDS)
                                  & d['LON'].between(*LON_BOUNDS)).fillna(False)
    d['in_analysis_scope'] = d['offense_date'].ge(pd.Timestamp(START_DATE))
    d['has_repeated_offense_id'] = (d['UniqueNIBRNo'].notna()
                                   & d['UniqueNIBRNo'].duplicated(keep=False))
    qualifying = (d['in_analysis_scope'] & d['is_night']
                  & d['RPT Dist No'].notna() & d['UniqueNIBRNo'].notna())
    n = int(qualifying.sum())
    mapped = int((qualifying & d['has_valid_coordinates']).sum())
    repeated_cases = d['CaseNo'].notna() & d['CaseNo'].duplicated(keep=False)
    q = dict(
        raw_rows=len(raw), processed_rows=len(d),
        exact_duplicates_found=duplicate_count, exact_duplicates_removed=duplicate_count,
        repeated_offense_id_rows=int(d['has_repeated_offense_id'].sum()),
        repeated_offense_id_values=int(d.loc[d['has_repeated_offense_id'], 'UniqueNIBRNo'].nunique()),
        repeated_case_rows_retained=int(repeated_cases.sum()),
        repeated_case_values=int(d.loc[repeated_cases, 'CaseNo'].nunique()),
        missing_offense_ids=int(d['UniqueNIBRNo'].isna().sum()),
        invalid_or_missing_dates=int(d['offense_date'].isna().sum()),
        records_before_2025=int(d['offense_date'].lt(pd.Timestamp(START_DATE)).sum()),
        invalid_or_missing_times=int((~valid).sum()),
        missing_times=int(d['Time OCC_source'].isna().sum()),
        midnight_codes=int(d['is_midnight_code'].sum()),
        missing_reporting_districts=int(d['RPT Dist No'].isna().sum()),
        missing_coordinates=int(coord_missing.sum()),
        nonnumeric_coordinates=int(coord_nonnumeric.sum()),
        zero_coordinates=int(coord_zero.sum()),
        out_of_area_nonzero_coordinates=int((~d['has_valid_coordinates']
            & ~coord_missing & ~coord_nonnumeric & ~coord_zero).sum()),
        invalid_coordinates_total=int((~d['has_valid_coordinates']).sum()),
        nighttime_records_all_dates=int(d['is_night'].sum()),
        qualifying_nighttime_records=n, qualifying_mapped_nighttime_records=mapped,
        qualifying_mapped_percentage=100 * mapped / n if n else 0,
        minimum_offense_date=str(d['offense_date'].min()),
        maximum_offense_date=str(d['offense_date'].max()),
        missing_values_by_column={c: int(d[c].isna().sum()) for c in SOURCE_COLUMNS},
        streetlight_status='Unavailable: no approved GIS file in repository',
    )
    return d, q


def main():
    verification = verify_source()
    raw = pd.read_csv(RAW, dtype='string', keep_default_na=False, na_values=[''])
    d, quality = clean_offenses(raw)
    # Verify again before writing outputs to detect source changes during the run.
    with RAW.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != verification['sha256']:
            raise ValueError('Source changed during cleaning')
    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    d.to_parquet(PROCESSED, index=False, compression='zstd')
    quality['source'] = verification
    quality['processed'] = dict(path='data/processed/' + PROCESSED.name,
                               format='Parquet', bytes=PROCESSED.stat().st_size,
                               rows=len(d), columns=len(d.columns))
    (REPORTS / 'data_quality.json').write_text(json.dumps(quality, indent=2) + '\n', encoding='utf-8')
    dictionary = []
    descriptions = {
        'CaseNo': 'Case identifier; repeated cases retained, never a deduplication key.',
        'UniqueNIBRNo': 'Offense identifier; all offense metrics use distinct nonmissing IDs.',
        'Date OCC': 'Parsed occurrence timestamp; invalid values become NaT.',
        'Date Rptd': 'Parsed report timestamp; invalid values become NaT.',
        'Time OCC': 'Zero-padded source HHMM; invalid values retained and flagged.',
        'RPT Dist No': 'Reporting-district geographic analysis key, retained as string.',
        'LAT': 'Numeric source latitude; validity determined separately.',
        'LON': 'Numeric source longitude; validity determined separately.',
        'offense_date': 'Occurrence date normalized to midnight; no time classification from this field.',
        'offense_month': 'First calendar day of occurrence month.',
        'offense_hour': 'Nullable integer hour from valid Time OCC only.',
        'has_valid_time': 'HHMM has 1-4 source digits, hour 00-23, minute 00-59.',
        'is_midnight_code': 'Normalized Time OCC equals 0000; valid midnight.',
        'is_night': 'Valid time in 18:00-23:59 or 00:00-05:59.',
        'has_valid_coordinates': 'Latitude 33.5-34.9 and longitude -118.9 to -117.5 inclusive; screening only.',
        'in_analysis_scope': 'Valid offense_date on or after 2025-01-01.',
        'has_repeated_offense_id': 'Nonmissing offense ID occurs in multiple nonidentical records; retained for review.',
    }
    for col in d.columns:
        meaning = descriptions.get(col, ('Trimmed source value before conversion.' if col.endswith('_source')
            else 'Source ' + col + '; surrounding whitespace trimmed, missing values preserved.'))
        dictionary.append(dict(column=col, origin='source' if col in SOURCE_COLUMNS else 'derived/audit',
                               dtype=str(d[col].dtype), description=meaning))
    pd.DataFrame(dictionary).to_csv(REPORTS / 'data_dictionary.csv', index=False)
    print(json.dumps(quality, indent=2))


if __name__ == '__main__':
    main()
