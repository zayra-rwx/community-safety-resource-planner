"""Worklist CSV (exactly T) and JSON metadata. No offense-level data is exported."""
import json
from datetime import datetime, timezone

import pandas as pd

from . import settings
from .filtering import filter_state

FORBIDDEN_EXPORT_COLUMNS = {'UniqueNIBRNo', 'CaseNo', 'LOCATION', 'LAT', 'LON', 'LAT_source', 'LON_source'}


def worklist_frame(overview):
    """T in its current table order with all 15 backend columns, unrounded."""
    frame = overview[settings.RANKED_COLUMNS].copy()
    frame['RPT Dist No'] = frame['RPT Dist No'].astype(str)
    for col in ['Recent period start', 'Recent period end']:
        frame[col] = pd.to_datetime(frame[col]).dt.strftime('%Y-%m-%d')
    return frame


def worklist_csv(overview):
    """UTF-8 CSV bytes. Import the 'RPT Dist No' column as text to keep leading zeros."""
    return worklist_frame(overview).to_csv(index=False, lineterminator='\n').encode('utf-8')


def worklist_metadata(*, meta, filters, resolved, min_active, top_n, sort_label, counts, recent):
    """JSON metadata bytes describing exactly how T was produced."""
    start, end = recent
    doc = {
        'title': settings.APP_TITLE,
        'exported_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'worklist_file_note': ('CSV rows are exactly the overview table (T) in its displayed sort order, '
                               'unrounded. Import "RPT Dist No" as text to retain leading zeros.'),
        'source': {'filename': meta['source_filename'], 'sha256': meta['source_sha256']},
        'processed_file': {'path': meta['processed_file'], 'bytes': meta['processed_bytes'],
                           'sha256': meta['processed_sha256'], 'modified_utc': meta['processed_modified_utc'],
                           'rows': meta['rows'], 'columns': meta['columns']},
        'app_version': meta['app_version'],
        'code_revision': meta['code_revision'],
        'data_through': meta['data_through'],
        'resolved_dates': {'start': resolved[0], 'end': resolved[1]},
        'filters': filter_state(filters),
        'minimum_active_months': min_active,
        'top_n': top_n,
        'table_sort': sort_label,
        'scope_counts': {'U_scoring_universe_districts': counts['U'],
                         'E_eligible_display_districts': counts['E'],
                         'T_worklist_districts': counts['T']},
        'recent_period': {'start': None if start is None else pd.Timestamp(start).date().isoformat(),
                          'end': None if end is None else pd.Timestamp(end).date().isoformat(),
                          'label': None if start is not None else 'No complete months'},
        'definitions': {
            'nighttime': settings.NIGHT_DEFINITION,
            'priority_score': settings.SCORE_FORMULA,
            'percentile_method': settings.PERCENTILE_METHOD,
            'persistence_rate': 'Active months / eligible months (zero when no eligible months)',
            'average_monthly': 'Nighttime reported offenses / eligible months',
            'recent': 'Distinct nighttime offenses in the latest up to three complete selected calendar months',
            'ranking_order': ('Score desc, nighttime count desc, persistence desc, numeric district asc '
                              '(nonnumeric last), then district string asc'),
            'scope_order': ('U = all districts after non-district filters (ranks/scores); E = U limited to the '
                            'district selection and minimum active months; T = top N of E by original rank, '
                            'then table sort'),
        },
        'coordinate_rules': settings.COORDINATE_RULE,
        'streetlight_statement': settings.STREETLIGHT_TEXT,
        'interpretation': settings.WARNING_TEXT,
    }
    return (json.dumps(doc, indent=2) + '\n').encode('utf-8')
