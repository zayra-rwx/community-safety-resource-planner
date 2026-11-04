"""Presentation adapters: build U/E/T scopes, KPIs, compositions and evidence.

Every metric comes from ``src.analysis``. These functions only select, reorder,
sum or label rows returned by the backend; they never rescore or rerank.

Scope order (BUILD_SPEC section 9):
  U = ranked_districts(full data, F with districts=None)
  E = U restricted to the district selection D, then Active months >= threshold
  T = top N of E by original rank, then reordered by the user's table sort
"""
from dataclasses import replace

import pandas as pd

from ..analysis import (category_summary, compare_districts, monthly_counts, nighttime_offenses, ranked_districts, recent_period)
from . import settings


# ---------------------------------------------------------------- scopes
def scoring_universe(d, filters):
    """U: complete ranked return for F (district selection removed)."""
    return ranked_districts(d, replace(filters, districts=None))


def eligible_scope(universe, districts, min_active_months):
    """E: rows of U for D (None = all, () = none) with Active months >= threshold.

    Scores and ranks are carried over unchanged from U.
    """
    rows = universe if districts is None else universe.loc[universe['RPT Dist No'].isin(districts)]
    return rows.loc[rows['Active months'] >= int(min_active_months)].reset_index(drop=True)


def top_n_value(top_n):
    return None if str(top_n) == 'All' else int(top_n)


def district_sort_key(series):
    """Numeric district ascending, nonnumeric last, then source string (backend convention)."""
    numeric = pd.to_numeric(series, errors='coerce')
    return numeric.fillna(float('inf'))


def overview_rows(eligible, top_n, sort_label=settings.DEFAULT_SORT):
    """T: top N of E by original rank, then reordered by the user's sort only."""
    n = top_n_value(top_n)
    members = eligible.sort_values('Rank', kind='stable')
    members = members if n is None else members.head(n)
    column, ascending = settings.SORT_OPTIONS[sort_label]
    if column == 'RPT Dist No':
        ordered = members.assign(_num=district_sort_key(members['RPT Dist No'])).sort_values(
            ['_num', 'RPT Dist No'], kind='stable').drop(columns='_num')
    else:
        ordered = members.sort_values([column, 'Rank'], ascending=[ascending, True], kind='stable')
    return ordered.reset_index(drop=True)


def scope_ids(frame):
    """Explicit district ID tuple for record calls (``()`` when empty)."""
    return tuple(frame['RPT Dist No'].astype(str))


# ---------------------------------------------------------------- KPIs
def coverage(mapped, total):
    """Mapped / total, or None (display N/A) when there is no denominator."""
    return None if not total else mapped / total


def kpi_summary(eligible):
    """KPIs over E (before top-N): sums, row count, unweighted mean persistence."""
    total = int(eligible['Nighttime reported offenses'].sum()) if len(eligible) else 0
    mapped = int(eligible['Valid mapped nighttime offenses'].sum()) if len(eligible) else 0
    return dict(nighttime=total, districts=int(len(eligible)),
                mean_persistence=float(eligible['Persistence rate'].mean()) if len(eligible) else 0.0,
                mapped=mapped, coverage=coverage(mapped, total))


# ---------------------------------------------------------------- labels
def area_label(value):
    return 'Unknown' if value is None or pd.isna(value) or str(value).strip() == '' else str(value)


def recent_label(start, end):
    if start is None or pd.isna(start):
        return 'No complete months'
    return f'{pd.Timestamp(start):%b %d, %Y} - {pd.Timestamp(end):%b %d, %Y}'


def period_label(start, end):
    if start is None or end is None or pd.isna(start) or pd.isna(end) or pd.Timestamp(end) < pd.Timestamp(start):
        return 'No valid period'
    return f'{pd.Timestamp(start):%b %d, %Y} - {pd.Timestamp(end):%b %d, %Y}'


def recent_for(d, filters):
    """Recent-period endpoints from dates/full-data availability only."""
    return recent_period(d, filters)


# ---------------------------------------------------------------- selection state
def reconcile(selected, choices):
    """Keep only selections still present in the current choices (order preserved)."""
    allowed = set(choices)
    return [s for s in selected if s in allowed]


def clamp_min_active(value, eligible_month_count):
    """Clamp the threshold to [1, eligible months]; None when the control must be disabled."""
    if not eligible_month_count:
        return None
    return max(1, min(int(value or 1), int(eligible_month_count)))


# ---------------------------------------------------------------- composition
def top_categories(summary, column, n=settings.TOP_CATEGORIES):
    """Top n rows in backend order plus one summed remainder row, with shares.

    The remainder label is distinct from any literal source label.
    """
    total = int(summary['nighttime_offenses'].sum()) if len(summary) else 0
    top = summary.head(n).copy()
    rest = summary.iloc[n:]
    top['is_remainder'] = False
    if len(rest):
        top = pd.concat([top, pd.DataFrame({column: [settings.OTHER_LABEL],
                                            'nighttime_offenses': [int(rest['nighttime_offenses'].sum())],
                                            'is_remainder': [True]})], ignore_index=True)
    top['share'] = top['nighttime_offenses'] / total if total else 0.0
    top['remaining_categories'] = [len(rest) if r else 0 for r in top['is_remainder']]
    return top.reset_index(drop=True)


# ---------------------------------------------------------------- evidence
def evidence(d, filters, district, universe):
    """All District Evidence inputs for one E district, from backend calls with F + (district,)."""
    f = replace(filters, districts=(district,))
    row = universe.loc[universe['RPT Dist No'].eq(district)]
    if row.empty:
        return None
    row = row.iloc[0]
    offenses = category_summary(d, 'NIBR Description', f)
    premises = category_summary(d, 'Premise Desc', f)
    return dict(
        row=row,
        monthly=monthly_counts(d, f),
        offenses=top_categories(offenses, 'NIBR Description'),
        premises=top_categories(premises, 'Premise Desc'),
        offense_categories=len(offenses),
        premise_categories=len(premises),
        coverage=coverage(int(row['Valid mapped nighttime offenses']), int(row['Nighttime reported offenses'])),
    )


def evidence_sentence(row, period):
    """Deterministic, non-causal summary sentence built from returned values."""
    count = int(row['Nighttime reported offenses'])
    active, eligible = int(row['Active months']), int(row['Eligible months'])
    noun = 'offense' if count == 1 else 'offenses'
    return (f"Reporting district {row['RPT Dist No']} ({area_label(row['AREA NAME'])}) had {count:,} "
            f"nighttime reported {noun} during {period}, with at least one in {active} of {eligible} "
            f"eligible calendar months. It holds original rank {int(row['Rank']):,} among all districts "
            "after non-district filters. This describes reported-offense patterns only, not lighting conditions.")


# ---------------------------------------------------------------- comparison
def comparison(d, filters, chosen, eligible):
    """compare_districts for 2-5 chosen E districts; raises ValueError otherwise."""
    chosen = list(dict.fromkeys(chosen))
    if not settings.COMPARE_MIN <= len(chosen) <= settings.COMPARE_MAX:
        raise ValueError(f'Choose {settings.COMPARE_MIN} to {settings.COMPARE_MAX} districts.')
    outside = set(chosen) - set(eligible['RPT Dist No'])
    if outside:
        raise ValueError('Comparison districts must come from the eligible display scope.')
    return compare_districts(d, chosen, filters)


# ---------------------------------------------------------------- map
def mapped_records(d, filters, district_ids):
    """Qualifying mapped nighttime records for an explicit district tuple (backend call)."""
    return nighttime_offenses(d, replace(filters, districts=tuple(district_ids)), mapped_only=True)
