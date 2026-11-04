"""Translate widget values into immutable backend ``Filters``.

Widget convention per categorical field: ``all_selected=True`` -> ``None`` (All,
including records whose category is missing); otherwise the explicit selection as a
tuple, so clearing every value gives ``()`` (no records), never silently All.
"""
from dataclasses import asdict, replace
from datetime import date

import pandas as pd

from ..analysis import Filters, selected_interval
from ..config import START_DATE
from .settings import CATEGORY_FILTERS


def category_value(all_selected, selection):
    return None if all_selected else tuple(str(v) for v in selection)


def build_filters(start, end, categories):
    """``categories`` maps Filters attribute -> (all_selected, selection)."""
    values = {attr: category_value(*categories.get(attr, (True, ())))
              for attr, _, _ in CATEGORY_FILTERS}
    as_text = lambda v: None if v is None else pd.Timestamp(v).date().isoformat()  # noqa: E731
    return Filters(start=as_text(start), end=as_text(end), **values)


def non_district(filters):
    """F: the same filters with district selection removed (scoring universe)."""
    return replace(filters, districts=None)


def date_bounds(full_max):
    """(min, max) selectable dates, or None when the data has no valid dates."""
    if full_max is None or pd.isna(full_max):
        return None
    low = pd.Timestamp(START_DATE).date()
    high = pd.Timestamp(full_max).date()
    return (low, high) if high >= low else None


def date_errors(start, end, bounds):
    """Reject reversed or out-of-scope inclusive date inputs. Empty list = valid."""
    if bounds is None:
        return ['No valid occurrence dates are available in the canonical data.']
    errors = []
    low, high = bounds
    if start is None or end is None:
        errors.append('Select both a start and an end date.')
        return errors
    if start < low or start > high:
        errors.append(f'Start date must be between {low:%B %d, %Y} and {high:%B %d, %Y}.')
    if end < low or end > high:
        errors.append(f'End date must be between {low:%B %d, %Y} and {high:%B %d, %Y}.')
    if start > end:
        errors.append('Start date is after end date; choose a start on or before the end.')
    return errors


def resolved_dates(d, filters):
    start, end = selected_interval(d, filters)
    fmt = lambda t: None if t is None or pd.isna(t) else pd.Timestamp(t).date().isoformat()  # noqa: E731
    return fmt(start), fmt(end)


def filter_state(filters):
    """JSON-friendly description of every filter state (All / none / values)."""
    out = {}
    for key, value in asdict(filters).items():
        if key in ('start', 'end'):
            out[key] = value
        elif value is None:
            out[key] = 'All (including missing categories)'
        elif len(value) == 0:
            out[key] = 'None selected (no records)'
        else:
            out[key] = list(value)
    return out


def source_options(d, column, data_max):
    """Actual nonmissing source values in the analysis window, sorted (no 'Unknown' label)."""
    if data_max is None or pd.isna(data_max):
        return []
    in_window = d['offense_date'].between(pd.Timestamp(START_DATE), pd.Timestamp(data_max))
    return sorted(d.loc[in_window, column].dropna().unique().tolist())


def to_date(value):
    return value if isinstance(value, date) else pd.Timestamp(value).date()
