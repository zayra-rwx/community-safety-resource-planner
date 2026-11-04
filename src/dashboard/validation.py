"""Application schema/invariant validation. Reports problems; never repairs data."""
import pandas as pd

from ..config import EXPECTED_SHA256, LAT_BOUNDS, LON_BOUNDS, START_DATE


class DataError(Exception):
    """Blocking, user-facing data error with a named file and recovery path.

    ``public_message`` contains only repository-relative paths and no stack trace
    or record identifiers; details go to local diagnostics.
    """

    def __init__(self, title, public_message, recovery):
        super().__init__(f'{title}: {public_message}')
        self.title = title
        self.public_message = public_message
        self.recovery = recovery


class SchemaError(DataError):
    pass


REQUIRED_QUALITY_KEYS = [
    'raw_rows', 'processed_rows', 'exact_duplicates_found', 'exact_duplicates_removed',
    'repeated_offense_id_rows', 'repeated_offense_id_values', 'repeated_case_rows_retained',
    'repeated_case_values', 'missing_offense_ids', 'invalid_or_missing_dates', 'records_before_2025',
    'invalid_or_missing_times', 'missing_times', 'midnight_codes', 'missing_reporting_districts',
    'missing_coordinates', 'nonnumeric_coordinates', 'zero_coordinates',
    'out_of_area_nonzero_coordinates', 'invalid_coordinates_total', 'nighttime_records_all_dates',
    'qualifying_nighttime_records', 'qualifying_mapped_nighttime_records',
    'qualifying_mapped_percentage', 'minimum_offense_date', 'maximum_offense_date', 'source', 'processed',
]
DICTIONARY_COLUMNS = ['column', 'origin', 'dtype', 'description']

_RECOVERY = ('Restore the committed file with `git checkout -- {path}`, or regenerate the processed '
             'outputs by placing the approved raw CSV at `data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv` '
             'and running `.venv\\Scripts\\python.exe -m src.clean_data`. Do not substitute another dataset.')


def recovery_for(path):
    return _RECOVERY.format(path=path)


def validate_dictionary(dictionary, path):
    missing = [c for c in DICTIONARY_COLUMNS if c not in dictionary.columns]
    if missing or dictionary.empty:
        raise SchemaError('Data dictionary error', f'`{path}` is missing required fields {missing}.',
                          recovery_for(path))
    return dictionary


def validate_quality(quality, path):
    missing = [k for k in REQUIRED_QUALITY_KEYS if k not in quality]
    if missing:
        raise SchemaError('Data-quality metadata error',
                          f'`{path}` is missing required fields: {", ".join(missing)}.', recovery_for(path))
    for key in ['filename', 'sha256']:
        if key not in quality['source']:
            raise SchemaError('Data-quality metadata error', f'`{path}` source block lacks `{key}`.',
                              recovery_for(path))
    return quality


def _bool(series):
    return series.astype('boolean').fillna(False).astype(bool)


def invariant_checks(d):
    """Return {check name: number of violating rows}. Zero means the invariant holds."""
    date = d['offense_date']
    month = date.dt.to_period('M').dt.to_timestamp()
    t = d['Time OCC']
    hour = pd.to_numeric(t.str[:2], errors='coerce')
    minute = pd.to_numeric(t.str[2:], errors='coerce')
    valid_time = _bool(t.str.fullmatch(r'\d{4}') & hour.between(0, 23) & minute.between(0, 59))
    night = valid_time & (hour.ge(18) | hour.lt(6)).fillna(False)
    in_box = _bool(d['LAT'].between(*LAT_BOUNDS) & d['LON'].between(*LON_BOUNDS))
    ids = d['UniqueNIBRNo']
    repeated = ids.notna() & ids.duplicated(keep=False)
    checks = {
        'offense_date is normalized to midnight': int((date.notna() & date.ne(date.dt.normalize())).sum()),
        'offense_month is first day of offense_date month': int(
            ((month.notna() | d['offense_month'].notna()) & ~month.eq(d['offense_month']).fillna(False)).sum()),
        'has_valid_time matches HHMM rule': int((_bool(d['has_valid_time']) != valid_time).sum()),
        'is_night matches 18:00-05:59 rule': int((_bool(d['is_night']) != night).sum()),
        'is_night implies has_valid_time': int((_bool(d['is_night']) & ~_bool(d['has_valid_time'])).sum()),
        'is_midnight_code matches Time OCC 0000': int((_bool(d['is_midnight_code']) != _bool(t.eq('0000'))).sum()),
        'offense_hour present only for valid times': int((d['offense_hour'].notna() != valid_time).sum()),
        'has_valid_coordinates matches screening box': int((_bool(d['has_valid_coordinates']) != in_box).sum()),
        'in_analysis_scope matches start date': int(
            (_bool(d['in_analysis_scope']) != _bool(date.ge(pd.Timestamp(START_DATE)))).sum()),
        'has_repeated_offense_id matches offense IDs': int((_bool(d['has_repeated_offense_id']) != repeated).sum()),
    }
    return checks


def validate_frame(d, dictionary, quality, path):
    """Check every dictionary field/type, derived-field invariants and metadata consistency.

    A missing column is an error; null values in present columns are permitted
    (they are reported by the quality audit, not repaired).
    """
    expected = dict(zip(dictionary['column'], dictionary['dtype']))
    missing = [c for c in expected if c not in d.columns]
    if missing:
        raise SchemaError('Processed data schema error',
                          f'`{path}` is missing required fields: {", ".join(missing)}.', recovery_for(path))
    extra = [c for c in d.columns if c not in expected]
    wrong = [f'{c} (expected {expected[c]}, found {d[c].dtype})'
             for c in expected if str(d[c].dtype) != expected[c]]
    if extra or wrong:
        detail = '; '.join(filter(None, [f'undocumented fields: {", ".join(extra)}' if extra else '',
                                          f'type mismatches: {", ".join(wrong)}' if wrong else '']))
        raise SchemaError('Processed data schema error', f'`{path}` does not match the data dictionary ({detail}).',
                          recovery_for(path))
    checks = invariant_checks(d)
    failed = {k: v for k, v in checks.items() if v}
    if failed:
        raise SchemaError('Processed data invariant error',
                          f'`{path}` fails derived-field checks: '
                          + ', '.join(f'{k} ({v} rows)' for k, v in failed.items()) + '.',
                          recovery_for(path))
    problems = []
    if quality['processed_rows'] != len(d):
        problems.append(f"quality report rows {quality['processed_rows']:,} != loaded rows {len(d):,}")
    if quality['processed'].get('columns') not in (None, len(d.columns)):
        problems.append('quality report column count differs from loaded file')
    if quality['source']['sha256'] != EXPECTED_SHA256:
        problems.append('quality report source hash differs from the approved source contract')
    maximum = d['offense_date'].max()
    if pd.notna(maximum) and str(maximum) != str(pd.Timestamp(quality['maximum_offense_date'])):
        problems.append('quality report maximum offense date differs from loaded data')
    if problems:
        raise SchemaError('Metadata consistency error', '; '.join(problems) + '.',
                          recovery_for('reports/phase2/data_quality.json'))
    return checks
