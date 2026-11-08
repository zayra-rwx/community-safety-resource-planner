import pandas as pd

from src.dashboard import adapters, export, mapping, settings


def frame(rows):
    return pd.DataFrame(rows, columns=['RPT Dist No', 'LOCATION', 'in_analysis_scope'])


def test_most_common_street_drops_block_numbers_and_intersections():
    d = frame([('0182', '1200 S Figueroa St', True), ('0182', '900 S Figueroa St', True),
               ('0182', '1200 1/2 S Hope St', True), ('0182', 'Main St & 1st St', True),
               ('0182', 'Main St & 1st St', True), ('0182', 'Main St & 1st St', True)])
    assert adapters.district_streets(d) == {'0182': 'S Figueroa St'}


def test_street_ties_are_deterministic_and_scope_is_respected():
    d = frame([('0101', '1 B St', True), ('0101', '2 A St', True), ('0101', '3 C St', False),
               ('0101', '4 C St', False), ('0102', '0102', True), ('06', '5 Vine St', True)])
    assert adapters.district_streets(d) == {'0101': 'A St'}


def test_label_formats():
    assert adapters.district_label('0182', 'Central') == '0182 · Central'
    assert adapters.district_label('0182', 'Central', 1, 'S Figueroa St') == '0182 · Central · near S Figueroa St (rank 1)'
    assert adapters.district_label('06', 'Hollywood') == '06 · Hollywood · area-level code'
    assert adapters.district_label('0102', None) == '0102 · Unknown'


def test_street_labels_stay_out_of_map_and_export():
    mapped = pd.DataFrame({'LAT': [34.0411], 'LON': [-118.2611], 'UniqueNIBRNo': ['X1'], 'RPT Dist No': ['0182'],
                           'offense_month': [pd.Timestamp('2026-01-01')], 'LOCATION': ['1200 S Figueroa St']})
    assert 'Figueroa' not in mapping.generalize(mapped).to_csv()
    assert 'Figueroa' not in mapping.map_figure(mapping.generalize(mapped), 'Title', 'Period').to_json()
    ranked = pd.DataFrame([{column: 1 for column in settings.RANKED_COLUMNS}])
    ranked['RPT Dist No'], ranked['AREA NAME'] = '0182', 'Central'
    assert b'Figueroa' not in export.worklist_csv(ranked)


def test_map_view_ignores_stray_points_but_counts_them():
    cells = pd.DataFrame({'lat': [34.04] * 99 + [33.70], 'lon': [-118.26] * 99 + [-118.90], 'offenses': [10] * 100})
    opening = mapping.view(cells)
    assert opening['lat'] == 34.04 and opening['lon'] == -118.26 and opening['zoom'] == 14
    assert opening['outside'] == 10


def test_partial_months_mark_only_incomplete_endpoints():
    months = adapters.partial_months(pd.Timestamp('2025-02-15'), pd.Timestamp('2025-04-30'))
    assert months == [pd.Timestamp('2025-02-01')]
    months = adapters.partial_months(pd.Timestamp('2025-01-01'), pd.Timestamp('2025-03-19'))
    assert months == [pd.Timestamp('2025-03-01')]
    assert adapters.partial_months(pd.Timestamp('2025-01-01'), pd.Timestamp('2025-01-31')) == []
