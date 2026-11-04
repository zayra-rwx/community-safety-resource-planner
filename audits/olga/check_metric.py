"""Independent priority-score audit of the committed Phase 2 implementation.

Run from the repository root: .venv/Scripts/python.exe audits/olga/check_metric.py
No production helper is used by independent(); production imports occur only in
the comparison stage. Generated evidence contains aggregates, never raw records.
"""
from collections import Counter
from datetime import date
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BASE = '87a892a392727cfaff176d3c0fbbf6019a60eb4a'
OUT = Path(__file__).resolve().parent


def independent(data, start='2025-01-01', end='2026-09-19', verbose=False):
    """Derive dates and time eligibility anew; explicit average-rank arithmetic."""
    d = data.copy()
    dates = pd.to_datetime(d['Date OCC'], errors='coerce').dt.normalize()
    start = max(pd.Timestamp(start), pd.Timestamp('2025-01-01'))
    end = min(pd.Timestamp(end), dates.max())
    months = max(0, (end.year - start.year) * 12 + end.month - start.month + 1) if end >= start else 0
    counts = {'input_rows': len(d)}
    d = d.loc[dates.between(start, end)].copy()
    d['_date'] = dates.loc[d.index]
    counts['after_inclusive_dates'] = len(d)
    # The scoring universe includes represented daytime-only districts.
    districts = sorted(d['RPT Dist No'].dropna().unique())
    counts['universe_districts_before_night_filter'] = len(districts)
    d = d.loc[d['RPT Dist No'].notna()]
    counts['after_nonmissing_district'] = len(d)
    d = d.loc[d['UniqueNIBRNo'].notna()]
    counts['after_nonmissing_offense_id'] = len(d)
    time_text = d['Time OCC'].astype('string').str.zfill(4)
    valid = time_text.str.fullmatch(r'\d{4}').fillna(False)
    hour = pd.to_numeric(time_text.str[:2], errors='coerce')
    minute = pd.to_numeric(time_text.str[2:], errors='coerce')
    valid &= hour.between(0, 23) & minute.between(0, 59)
    counts['after_valid_hhmm'] = int(valid.sum())
    night = d.loc[valid & (hour.ge(18) | hour.lt(6))].copy()
    counts['after_nighttime_1800_through_0559'] = len(night)
    counts['distinct_nighttime_ids'] = night['UniqueNIBRNo'].nunique()
    counts['coordinates_filter'] = 'Not applied: unmapped offenses remain eligible.'
    assert not night['UniqueNIBRNo'].duplicated().any(), 'Conflicting IDs need attribution review'
    offense_sets = {district: set() for district in districts}
    month_sets = {district: set() for district in districts}
    for district, identifier, day in zip(night['RPT Dist No'], night['UniqueNIBRNo'], night['_date']):
        offense_sets[district].add(identifier)
        month_sets[district].add((day.year, day.month))
    frequencies = {key: len(value) for key, value in offense_sets.items()}
    active = {key: len(value) for key, value in month_sets.items()}
    persistence = {key: active[key] / months if months else 0.0 for key in districts}

    def average_ranks(values):
        histogram = Counter(values.values())
        before = 0
        ranks = {}
        for value, tied in sorted(histogram.items()):
            # Positions before+1 through before+tied; use their arithmetic mean.
            ranks[value] = before + (tied + 1) / 2
            before += tied
        return {key: ranks[value] for key, value in values.items()}

    fr, pr = average_ranks(frequencies), average_ranks(persistence)
    n = len(districts)
    result = {}
    for key in districts:
        fp, pp = fr[key] / n, pr[key] / n
        score = 100 * (0.6 * fp + 0.4 * pp) if frequencies[key] else 0.0
        result[key] = {'nighttime': frequencies[key], 'active_months': active[key], 'eligible_months': months,
                       'persistence': persistence[key], 'frequency_rank_numerator': fr[key],
                       'persistence_rank_numerator': pr[key], 'percentile_denominator': n,
                       'frequency_percentile': fp, 'persistence_percentile': pp, 'score': score}
    if verbose:
        print('INDEPENDENT FILTER COUNTS', json.dumps(counts, indent=2, default=int))
    return result, counts


def fixture():
    # Expectations recorded before execution: A and B each 2/3 months, each
    # frequency/persistence rank 2.5 of 3 => score 250/3. C daytime-only => 0.
    records = [
        ('a1', 'A', '2025-01-01', '1800'),
        ('a2', 'A', '2025-03-31', '0559'),
        ('b1', 'B', '2025-01-01', '0000'),
        ('b2', 'B', '2025-03-31', '2359'),
        ('c1', 'C', '2025-03-31', '0600'),
        ('a3', 'A', '2025-02-01', '1759'),
        ('a4', 'A', '2025-02-01', '2400'),
        ('old', 'A', '2024-12-31', '1800'),
        ('no-district', None, '2025-02-01', '1800'),
        (None, 'A', '2025-02-01', '1800'),
    ]
    d = pd.DataFrame(records, columns=['UniqueNIBRNo', 'RPT Dist No', 'Date OCC', 'Time OCC'])
    print('SMALL CASE: expected before execution A=B=83.33333333333334; C=0; active/eligible=2/3')
    print(d.to_string(index=False))
    result, counts = independent(d, end='2025-03-31')
    assert abs(result['A']['score'] - 250 / 3) < 1e-12
    assert result['A'] == result['B']
    assert result['A']['active_months'] == 2 and result['A']['eligible_months'] == 3
    assert result['C']['score'] == 0 and counts['distinct_nighttime_ids'] == 4
    # Build the equivalent production-shaped frame directly; do not call cleaner.
    p = d.copy()
    p['offense_date'] = pd.to_datetime(p['Date OCC'])
    p['offense_month'] = p['offense_date'].dt.to_period('M').dt.to_timestamp()
    p['is_night'] = [True, True, True, True, False, False, False, True, True, True]
    p['has_valid_coordinates'] = False
    p['AREA NAME'] = 'Synthetic'
    from src.analysis import ranked_districts, Filters
    production = ranked_districts(p, Filters(end='2025-03-31')).set_index('RPT Dist No')
    for key in result:
        assert abs(production.loc[key, 'Priority score'] - result[key]['score']) < 1e-12
    print('SMALL CASE actual:', json.dumps(result, indent=2))
    # Remove the daytime-only district: equal positive districts rank 1.5/2.
    alternative, _ = independent(d.loc[d['RPT Dist No'].ne('C')], end='2025-03-31')
    assert alternative['A']['score'] == 75
    print('ASSUMPTION CHECK: remove daytime-only C -> A=B=75; original -> A=B=83.33333333333334')
    two = p.loc[p['RPT Dist No'].ne('C')]
    assert (ranked_districts(two)['Priority score'] == 75).all()
    single = p.loc[p['RPT Dist No'].eq('A')]
    assert ranked_districts(single).iloc[0]['Priority score'] == 100
    print('PRODUCTION boundary checks: two equal positive districts=75 each; single positive district=100; PASS')
    return result


def main():
    print('Audited base:', BASE)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == BASE
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    checked = [p for p in tracked if p.startswith(('src/', 'tests/', 'reports/phase2/')) or p in ['BUILD_SPEC.md', 'README.md', 'requirements-phase2.txt', 'data/processed/lapd_nibrs_offenses.parquet']]
    hashes = {}
    for name in checked:
        actual = subprocess.check_output(['git', 'hash-object', name], cwd=ROOT, text=True).strip()
        expected = subprocess.check_output(['git', 'rev-parse', BASE + ':' + name], cwd=ROOT, text=True).strip()
        assert actual == expected, f'Baseline differs: {name}'
        hashes[name] = actual
    path = ROOT / 'data/processed/lapd_nibrs_offenses.parquet'
    with path.open('rb') as handle:
        data_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
    print('Processed SHA256:', data_hash)
    print('Python:', sys.version.split()[0])
    versions = {p: importlib.metadata.version(p) for p in ['pandas', 'pyarrow', 'pytest']}
    print('Versions:', json.dumps(versions))
    data = pd.read_parquet(path)
    result, counts = independent(data, verbose=True)
    from src.analysis import ranked_districts, Filters
    production = ranked_districts(data, Filters(start='2025-01-01', end='2026-09-19'))
    differences = []
    for _, row in production.iterrows():
        value = result[row['RPT Dist No']]
        assert value['nighttime'] == row['Nighttime reported offenses']
        assert value['active_months'] == row['Active months']
        assert value['eligible_months'] == row['Eligible months']
        differences.append(abs(value['score'] - row['Priority score']))
    assert max(differences) <= 1e-10
    selected = result['0182']
    target = production.set_index('RPT Dist No').loc['0182']
    print('DISTRICT 0182', json.dumps(selected, indent=2))
    tied = sum(v['persistence'] == selected['persistence'] for v in result.values())
    lower = sum(v['persistence'] < selected['persistence'] for v in result.values())
    print(f'Persistence tie: {lower} lower districts; {tied} tied; average rank={lower}+({tied}+1)/2')
    print('Production unrounded:', repr(float(target['Priority score'])))
    print('CLI displayed (6 decimals):', f"{selected['score']:.6f}")
    print('Selected difference:', selected['score'] - float(target['Priority score']))
    print('Maximum difference across all districts:', max(differences))
    assert production.iloc[0]['RPT Dist No'] == '0182'
    subset = ranked_districts(data, Filters(districts=('0182',)))
    assert subset.iloc[0]['Priority score'] == target['Priority score'] and subset.iloc[0]['Rank'] == 1
    print('District selection preserves original score and rank: PASS')
    print('If max-rank were used for the top persistence tie, district 0182 would score 100 instead.')
    small = fixture()
    manifest = {'audited_commit': BASE, 'tracked_git_blobs': hashes, 'processed_sha256': data_hash,
                'python': sys.version.split()[0], 'versions': versions,
                'excluded_unfinished_files': ['pytest.ini', 'requirements-phase3.txt', 'src/dashboard.py'],
                'scope': 'Committed CLI/backend only; audit code is new supporting evidence.'}
    (OUT / 'version.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (OUT / 'numeric_results.json').write_text(json.dumps({'district_0182': selected, 'filter_counts': counts,
        'maximum_absolute_difference': max(differences), 'persistence_lower': lower, 'persistence_tied': tied,
        'small_case': small}, indent=2, default=int) + '\n', encoding='utf-8')
    print('ALL NUMERIC ASSERTIONS PASSED')


if __name__ == '__main__':
    main()
