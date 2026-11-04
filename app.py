"""Community Safety Resource Planner: Streetlight Assessment (Phase 3 MVP).

Run from the repository root:
    .venv\\Scripts\\python.exe -m streamlit run app.py

UI and session state only. Metrics come from ``src.analysis`` through the
presentation adapters in ``src.dashboard``.
"""
import logging
from dataclasses import astuple

import pandas as pd
import streamlit as st

from src.analysis import Filters, eligible_months, selected_interval
from src.dashboard import adapters, charts, export, filtering, mapping, settings
from src.dashboard.loading import launch_signature, load_bundle
from src.dashboard.validation import DataError

log = logging.getLogger('dashboard')
st.set_page_config(page_title='Streetlight Assessment Planner', layout='wide')

NON_DISTRICT = [f for f in settings.CATEGORY_FILTERS if f[0] != 'districts']


# ------------------------------------------------------------------ caching
@st.cache_resource(show_spinner=False, max_entries=2)
def cached_bundle(signature):
    """Canonical frame + metadata, keyed by resolved path/size/mtime signature (read-only, shared)."""
    return load_bundle()


@st.cache_data(show_spinner=False, max_entries=64)
def cached_universe(signature, filter_key):
    """U for an immutable non-district F; shared because it holds no user selection state."""
    return adapters.scoring_universe(cached_bundle(signature).frame, Filters(*filter_key))


@st.cache_data(show_spinner=False, max_entries=4)
def cached_options(signature):
    bundle = cached_bundle(signature)
    return {col: filtering.source_options(bundle.frame, col, bundle.meta['full_max_date'])
            for _, col, _ in NON_DISTRICT}


def session_memo(name, key, fn):
    """Per-session memo for user-specific selected results (never a shared global cache)."""
    store = st.session_state.setdefault('_memo', {})
    if (name, key) not in store:
        if len(store) > 48:
            store.clear()
        store[(name, key)] = fn()
    return store[(name, key)]


# ------------------------------------------------------------------ state
def defaults(bounds):
    values = {'start': bounds[0] if bounds else None, 'end': bounds[1] if bounds else None,
              'min_active': settings.DEFAULT_MIN_ACTIVE, 'top_n': settings.DEFAULT_TOP_N,
              'sort': settings.DEFAULT_SORT, 'active_district': None, 'evidence_select': None,
              'compare_select': []}
    for attr, _, _ in settings.CATEGORY_FILTERS:
        values[f'all_{attr}'] = True
        values[f'sel_{attr}'] = []
    return values


def init_state(bounds):
    for key, value in defaults(bounds).items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault('table_nonce', 0)
    st.session_state.setdefault('notices', [])
    if bounds:  # keep stored dates inside the loaded data's range
        for key in ('start', 'end'):
            value = st.session_state[key]
            if value is None or value < bounds[0] or value > bounds[1]:
                st.session_state[key] = bounds[0] if key == 'start' else bounds[1]


def reset_all():
    for key, value in defaults(st.session_state['_bounds']).items():
        st.session_state[key] = value
    st.session_state['table_nonce'] += 1
    st.session_state.pop('_memo', None)


def set_active(district):
    st.session_state['active_district'] = district
    st.session_state['evidence_select'] = district


def clear_active():
    set_active(None)
    st.session_state['table_nonce'] += 1


def on_evidence_change():
    st.session_state['active_district'] = st.session_state['evidence_select']


def on_table_select(key):
    rows = st.session_state[key].selection.rows
    order = st.session_state.get('_t_order', [])
    set_active(order[rows[0]] if rows and rows[0] < len(order) else None)


# ------------------------------------------------------------------ helpers
def fmt_int(v):
    return f'{int(v):,}'


def table_config():
    return {
        'Rank': st.column_config.NumberColumn('Rank', format='%d', help='Original rank among all districts after non-district filters (U).'),
        'RPT Dist No': st.column_config.TextColumn('Reporting district'),
        'AREA NAME': st.column_config.TextColumn('Area'),
        'Priority score': st.column_config.NumberColumn('Priority score', format='%.2f', help=settings.SCORE_FORMULA),
        'Nighttime reported offenses': st.column_config.NumberColumn(format='%d'),
        'Active months': st.column_config.NumberColumn(format='%d'),
        'Eligible months': st.column_config.NumberColumn(format='%d'),
        'Persistence rate': st.column_config.NumberColumn(format='percent', help='Active months / eligible months'),
        'Average monthly nighttime offenses': st.column_config.NumberColumn(format='%.2f'),
        'Recent nighttime offenses': st.column_config.NumberColumn(format='%d'),
        'Valid mapped nighttime offenses': st.column_config.NumberColumn(format='%d'),
        'Frequency percentile': st.column_config.NumberColumn(format='%.4f'),
        'Persistence percentile': st.column_config.NumberColumn(format='%.4f'),
    }


def show_chart(fig, empty_message, key):
    if fig is None:
        st.info(empty_message)
    else:
        st.plotly_chart(fig, config={'displaylogo': False}, key=key)


def display_frame(frame, columns):
    out = frame[columns].copy()
    if 'AREA NAME' in out:
        out['AREA NAME'] = out['AREA NAME'].map(adapters.area_label)
    return out


def render_map(d, filters, ids, title, period, scope_label, key):
    """Map is isolated: any failure leaves metrics/tables/export usable."""
    try:
        memo_key = (signature, astuple(filters), tuple(ids))
        cells = session_memo('cells', memo_key, lambda: mapping.generalize(adapters.mapped_records(d, filters, ids)))
        st.caption(f'{scope_label}. Points are approximate: valid coordinates rounded to '
                   f'{settings.MAP_DECIMALS} decimals (about 100 m) and aggregated per cell. Not measured lighting conditions.')
        if cells.empty:
            st.info('No valid mapped nighttime offenses in this scope. Metrics and tables above remain available.')
            return
        shown, reduced = mapping.render_cells(cells)
        if reduced:
            st.caption(f'Rendering reduced to the {len(shown):,} busiest of {len(cells):,} cells; counts are unaffected.')
        fig = mapping.map_figure(shown, title, period)
        st.plotly_chart(fig, config={'displaylogo': False}, key=key)
        st.caption(f'{int(cells["offenses"].sum()):,} mapped nighttime reported offenses in {len(cells):,} cells. '
                   'Basemap tiles load from the network; if they fail, cells still plot on a blank background.')
    except Exception:  # noqa: BLE001
        log.exception('map rendering failed')
        st.warning('The map could not be rendered. Metrics, charts and export are unaffected.')


# ------------------------------------------------------------------ header + load
st.title(settings.APP_TITLE)
st.markdown(settings.PURPOSE)
st.warning(settings.WARNING_TEXT)
st.info(settings.STREETLIGHT_TEXT)

try:
    signature = launch_signature()
    if 'bundle_loaded' not in st.session_state:
        with st.status('Loading and validating the canonical processed data...', expanded=False) as status:
            bundle = cached_bundle(signature)
            status.update(label='Canonical data loaded and validated.', state='complete')
        st.session_state['bundle_loaded'] = True
    bundle = cached_bundle(signature)
except DataError as err:
    log.exception('data load failed')
    st.error(f'**{err.title}.** {err.public_message}')
    st.markdown(f'**How to recover:** {err.recovery}')
    st.stop()
except Exception:  # noqa: BLE001
    log.exception('unexpected load failure')
    st.error('**Data error.** The canonical data could not be loaded. See the local console log for details.')
    st.stop()

d, meta, quality = bundle.frame, bundle.meta, bundle.quality
bounds = filtering.date_bounds(meta['full_max_date'])
st.session_state['_bounds'] = bounds
init_state(bounds)

data_through = pd.Timestamp(meta['data_through']) if meta['data_through'] else None
st.markdown(
    f"**Data through:** {data_through:%B %d, %Y} &nbsp;|&nbsp; **Loaded file:** `{meta['processed_file']}` "
    f"({meta['rows']:,} rows) &nbsp;|&nbsp; **{settings.NIGHT_DEFINITION}**" if data_through else
    f"**Loaded file:** `{meta['processed_file']}` ({meta['rows']:,} rows)")

# ------------------------------------------------------------------ sidebar filters
sb = st.sidebar
sb.header('Filters')
sb.button('Reset all to defaults', on_click=reset_all, width='stretch', key='reset_button')
dates_ok = bounds is not None
if not dates_ok:
    sb.error('Data error: no valid occurrence dates in the canonical data. Date-dependent controls are disabled.')
start = sb.date_input('Start date (inclusive)', key='start', min_value=bounds[0] if bounds else None,
                      max_value=bounds[1] if bounds else None, disabled=not dates_ok, format='YYYY-MM-DD')
end = sb.date_input('End date (inclusive)', key='end', min_value=bounds[0] if bounds else None,
                    max_value=bounds[1] if bounds else None, disabled=not dates_ok, format='YYYY-MM-DD')
errors = filtering.date_errors(start, end, bounds)
for e in errors:
    sb.error(e)
dates_ok = not errors

options = cached_options(signature)
categories = {}


def category_widget(container, attr, column, label, choices):
    with container:
        all_on = st.checkbox(f'All {label.lower()}', key=f'all_{attr}',
                             help='All includes records whose category is missing.')
        st.multiselect(label, choices, key=f'sel_{attr}', disabled=all_on,
                       placeholder='Choose values' if not all_on else 'All selected')
        if not all_on and not st.session_state[f'sel_{attr}']:
            st.caption(f'No {label.lower()} selected: results are empty until you choose values or tick All.')
    categories[attr] = (all_on, st.session_state[f'sel_{attr}'])


area_box, district_box = sb.container(), sb.container()
category_widget(area_box, 'areas', 'AREA NAME', 'Areas', options['AREA NAME'])
for attr, column, label in NON_DISTRICT[1:]:
    category_widget(sb.container(), attr, column, label, options[column])

# F (no district) -> U, computed before the district widget so options derive from U.
f_no_district = filtering.build_filters(start if dates_ok else None, end if dates_ok else None,
                                        {**categories, 'districts': (True, ())})
if dates_ok:
    universe = cached_universe(signature, astuple(f_no_district))
else:
    universe = pd.DataFrame(columns=settings.RANKED_COLUMNS)
district_choices = list(universe.sort_values('RPT Dist No')['RPT Dist No']) if len(universe) else []

previous = list(st.session_state['sel_districts'])
st.session_state['sel_districts'] = adapters.reconcile(previous, district_choices)
category_widget(district_box, 'districts', 'RPT Dist No', 'Reporting districts', district_choices)
if previous and not st.session_state['sel_districts'] and not st.session_state['all_districts']:
    district_box.caption('None of the previously chosen districts exist under the current filters, '
                         'so the district selection is now empty.')

filters = filtering.build_filters(start if dates_ok else None, end if dates_ok else None, categories)
interval = selected_interval(d, filters) if dates_ok else (None, None)
month_count = len(eligible_months(*interval)) if dates_ok else 0

sb.subheader('Display')
clamped = adapters.clamp_min_active(st.session_state['min_active'], month_count)
if clamped is not None:
    st.session_state['min_active'] = clamped
    sb.number_input('Minimum active months', min_value=1, max_value=month_count, step=1, key='min_active',
                    help='Display threshold only; it never changes scores or ranks.')
else:
    sb.number_input('Minimum active months', value=1, disabled=True, key='_min_active_disabled')
    sb.caption('Disabled: the selected period has no eligible months.')
min_active = clamped or 1
sb.selectbox('Districts shown in overview (top N)', settings.TOP_N_OPTIONS, key='top_n')

# ------------------------------------------------------------------ scopes
E = adapters.eligible_scope(universe, filters.districts, min_active) if dates_ok else universe.iloc[:0]
e_ids = list(E.sort_values('Rank')['RPT Dist No'])
if st.session_state['active_district'] and st.session_state['active_district'] not in e_ids:
    st.session_state['notices'].append(
        f"District {st.session_state['active_district']} is no longer in the eligible scope; evidence selection cleared.")
    set_active(None)
if st.session_state['evidence_select'] not in [None] + e_ids:
    st.session_state['evidence_select'] = None
pruned = adapters.reconcile(st.session_state['compare_select'], e_ids)
if len(pruned) != len(st.session_state['compare_select']):
    st.session_state['notices'].append('Comparison districts no longer in the eligible scope were removed.')
st.session_state['compare_select'] = pruned
recent = adapters.recent_for(d, filters) if dates_ok else (None, None)
recent_text = adapters.recent_label(*recent)
period = adapters.period_label(*interval) if dates_ok else 'No valid period'
resolved = filtering.resolved_dates(d, filters) if dates_ok else (None, None)

for notice in st.session_state['notices']:
    st.toast(notice)
st.session_state['notices'] = []

tabs = st.tabs(['Priority Overview', 'District Evidence', 'Compare Districts', 'Methods and Data Quality'])

# ------------------------------------------------------------------ overview
with tabs[0]:
    if not dates_ok:
        st.error('Choose a valid date range in the sidebar to see results. Filters are kept as entered.')
    st.subheader('Key evidence in the eligible selected scope')
    st.caption(f'KPIs: all eligible selected districts ({len(E):,} districts; minimum {min_active} active '
               f'month(s); top-N does not apply). Period: {period}.')
    k = adapters.kpi_summary(E)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Nighttime reported offenses', fmt_int(k['nighttime']))
    c2.metric('Reporting districts', fmt_int(k['districts']))
    c3.metric('Mean district persistence', charts.percent(k['mean_persistence']),
              help='Unweighted mean of district persistence rates in E.')
    c4.metric('Valid mapped nighttime offenses', fmt_int(k['mapped']),
              help=f"Mapped coverage: {charts.percent(k['coverage'])}")
    st.caption(f"Mapped coverage in this scope: {charts.percent(k['coverage'])}.")

    top_n = st.session_state['top_n']
    sort_label = st.selectbox('Sort table by', list(settings.SORT_OPTIONS), key='sort',
                              help='Reorders the shown rows only; membership, scores and ranks are unchanged.')
    T = adapters.overview_rows(E, top_n, sort_label)
    st.session_state['_t_order'] = list(T['RPT Dist No'])
    st.subheader(f'Ranked reporting districts (top {top_n} of {len(E):,} eligible)')
    st.caption(f'Overview: top {top_n} of E districts. Rank: all districts after non-district filters '
               f'({len(universe):,} districts). Recent nighttime offenses period: {recent_text}.')
    if E.empty:
        st.info('No districts match the current filters and minimum active months. '
                'Adjust or reset the filters in the sidebar; your selections are kept.')
    else:
        active = st.session_state['active_district']
        rows = [st.session_state['_t_order'].index(active)] if active in st.session_state['_t_order'] else []
        key = f"overview_table_{st.session_state['table_nonce']}_{hash((tuple(T['RPT Dist No']), active))}"
        st.dataframe(display_frame(T, settings.DISPLAY_COLUMNS), hide_index=True, column_config=table_config(),
                     on_select=lambda: on_table_select(key), selection_mode='single-row', key=key,
                     selection_default={'selection': {'rows': rows}})
        b1, b2, b3 = st.columns([1, 1, 1])
        b1.button('Clear district selection', on_click=clear_active, disabled=active is None, key='clear_button')
        b2.download_button('Download worklist CSV', export.worklist_csv(T), file_name='district_worklist.csv',
                           mime='text/csv', help='Exactly the rows above in this order, unrounded, all 15 columns.')
        b3.download_button('Download worklist metadata (JSON)', export.worklist_metadata(
            meta=meta, filters=filters, resolved=resolved, min_active=min_active, top_n=top_n,
            sort_label=sort_label, counts={'U': len(universe), 'E': len(E), 'T': len(T)}, recent=recent),
            file_name='district_worklist_metadata.json', mime='application/json')
        if active:
            st.caption(f'Active evidence district: **{active}**. Select a row or use District Evidence to change it.')
        else:
            st.caption('Select a row to make it the active evidence district (see District Evidence).')
        st.caption('Open the CSV with "RPT Dist No" imported as text to keep leading zeros.')
        with st.expander('Score detail: percentiles behind the priority score'):
            st.markdown(f'{settings.SCORE_FORMULA}. {settings.PERCENTILE_METHOD}.')
            st.dataframe(display_frame(T, ['Rank', 'RPT Dist No', 'Priority score', 'Frequency percentile',
                                           'Persistence percentile']), hide_index=True, column_config=table_config())

    st.subheader('Approximate offense locations')
    active = st.session_state['active_district']
    if active:
        render_map(d, filters, (active,), f'Mapped nighttime reported offenses, district {active}', period,
                   f'Map focus: active evidence district {active} (may be outside the table). '
                   'Clear the selection to return to the table scope', key='map_overview')
    elif dates_ok:
        render_map(d, filters, adapters.scope_ids(T), 'Mapped nighttime reported offenses, overview districts',
                   period, f'Map scope: the {len(T):,} districts in the table (T)', key='map_overview')

    with st.expander('Data-quality summary'):
        q = quality
        st.markdown(
            f"- Full-source audit (unfiltered): {q['processed_rows']:,} processed rows; "
            f"{q['exact_duplicates_removed']:,} exact duplicates removed; {q['repeated_offense_id_rows']:,} repeated offense IDs.\n"
            f"- {q['records_before_2025']:,} records before 2025 are kept in the data but outside metrics.\n"
            f"- {q['invalid_coordinates_total']:,} records have invalid coordinates (still counted in district metrics, not mapped).\n"
            f"- Full-source qualifying mapped coverage: {q['qualifying_mapped_percentage']:.2f}%.\n"
            f"- Current eligible scope (E) mapped coverage: {charts.percent(k['coverage'])}.\n"
            "- See Methods and Data Quality for the full audit, definitions and limitations.")

# ------------------------------------------------------------------ evidence
with tabs[1]:
    st.subheader('District evidence')
    st.caption(f'Choices: all {len(e_ids):,} eligible districts (E), including those outside the overview table. '
               f'Period: {period}.')
    labels = E.set_index('RPT Dist No')
    st.selectbox('Reporting district', [None] + e_ids, key='evidence_select', on_change=on_evidence_change,
                 format_func=lambda v: 'Choose a district' if v is None else
                 f"{v} - {adapters.area_label(labels.loc[v, 'AREA NAME'])} (rank {int(labels.loc[v, 'Rank']):,})")
    active = st.session_state['active_district']
    if not e_ids:
        st.info('No eligible districts under the current filters.')
    elif active is None:
        st.info('Select a district here or click a row in the Priority Overview table to see its evidence.')
    else:
        ev = session_memo('evidence', (signature, astuple(filters), active),
                          lambda: adapters.evidence(d, filters, active, universe))
        row = ev['row']
        m = st.columns(6)
        m[0].metric('Area', adapters.area_label(row['AREA NAME']))
        m[1].metric('Original rank', fmt_int(row['Rank']))
        m[2].metric('Priority score', f"{row['Priority score']:.2f}")
        m[3].metric('Nighttime reported offenses', fmt_int(row['Nighttime reported offenses']))
        m[4].metric('Active / eligible months', f"{int(row['Active months'])} / {int(row['Eligible months'])}",
                    help=f"Persistence rate {charts.percent(row['Persistence rate'])}")
        m[5].metric('Mapped coverage', charts.percent(ev['coverage']),
                    help=f"{fmt_int(row['Valid mapped nighttime offenses'])} valid mapped nighttime offenses")
        st.markdown(adapters.evidence_sentence(row, period))
        st.caption(f"Persistence rate {charts.percent(row['Persistence rate'])}; recent nighttime offenses "
                   f"{fmt_int(row['Recent nighttime offenses'])} ({recent_text}).")
        fig = charts.monthly_line(ev['monthly'], f'Monthly nighttime reported offenses, district {active}', period)
        show_chart(fig, 'No monthly data for this selection.', 'chart_evidence_monthly')
        left, right = st.columns(2)
        with left:
            fig = charts.composition_bar(ev['offenses'], 'NIBR Description',
                                         f"Offense composition (top {settings.TOP_CATEGORIES} of "
                                         f"{ev['offense_categories']:,} descriptions)", period)
            show_chart(fig, 'No offense categories.', 'chart_offenses')
        with right:
            fig = charts.composition_bar(ev['premises'], 'Premise Desc',
                                         f"Premise composition (top {settings.TOP_CATEGORIES} of "
                                         f"{ev['premise_categories']:,} premises)", period)
            show_chart(fig, 'No premise categories.', 'chart_premises')
        st.caption(f'"{settings.OTHER_LABEL}" sums every category below the top {settings.TOP_CATEGORIES}. '
                   '"Unknown" marks records with no recorded description/premise; it is different from source '
                   'labels such as "Location Unknown". Shares are of this district\'s nighttime total.')
        with st.expander('Composition tables'):
            for name, col in [('offenses', 'NIBR Description'), ('premises', 'Premise Desc')]:
                st.dataframe(ev[name][[col, 'nighttime_offenses', 'share']].rename(
                    columns={'nighttime_offenses': 'Nighttime reported offenses', 'share': 'Share of district'}),
                    hide_index=True, column_config={'Share of district': st.column_config.NumberColumn(format='percent')})
        st.markdown('**Approximate mapped locations for this district**')
        render_map(d, filters, (active,), f'Mapped nighttime reported offenses, district {active}', period,
                   f'Map scope: district {active}', key='map_evidence')

# ------------------------------------------------------------------ comparison
with tabs[2]:
    st.subheader('Compare districts')
    st.caption(f'Choose {settings.COMPARE_MIN}-{settings.COMPARE_MAX} districts from the {len(e_ids):,} eligible '
               f'districts (E), including ones outside the overview table. Ranks are original. Period: {period}.')
    if len(e_ids) < settings.COMPARE_MIN:
        st.info(f'Comparison needs at least {settings.COMPARE_MIN} eligible districts; the current filters leave '
                f'{len(e_ids)}. Broaden the filters or lower the minimum active months.')
    else:
        st.multiselect('Districts to compare', e_ids, key='compare_select', max_selections=settings.COMPARE_MAX,
                       format_func=lambda v: f"{v} - {adapters.area_label(labels.loc[v, 'AREA NAME'])} "
                                             f"(rank {int(labels.loc[v, 'Rank']):,})")
        chosen = st.session_state['compare_select']
        if len(chosen) < settings.COMPARE_MIN:
            st.info(f'Select at least {settings.COMPARE_MIN} districts (up to {settings.COMPARE_MAX}).')
        else:
            result = session_memo('compare', (signature, astuple(filters), tuple(chosen)),
                                  lambda: adapters.comparison(d, filters, chosen, E))
            table = result['districts']
            st.dataframe(display_frame(table, settings.DISPLAY_COLUMNS), hide_index=True, column_config=table_config())
            fig = charts.comparison_panels(table, period)
            show_chart(fig, 'No comparison data.', 'chart_compare_panels')
            fig = charts.monthly_line(result['monthly'], 'Monthly nighttime reported offenses, selected districts', period)
            show_chart(fig, 'No monthly data.', 'chart_compare_monthly')

# ------------------------------------------------------------------ methods
with tabs[3]:
    q = quality
    st.subheader('Methods and data quality')
    st.markdown('#### Provenance')
    st.table(pd.DataFrame([
        ('Approved source file', q['source']['filename']),
        ('Source SHA-256', q['source']['sha256']),
        ('Processed file', meta['processed_file']),
        ('Processed file SHA-256', meta['processed_sha256']),
        ('Processed file size', f"{meta['processed_bytes']:,} bytes"),
        ('Loaded rows / columns', f"{meta['rows']:,} / {meta['columns']}"),
        ('Full date range in file', f"{meta['full_min_date']} to {meta['full_max_date']}"),
        ('Available analysis range', f"{meta['analysis_start']} to {meta['data_through']}"),
        ('App version / code revision', f"{meta['app_version']} / {meta['code_revision']}"),
        ('Last successful load (UTC)', meta['loaded_at_utc']),
        ('Quality report / dictionary', f"{meta['quality_file']} / {meta['dictionary_file']}"),
    ], columns=['Item', 'Value']).set_index('Item'))

    st.markdown('#### Definitions')
    with st.expander('Metric definitions', expanded=True):
        st.markdown(f"""
- **Qualifying nighttime record:** inside the selected dates and category filters, {settings.NIGHT_DEFINITION.lower()}
  Nonmissing reporting district and offense ID required; missing coordinates do not disqualify a record.
- **Counts** are distinct offense IDs (`UniqueNIBRNo`). Source `TotalOffenseCount`/`TotalVictimCount` are never summed.
- **Eligible months:** calendar months intersecting the selected inclusive dates (partial end months count).
  Metrics start {settings.START_DATE} and end at the latest valid occurrence date in the full file ({meta['data_through']}).
- **Active months:** eligible months with at least one nighttime reported offense. **Persistence rate** = active / eligible.
- **Average monthly nighttime offenses** = nighttime count / eligible months.
- **Recent nighttime offenses:** latest up to three *complete* calendar months in the selected period (currently {recent_text}).
- **{settings.SCORE_FORMULA}.** {settings.PERCENTILE_METHOD}. The scoring universe is every district present after
  non-district filters, including districts with only daytime records.
- **Rank:** score, nighttime count, persistence (all descending), then numeric district ascending, then district text.
- **Display scopes:** U = all districts after non-district filters (scores and ranks); E = U limited to the district
  selection and minimum active months (KPIs, evidence and comparison choices); T = top N of E by original rank, then table sort
  (table, map, export). District selection, thresholds, top-N and sorting never change scores or ranks.
- **Coordinates:** {settings.COORDINATE_RULE}
- No population-adjusted rates and no spatial measure enter any metric.
""")
    st.markdown('#### Full-source audit (unfiltered, from the quality report)')
    st.caption('Flags overlap (for example, a pre-2025 record may also have invalid coordinates); they are not '
               'disjoint removals and must not be summed. Only exact duplicate rows were removed during cleaning.')
    audit = [
        ('Raw rows / processed rows', f"{q['raw_rows']:,} / {q['processed_rows']:,}"),
        ('Exact duplicate rows found / removed', f"{q['exact_duplicates_found']:,} / {q['exact_duplicates_removed']:,}"),
        ('Repeated offense-ID rows (retained, flagged)', fmt_int(q['repeated_offense_id_rows'])),
        ('Rows in multi-offense cases (repeated CaseNo, retained)', fmt_int(q['repeated_case_rows_retained'])),
        ('Missing offense IDs', fmt_int(q['missing_offense_ids'])),
        ('Invalid or missing occurrence dates', fmt_int(q['invalid_or_missing_dates'])),
        ('Records before 2025 (kept, outside metrics)', fmt_int(q['records_before_2025'])),
        ('Invalid or missing occurrence times', fmt_int(q['invalid_or_missing_times'])),
        ('Recorded midnight (0000) values, full history', fmt_int(q['midnight_codes'])),
        ('Missing reporting districts', fmt_int(q['missing_reporting_districts'])),
        ('Missing / nonnumeric coordinates', f"{q['missing_coordinates']:,} / {q['nonnumeric_coordinates']:,}"),
        ('Zero / nonzero out-of-box coordinates', f"{q['zero_coordinates']:,} / {q['out_of_area_nonzero_coordinates']:,}"),
        ('Invalid coordinates, total (union)', fmt_int(q['invalid_coordinates_total'])),
        ('Qualifying nighttime records, 2025 onward', fmt_int(q['qualifying_nighttime_records'])),
        ('Qualifying mapped nighttime records', fmt_int(q['qualifying_mapped_nighttime_records'])),
        ('Full-source qualifying mapped coverage', f"{q['qualifying_mapped_percentage']:.2f}%"),
    ]
    st.table(pd.DataFrame(audit, columns=['Full-source measure', 'Count']).set_index('Full-source measure'))
    st.markdown('**Midnight treatment:** `0000` is valid midnight, included in nighttime metrics and flagged '
                'separately. Invalid or missing times stay in quality totals but never enter nighttime metrics; '
                'hours are never derived from the date field.')
    st.markdown('#### Current eligible-scope coverage (filtered, E)')
    k = adapters.kpi_summary(E)
    st.markdown(f"{fmt_int(k['mapped'])} of {fmt_int(k['nighttime'])} nighttime reported offenses in the "
                f"{fmt_int(k['districts'])} eligible districts have valid coordinates "
                f"(mapped coverage {charts.percent(k['coverage'])}).")
    with st.expander('Schema and derived-field checks run at load'):
        st.caption('Every column and type matched reports/phase2/data_dictionary.csv; rows violating each invariant:')
        st.table(pd.DataFrame(list(meta['invariant_checks'].items()), columns=['Check', 'Violating rows']).set_index('Check'))
    st.markdown('#### Limitations')
    st.markdown('\n'.join(f'- {item}' for item in settings.LIMITATIONS))
    st.markdown('#### Future extension (not part of this MVP)')
    st.markdown('With a separately approved streetlight GIS file, a future version could validate asset IDs '
                '(SLID/STLID), geometry and CRS, project to EPSG:2229 and describe nearest-light distance and lights '
                'within 150 feet. Those descriptive measures would never enter the priority score. Nothing of this is '
                'implemented or displayed here.')
    st.caption(settings.WARNING_TEXT)
