from dataclasses import replace

import pandas as pd
import pytest

from src.clean_data import clean_offenses, verify_source
from src.config import SOURCE_COLUMNS
from src.analysis import (Filters, category_summary, compare_districts,
                          count_nighttime_offenses, eligible_months, filter_offenses,
                          monthly_counts, nighttime_offenses, ranked_districts, recent_period)


def source(rows):
    defaults = dict.fromkeys(SOURCE_COLUMNS, pd.NA)
    defaults.update({'CaseNo': 'shared-case', 'Date OCC': '2025 Jan 01 12:00:00 AM',
                     'Time OCC': '1800', 'RPT Dist No': '0101', 'AREA NAME': 'Central',
                     'NIBR Code': '23A', 'NIBR Description': 'Theft', 'Crime Against': 'Property',
                     'Premise Desc': 'Street', 'LAT': '34.05', 'LON': '-118.25'})
    return pd.DataFrame([dict(defaults, UniqueNIBRNo=str(i), **row) for i, row in enumerate(rows)], dtype='string')


def cleaned(rows):
    return clean_offenses(source(rows))[0]


@pytest.mark.parametrize('time,night,midnight,valid', [
    ('1800', True, False, True), ('2359', True, False, True),
    ('0000', True, True, True), ('0559', True, False, True),
    ('0600', False, False, True), ('1759', False, False, True),
    ('0', True, True, True), ('559', True, False, True),
    ('2400', False, False, False), ('2360', False, False, False),
    ('1261', False, False, False), ('-1', False, False, False),
    ('18:00', False, False, False), ('1800.0', False, False, False),
    (None, False, False, False), ('', False, False, False),
])
def test_time_boundaries(time, night, midnight, valid):
    d = cleaned([{'Time OCC': time}])
    assert bool(d.loc[0, 'is_night']) == night
    assert bool(d.loc[0, 'is_midnight_code']) == midnight
    assert bool(d.loc[0, 'has_valid_time']) == valid
    if midnight:
        assert d.loc[0, 'Time OCC'] == '0000'
    if not valid:
        assert pd.isna(d.loc[0, 'offense_hour'])
        assert count_nighttime_offenses(d) == 0


def test_duplicate_and_case_rules():
    raw = source([{}, {}])
    raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
    before = raw.copy(deep=True)
    d, q = clean_offenses(raw)
    assert len(d) == 2
    assert q['exact_duplicates_removed'] == 1
    assert q['repeated_case_rows_retained'] == 2
    assert count_nighttime_offenses(d) == 2
    pd.testing.assert_frame_equal(raw, before)


def test_conflicting_offense_ids_retained_and_require_review():
    raw = source([{}, {'Time OCC': '1900'}])
    raw['UniqueNIBRNo'] = 'same'
    d, q = clean_offenses(raw)
    assert len(d) == 2 and q['repeated_offense_id_rows'] == 2
    assert count_nighttime_offenses(d) == 1
    with pytest.raises(ValueError, match='requires review'):
        ranked_districts(d)


@pytest.mark.parametrize('lat,lon', [(None, '-118.25'), ('0', '0'),
                                   ('bad', '-118.25'), ('40', '-74')])
def test_unmapped_still_counts(lat, lon):
    d = cleaned([{'LAT': lat, 'LON': lon}])
    assert count_nighttime_offenses(d) == 1
    assert count_nighttime_offenses(d, mapped_only=True) == 0
    assert nighttime_offenses(d, mapped_only=True).empty
    assert ranked_districts(d).iloc[0]['Nighttime reported offenses'] == 1


@pytest.fixture
def four_months():
    return cleaned([
        {}, {'Date OCC': '2025 Feb 01 12:00:00 AM'},
        {'Date OCC': '2025 Apr 01 12:00:00 AM'},
        {'RPT Dist No': '0102'},
        {'RPT Dist No': '0103', 'Date OCC': '2025 Apr 30 11:59:00 PM', 'Time OCC': '1200'},
    ])


def test_zero_months_persistence_weights_and_recent(four_months):
    d = four_months
    m = monthly_counts(d)
    assert len(m) == 12
    assert m.loc[m['RPT Dist No'].eq('0101'), 'nighttime_offenses'].tolist() == [1, 1, 0, 1]
    r = ranked_districts(d).set_index('RPT Dist No')
    assert r.loc['0101', 'Persistence rate'] == .75
    assert r.loc['0101', 'Eligible months'] == 4
    assert r.loc['0101', 'Average monthly nighttime offenses'] == .75
    assert r.loc['0101', 'Recent nighttime offenses'] == 2
    assert r.loc['0103', 'Priority score'] == 0
    expected = (0.6 * r['Frequency percentile'] + 0.4 * r['Persistence percentile']) * 100
    assert r.loc['0101', 'Priority score'] == expected.loc['0101']
    assert r.loc['0102', 'Priority score'] == expected.loc['0102']
    assert recent_period(d) == (pd.Timestamp('2025-02-01'), pd.Timestamp('2025-04-30'))


def test_different_frequency_and_persistence_weights():
    d = cleaned([{}, {}, {}, {'RPT Dist No': '0102'},
                 {'RPT Dist No': '0102', 'Date OCC': '2025 Feb 28 12:00:00 AM'}])
    r = ranked_districts(d).set_index('RPT Dist No')
    assert r.loc['0101', 'Priority score'] == 80  # 0.6*1 + 0.4*0.5
    assert r.loc['0102', 'Priority score'] == 70  # 0.6*0.5 + 0.4*1


def test_selection_preserves_universe_scores_and_rank(four_months):
    full = ranked_districts(four_months)
    selected = ranked_districts(four_months, Filters(districts=('0102',)))
    pd.testing.assert_frame_equal(selected, full.loc[full['RPT Dist No'].eq('0102')].reset_index(drop=True))
    result = compare_districts(four_months, ['0101', '0102'])
    assert len(result['districts']) == 2 and len(result['monthly']) == 8


def test_tie_order_is_numeric_and_deterministic():
    d = cleaned([{'RPT Dist No': '10'}, {'RPT Dist No': '2'}])
    a = ranked_districts(d)
    b = ranked_districts(d.iloc[::-1])
    pd.testing.assert_frame_equal(a, b)
    assert a['RPT Dist No'].tolist() == ['2', '10']
    assert a['Priority score'].tolist() == [75, 75]


@pytest.mark.parametrize('attribute,value', [('areas', 'Central'), ('districts', '0101'),
    ('codes', '23A'), ('descriptions', 'Theft'), ('crime_against', 'Property'), ('premises', 'Street')])
def test_categorical_filters(four_months, attribute, value):
    f = replace(Filters(), **{attribute: (value,)})
    assert not filter_offenses(four_months, f).empty
    assert filter_offenses(four_months, replace(f, **{attribute: ('absent',)})).empty


def test_dates_scope_inclusive_and_recent_partial_months(four_months):
    f = Filters(start='2025-02-01', end='2025-04-01')
    assert count_nighttime_offenses(four_months, f) == 2
    assert len(eligible_months(f.start, f.end)) == 3
    assert recent_period(four_months, f) == (pd.Timestamp('2025-02-01'), pd.Timestamp('2025-03-31'))
    assert recent_period(four_months, Filters(start='2025-04-02')) == (None, None)
    d = cleaned([{'Date OCC': '2024 Dec 31 12:00:00 AM'}, {'Date OCC': 'bad'}, {}])
    assert len(d) == 3 and count_nighttime_offenses(d) == 1


@pytest.mark.parametrize('f', [Filters(areas=('absent',)), Filters(districts=()),
    Filters(start='2026-01-01'), Filters(start='2025-04-01', end='2025-01-01')])
def test_empty_outputs(four_months, f):
    assert count_nighttime_offenses(four_months, f) == 0
    assert ranked_districts(four_months, f).empty
    assert monthly_counts(four_months, f).empty
    assert category_summary(four_months, filters=f).empty


def test_empty_input_and_missing_dates():
    d = cleaned([{'Date OCC': 'bad'}])
    assert ranked_districts(d).empty
    assert monthly_counts(d).empty
    assert ranked_districts(d.iloc[:0]).empty


def test_summary_unknown_and_no_input_mutation(four_months):
    d = four_months.copy()
    d.loc[0, 'Premise Desc'] = pd.NA
    before = d.copy(deep=True)
    summary = category_summary(d, 'Premise Desc')
    assert summary.set_index('Premise Desc').loc['Unknown', 'nighttime_offenses'] == 1
    ranked_districts(d)
    monthly_counts(d)
    pd.testing.assert_frame_equal(d, before)


def test_bad_source_stops_before_outputs(tmp_path):
    p = tmp_path / 'wrong.csv'
    p.write_text('a,b\n1,2\n')
    with pytest.raises(ValueError):
        verify_source(p)
