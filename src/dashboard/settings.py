"""Display labels, defaults and fixed text for the Phase 3 dashboard.

Paths, the analysis start date, coordinate bounds and score weights are reused
from ``src.config``; they are not redefined here.
"""
from ..config import (FREQUENCY_WEIGHT, LAT_BOUNDS, LON_BOUNDS, PERSISTENCE_WEIGHT,
                      PROCESSED, REPORTS, ROOT, START_DATE)

APP_TITLE = 'Community Safety Resource Planner: Streetlight Assessment'
APP_VERSION = '0.3.0-mvp'
PURPOSE = ('Compare recurring nighttime reported-offense patterns across LAPD reporting '
           'districts to decide which districts should receive on-site lighting assessments first.')
WARNING_TEXT = ('Reported-offense patterns and mapped streetlights identify places for further '
                'assessment. They do not establish that lighting conditions caused offenses or that '
                'additional lighting will reduce them.')
STREETLIGHT_TEXT = ('Streetlight asset data was unavailable for this MVP. Rankings use reported-offense '
                    'frequency and persistence; the map shows approximate offense locations, not '
                    'measured lighting conditions.')
NIGHT_DEFINITION = ('Nighttime = recorded occurrence time 18:00 through 05:59 (valid HHMM only). '
                    'Recorded midnight (0000) is included and flagged separately.')

# Launch-required files (exactly these three).
QUALITY_PATH = REPORTS / 'data_quality.json'
DICTIONARY_PATH = REPORTS / 'data_dictionary.csv'
LAUNCH_FILES = (PROCESSED, QUALITY_PATH, DICTIONARY_PATH)

# Ranked-table contract (exact backend names).
DISPLAY_COLUMNS = ['Rank', 'RPT Dist No', 'AREA NAME', 'Priority score', 'Nighttime reported offenses',
                   'Active months', 'Eligible months', 'Persistence rate',
                   'Average monthly nighttime offenses', 'Recent nighttime offenses',
                   'Valid mapped nighttime offenses']
RANKED_COLUMNS = DISPLAY_COLUMNS + ['Frequency percentile', 'Persistence percentile',
                                    'Recent period start', 'Recent period end']
COLUMN_LABELS = {'RPT Dist No': 'Reporting district', 'AREA NAME': 'Area'}

# Categorical filters: (Filters attribute, source column, sidebar label).
CATEGORY_FILTERS = [
    ('areas', 'AREA NAME', 'Areas'),
    ('districts', 'RPT Dist No', 'Reporting districts'),
    ('codes', 'NIBR Code', 'NIBR offense codes'),
    ('descriptions', 'NIBR Description', 'Offense descriptions'),
    ('crime_against', 'Crime Against', 'Crime against'),
    ('premises', 'Premise Desc', 'Premises'),
]

TOP_N_OPTIONS = ['5', '10', '20', 'All']
DEFAULT_TOP_N = '10'
DEFAULT_MIN_ACTIVE = 1

# Table sorts reorder T only; they never change membership, scores or ranks.
SORT_OPTIONS = {
    'Original rank (default)': ('Rank', True),
    'Priority score, high to low': ('Priority score', False),
    'Nighttime reported offenses, high to low': ('Nighttime reported offenses', False),
    'Persistence rate, high to low': ('Persistence rate', False),
    'Recent nighttime offenses, high to low': ('Recent nighttime offenses', False),
    'Valid mapped nighttime offenses, high to low': ('Valid mapped nighttime offenses', False),
    'Reporting district, ascending': ('RPT Dist No', True),
}
DEFAULT_SORT = 'Original rank (default)'

COMPARE_MIN, COMPARE_MAX = 2, 5
TOP_CATEGORIES = 10
OTHER_LABEL = 'Other (remaining categories)'

# Map generalization: display-only rounding of valid coordinates.
MAP_DECIMALS = 3
MAP_MAX_CELLS = 25000

SCORE_FORMULA = (f'Priority score = ({FREQUENCY_WEIGHT:.2f} x frequency percentile + '
                 f'{PERSISTENCE_WEIGHT:.2f} x persistence percentile) x 100; zero when a district has '
                 'zero nighttime reported offenses')
PERCENTILE_METHOD = ("Ascending average rank divided by the number of districts in the scoring universe "
                     "(pandas rank(method='average', pct=True))")
COORDINATE_RULE = (f'Valid coordinates: latitude {LAT_BOUNDS[0]} to {LAT_BOUNDS[1]} and longitude '
                   f'{LON_BOUNDS[0]} to {LON_BOUNDS[1]} inclusive (a broad LA-region screen, not a verified '
                   'city boundary). Missing, nonnumeric, zero or outside-box coordinates are invalid; those '
                   f'offenses still count in district metrics but never enter the map. Map cells round '
                   f'valid coordinates to {MAP_DECIMALS} decimal places for display only.')

LIMITATIONS = [
    'Reported offenses are not the same as actual incidents; some offenses are never reported.',
    'Historical date anomalies (records back to 1800), reporting-system changes and reporting delays '
    'limit comparisons; the newest month may be partial and complete months may still receive late reports.',
    'Locations are approximate source values. The coordinate box is only a broad screen, not a '
    'jurisdiction or geocoding check; some "valid" points may lie far from their district (team audit '
    'AUDIT-ZAYRA-01, open).',
    'Some reporting-district keys are two-digit area-level codes (01-21) with little or no mapped '
    'location; they are ranked as recorded (team audit AUDIT-ZAYRA-02, open).',
    'Recorded midnight (0000) may reflect a source convention for unknown times; it is kept as recorded '
    'and flagged, not inferred.',
    'Streetlight asset data is unavailable: no lighting condition, streetlight location or proximity is '
    'shown or used.',
    'No verified reporting-district population denominator exists, so no population-adjusted rates are shown.',
    'Rankings support assessment prioritization only. They are not predictions, danger labels or '
    'enforcement recommendations.',
]


def relative(path):
    """Repository-relative POSIX path for public messages (never a machine path)."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name
