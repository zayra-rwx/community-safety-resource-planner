"""Reconcile major backend outputs against the full canonical data."""
import json
from dataclasses import replace

import pandas as pd

from .analysis import (Filters, load_processed, ranked_districts, monthly_counts,
                       nighttime_offenses, count_nighttime_offenses, category_summary,
                       compare_districts, filter_offenses, recent_period)
from .config import REPORTS
from .clean_data import verify_source


def main():
    source = verify_source()
    d = load_processed()
    rank = ranked_districts(d)
    monthly = monthly_counts(d)
    night = nighttime_offenses(d)
    mapped = nighttime_offenses(d, mapped_only=True)
    quality = json.loads((REPORTS / 'data_quality.json').read_text(encoding='utf-8'))
    assert len(d) == quality['processed_rows'] == source['data_rows']
    assert len(night) == quality['qualifying_nighttime_records']
    assert len(mapped) == quality['qualifying_mapped_nighttime_records']
    assert rank['Nighttime reported offenses'].sum() == night['UniqueNIBRNo'].nunique()
    assert rank['Valid mapped nighttime offenses'].sum() == mapped['UniqueNIBRNo'].nunique()
    assert monthly['nighttime_offenses'].sum() == len(night)
    assert len(monthly) == len(rank) * int(rank['Eligible months'].iloc[0])
    for column in ['NIBR Description', 'Premise Desc']:
        assert category_summary(d, column)['nighttime_offenses'].sum() == len(night)
    chosen = tuple(rank.head(3)['RPT Dist No'])
    comparison = compare_districts(d, chosen)
    pd.testing.assert_frame_equal(comparison['districts'], rank.head(3))
    for attribute, column in [('areas', 'AREA NAME'), ('codes', 'NIBR Code'),
                              ('descriptions', 'NIBR Description'), ('crime_against', 'Crime Against'),
                              ('premises', 'Premise Desc')]:
        value = night[column].dropna().iloc[0]
        f = replace(Filters(), **{attribute: (value,)})
        filtered = filter_offenses(d, f)
        assert filtered[column].eq(value).all()
        table = ranked_districts(d, f)
        assert table['Nighttime reported offenses'].sum() == count_nighttime_offenses(d, f)
    assert ranked_districts(d, Filters(areas=('__absent__',))).empty
    recent = recent_period(d)
    expected_recent = night.loc[night['offense_date'].between(*recent), 'UniqueNIBRNo'].nunique()
    assert rank['Recent nighttime offenses'].sum() == expected_recent
    rank.to_csv(REPORTS / 'district_ranking.csv', index=False)
    comparison['monthly'].to_csv(REPORTS / 'example_comparison_monthly.csv', index=False)
    category_summary(d).to_csv(REPORTS / 'offense_summary.csv', index=False)
    category_summary(d, 'Premise Desc').to_csv(REPORTS / 'premise_summary.csv', index=False)
    report = dict(status='passed', source_sha256=source['sha256'], processed_rows=len(d),
                  districts=len(rank), district_month_rows=len(monthly),
                  eligible_months=int(rank['Eligible months'].iloc[0]),
                  nighttime_offenses=len(night), mapped_nighttime_offenses=len(mapped),
                  recent_start=str(recent[0].date()), recent_end=str(recent[1].date()),
                  recent_nighttime_offenses=int(expected_recent),
                  checks='Full-data count, monthly, coverage, category, filter, comparison and recent-period reconciliations passed',
                  spatial='Unavailable: approved streetlight GIS input absent')
    (REPORTS / 'backend_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    print(rank.head(5).to_string(index=False))


if __name__ == '__main__':
    main()
