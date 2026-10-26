"""Reusable full-data analysis. No UI and no hidden global dataframes."""
import argparse
from dataclasses import dataclass, replace

import pandas as pd

from .config import PROCESSED, START_DATE, FREQUENCY_WEIGHT, PERSISTENCE_WEIGHT


@dataclass(frozen=True)
class Filters:
    start: str | None = None
    end: str | None = None
    areas: tuple[str, ...] | None = None
    districts: tuple[str, ...] | None = None
    codes: tuple[str, ...] | None = None
    descriptions: tuple[str, ...] | None = None
    crime_against: tuple[str, ...] | None = None
    premises: tuple[str, ...] | None = None


def load_processed(path=PROCESSED):
    d = pd.read_parquet(path)
    required = {'UniqueNIBRNo', 'offense_date', 'offense_month', 'is_night',
                'has_valid_coordinates', 'RPT Dist No', 'AREA NAME', 'NIBR Code',
                'NIBR Description', 'Crime Against', 'Premise Desc'}
    if required - set(d.columns):
        raise ValueError(f'Missing processed columns: {sorted(required - set(d.columns))}')
    return d


def selected_interval(d, filters=Filters()):
    start = max(pd.Timestamp(filters.start or START_DATE).normalize(), pd.Timestamp(START_DATE))
    maximum = d['offense_date'].max()
    end = pd.Timestamp(filters.end).normalize() if filters.end else maximum
    if pd.notna(maximum) and pd.notna(end):
        end = min(end, maximum.normalize())
    return start, end


def eligible_months(start, end):
    if pd.isna(start) or pd.isna(end) or pd.Timestamp(end) < pd.Timestamp(start):
        return pd.DatetimeIndex([], dtype='datetime64[ns]')
    return pd.period_range(start, end, freq='M').to_timestamp()


def filter_offenses(d, filters=Filters(), *, include_districts=True):
    start, end = selected_interval(d, filters)
    mask = d['offense_date'].between(start, end) if pd.notna(end) else pd.Series(False, index=d.index)
    mappings = [('areas', 'AREA NAME'), ('codes', 'NIBR Code'),
                ('descriptions', 'NIBR Description'), ('crime_against', 'Crime Against'),
                ('premises', 'Premise Desc')]
    if include_districts:
        mappings.append(('districts', 'RPT Dist No'))
    for attribute, column in mappings:
        values = getattr(filters, attribute)
        if values is not None:
            mask &= d[column].isin(values)
    return d.loc[mask].copy()


def nighttime_offenses(d, filters=Filters(), *, mapped_only=False):
    selected = filter_offenses(d, filters)
    mask = (selected['is_night'] & selected['RPT Dist No'].notna()
            & selected['UniqueNIBRNo'].notna())
    if mapped_only:
        mask &= selected['has_valid_coordinates']
    return selected.loc[mask].copy()


def count_nighttime_offenses(d, filters=Filters(), *, mapped_only=False):
    return int(nighttime_offenses(d, filters, mapped_only=mapped_only)['UniqueNIBRNo'].nunique())


def _assert_consistent_ids(d):
    # Repeated nonidentical IDs are retained by cleaning but need adjudication
    # before district/month/category attribution is safe.
    if d['UniqueNIBRNo'].dropna().duplicated().any():
        raise ValueError('Repeated UniqueNIBRNo requires review before analysis; records retained in processed data')


def monthly_counts(d, filters=Filters()):
    start, end = selected_interval(d, filters)
    selected = filter_offenses(d, filters)
    night = nighttime_offenses(d, filters)
    _assert_consistent_ids(night)
    districts = sorted(selected['RPT Dist No'].dropna().unique())
    index = pd.MultiIndex.from_product([districts, eligible_months(start, end)],
                                      names=['RPT Dist No', 'offense_month'])
    counts = night.groupby(['RPT Dist No', 'offense_month'])['UniqueNIBRNo'].nunique()
    return counts.reindex(index, fill_value=0).rename('nighttime_offenses').reset_index()


def recent_period(d, filters=Filters()):
    """Latest up to three full months contained in the selected available interval.

    Availability uses canonical maximum date before categorical/district filters,
    so sparse category selections never redefine the comparison period.
    """
    start, end = selected_interval(d, filters)
    complete = [m for m in eligible_months(start, end)
                if m >= start and m + pd.offsets.MonthEnd(0) <= end]
    if not complete:
        return None, None
    return complete[-3:][0], complete[-1] + pd.offsets.MonthEnd(0)


def ranked_districts(d, filters=Filters()):
    # District selection is applied only after scoring and ranking the universe.
    universe_filters = replace(filters, districts=None)
    selected = filter_offenses(d, universe_filters)
    night = nighttime_offenses(d, universe_filters)
    _assert_consistent_ids(night)
    districts = sorted(selected['RPT Dist No'].dropna().unique())
    table = pd.DataFrame(index=pd.Index(districts, name='RPT Dist No'))
    table['AREA NAME'] = selected.groupby('RPT Dist No')['AREA NAME'].agg(
        lambda x: ' / '.join(sorted(x.dropna().unique())))
    table['Nighttime reported offenses'] = night.groupby('RPT Dist No')['UniqueNIBRNo'].nunique()
    monthly = monthly_counts(d, universe_filters)
    table['Active months'] = monthly.loc[monthly['nighttime_offenses'].gt(0)].groupby('RPT Dist No').size()
    table[['Nighttime reported offenses', 'Active months']] = table[
        ['Nighttime reported offenses', 'Active months']].fillna(0).astype('int64')
    months = len(eligible_months(*selected_interval(d, filters)))
    table['Eligible months'] = months
    table['Persistence rate'] = table['Active months'] / months if months else 0.0
    table['Average monthly nighttime offenses'] = table['Nighttime reported offenses'] / months if months else 0.0
    recent_start, recent_end = recent_period(d, filters)
    recent = night.loc[night['offense_date'].between(recent_start, recent_end)] if recent_start is not None else night.iloc[:0]
    table['Recent nighttime offenses'] = recent.groupby('RPT Dist No')['UniqueNIBRNo'].nunique()
    table['Valid mapped nighttime offenses'] = night.loc[night['has_valid_coordinates']].groupby('RPT Dist No')['UniqueNIBRNo'].nunique()
    for col in ['Recent nighttime offenses', 'Valid mapped nighttime offenses']:
        table[col] = table[col].fillna(0).astype('int64')
    table['Frequency percentile'] = table['Nighttime reported offenses'].rank(method='average', pct=True)
    table['Persistence percentile'] = table['Persistence rate'].rank(method='average', pct=True)
    table['Priority score'] = 100 * (FREQUENCY_WEIGHT * table['Frequency percentile']
                                     + PERSISTENCE_WEIGHT * table['Persistence percentile'])
    table.loc[table['Nighttime reported offenses'].eq(0), 'Priority score'] = 0.0
    table = table.reset_index()
    # Reporting districts are numeric codes stored as strings to preserve source formatting.
    table['_district_order'] = pd.to_numeric(table['RPT Dist No'], errors='coerce')
    table = table.sort_values(['Priority score', 'Nighttime reported offenses', 'Persistence rate',
                               '_district_order', 'RPT Dist No'], ascending=[False, False, False, True, True])
    table['Rank'] = range(1, len(table) + 1)
    table['Recent period start'] = recent_start
    table['Recent period end'] = recent_end
    columns = ['Rank', 'RPT Dist No', 'AREA NAME', 'Priority score', 'Nighttime reported offenses',
               'Active months', 'Eligible months', 'Persistence rate', 'Average monthly nighttime offenses',
               'Recent nighttime offenses', 'Valid mapped nighttime offenses', 'Frequency percentile',
               'Persistence percentile', 'Recent period start', 'Recent period end']
    if filters.districts is not None:
        table = table.loc[table['RPT Dist No'].isin(filters.districts)]
    return table[columns].reset_index(drop=True)


def category_summary(d, column='NIBR Description', filters=Filters()):
    if column not in ['NIBR Description', 'Premise Desc']:
        raise ValueError('Summary column must be NIBR Description or Premise Desc')
    night = nighttime_offenses(d, filters)
    _assert_consistent_ids(night)
    # Missing values remain missing in data; "Unknown" is an output label only.
    night[column] = night[column].fillna('Unknown')
    return (night.groupby(column)['UniqueNIBRNo'].nunique().rename('nighttime_offenses')
            .reset_index().sort_values(['nighttime_offenses', column], ascending=[False, True]).reset_index(drop=True))


def compare_districts(d, districts, filters=Filters()):
    comparison_filters = replace(filters, districts=tuple(districts))
    return {'districts': ranked_districts(d, comparison_filters),
            'monthly': monthly_counts(d, comparison_filters)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start')
    parser.add_argument('--end')
    parser.add_argument('--top', type=int, default=10)
    args = parser.parse_args()
    d = load_processed()
    print(ranked_districts(d, Filters(start=args.start, end=args.end)).head(args.top).to_string(index=False))


if __name__ == '__main__':
    main()
