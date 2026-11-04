"""Local assessment dashboard. Run: python -m streamlit run app.py."""
import hashlib
import json
import logging
import time
from dataclasses import replace

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import (Filters, ranked_districts, nighttime_offenses, monthly_counts,
                          category_summary, compare_districts, eligible_months, selected_interval, recent_period)
from dashboard_support import (APP_VERSION, LIMITATION, WARNING, file_signature, load_bundle,
                               select_scopes, scope_kpis, district_label, top_categories, map_cells, export_payload)

st.set_page_config(page_title="Community Safety Resource Planner", page_icon="🌙", layout="wide")
started = time.perf_counter()
st.markdown("""<style>
.block-container {padding-top:4rem; max-width:1600px;}
h1,h2,h3 {color:#652026;} [data-testid="stMetric"] {background:#f7f5f1;border:1px solid #e7e1d8;border-radius:12px;padding:16px;}
[data-testid="stMetricValue"] {font-size:1.5rem;} [data-testid="stMetricLabel"] {white-space:normal;}
[data-testid="stSidebar"] {background:#f5f3ee;} .stDownloadButton button {border-color:#8d3339;}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=2)
def cached_bundle(signature):
    return load_bundle()


@st.cache_data(show_spinner=False, max_entries=32)
def cached_ranking(signature, filters, _data):
    return ranked_districts(_data, filters)


@st.cache_data(show_spinner=False, max_entries=32)
def cached_map(signature, filters, _data):
    return map_cells(nighttime_offenses(_data, filters, mapped_only=True))


@st.cache_data(show_spinner=False, max_entries=32)
def cached_evidence(signature, filters, _data):
    return (monthly_counts(_data, filters), category_summary(_data, "NIBR Description", filters),
            category_summary(_data, "Premise Desc", filters))


@st.cache_data(show_spinner=False, max_entries=16)
def cached_comparison(signature, filters, districts, _data):
    return compare_districts(_data, districts, filters)


def reset_filters():
    for key in list(st.session_state):
        del st.session_state[key]


def categories(label, options, key):
    all_values = st.checkbox("All " + label.lower(), value=True, key="all_" + key)
    selected = st.multiselect(label, options, key="filter_" + key, disabled=all_values,
                             help="All includes missing labels. Turn All off to choose values; an empty selection means no records.")
    return None if all_values else tuple(selected)


def draw_map(cells, title, key):
    if cells.empty:
        st.info("No valid mapped offenses in this selection. Counts and exports remain available.")
        return
    try:
        fig = px.scatter_map(cells, lat="latitude", lon="longitude", size="Reported offenses",
                             color="Reported offenses", color_continuous_scale="Burgyl", size_max=25,
                             zoom=9, map_style="carto-positron", title=title,
                             hover_data={"latitude": False, "longitude": False}, height=470)
        fig.update_layout(margin=dict(l=0, r=0, t=45, b=0))
        st.plotly_chart(fig, width="stretch", key=key)
        st.caption("Approximate locations: counts aggregated to coordinates rounded to 3 decimal places. No offense IDs or addresses are sent to the map. The broad coordinate screen does not verify district boundaries.")
    except Exception:
        logging.exception("Map rendering failed")
        st.warning("The map is unavailable. Ranking, charts and downloads remain usable.")


def display_table(frame):
    return frame.style.format({"Priority score": "{:.2f}", "Persistence rate": "{:.1%}",
                               "Average monthly nighttime offenses": "{:.2f}",
                               "Frequency percentile": "{:.1%}", "Persistence percentile": "{:.1%}"}, na_rep="N/A")


try:
    signature = file_signature()
    with st.spinner("Loading and validating the full team dataset…"):
        data, quality, dictionary, source = cached_bundle(signature)
except (OSError, ValueError, KeyError, TypeError) as exc:
    logging.exception("Canonical data validation failed")
    st.error("The canonical team data could not be loaded or validated.")
    st.info("Required repository files: data/processed/lapd_nibrs_offenses.parquet; reports/phase2/data_quality.json; reports/phase2/data_dictionary.csv. Restore them from the finalized main branch.")
    if isinstance(exc, (FileNotFoundError, ValueError)):
        st.caption(str(exc))
    st.stop()

minimum_date = pd.Timestamp("2025-01-01").date()
maximum_date = data["offense_date"].max().date()
if maximum_date < minimum_date:
    st.error("No dates are available within the approved analysis period.")
    st.stop()

with st.sidebar:
    st.markdown("### Assessment filters")
    st.button("Reset all filters", on_click=reset_filters, width="stretch")
    dates = st.date_input("Occurrence dates", (minimum_date, maximum_date),
                          min_value=minimum_date, max_value=maximum_date, key="dates")
    st.caption("Nighttime: 18:00–05:59 · recorded midnight included")
    if len(dates) != 2:
        st.info("Select both a start and end date.")
        st.stop()
    if dates[0] > dates[1]:
        st.error("Start date must not follow end date.")
        st.stop()
    areas = categories("Areas", sorted(data["AREA NAME"].dropna().unique()), "areas")
    with st.expander("Offense and premise filters"):
        codes = categories("NIBR codes", sorted(data["NIBR Code"].dropna().unique()), "codes")
        descriptions = categories("Offense descriptions", sorted(data["NIBR Description"].dropna().unique()), "descriptions")
        crime = categories("Crime-against categories", sorted(data["Crime Against"].dropna().unique()), "crime")
        premises = categories("Premises", sorted(data["Premise Desc"].dropna().unique()), "premises")

filters = Filters(start=str(dates[0]), end=str(dates[1]), areas=areas, codes=codes,
                  descriptions=descriptions, crime_against=crime, premises=premises)
try:
    universe = cached_ranking(signature, filters, data)
except (ValueError, KeyError) as exc:
    logging.exception("Backend could not attribute the selected records")
    st.error("The selected records need data review before they can be ranked. Check canonical schema and offense-ID consistency.")
    st.stop()

area_labels = dict(zip(universe["RPT Dist No"], universe["AREA NAME"].fillna("Unknown")))
labels = {code: district_label(code, area) for code, area in area_labels.items()}
with st.sidebar:
    st.divider()
    all_districts = st.checkbox("All reporting districts", value=True, key="all_districts")
    choices = sorted(area_labels)
    if "selected_districts" in st.session_state:
        st.session_state["selected_districts"] = [v for v in st.session_state["selected_districts"] if v in choices]
    selected_districts = st.multiselect("Reporting districts", choices, format_func=labels.get,
                                        disabled=all_districts, key="selected_districts")
    month_count = len(eligible_months(*selected_interval(data, filters)))
    if st.session_state.get("minimum_months", 1) > max(1, month_count):
        st.session_state["minimum_months"] = max(1, month_count)
    minimum = st.number_input("Minimum active months", min_value=1, max_value=max(1, month_count),
                               value=1, step=1, key="minimum_months", disabled=month_count == 0)
    top_label = st.selectbox("Overview districts", ["10", "5", "20", "All"], key="top_n")
    sort_label = st.selectbox("Sort overview", ["Original rank", "Nighttime count", "Persistence", "Recent count"], key="sort")

selected_ids = None if all_districts else tuple(selected_districts)
top_n = None if top_label == "All" else int(top_label)
sort_column = {"Original rank": "Rank", "Nighttime count": "Nighttime reported offenses",
               "Persistence": "Persistence rate", "Recent count": "Recent nighttime offenses"}[sort_label]
descending = sort_column != "Rank"
eligible, overview = select_scopes(universe, selected_ids, minimum, top_n, sort_column, descending)
kpis = scope_kpis(eligible)

st.caption("COMMUNITY SAFETY · LOS ANGELES")
st.title("Streetlight Assessment Planner")
st.write("Compare recurring nighttime reported-offense patterns to prioritize on-site lighting assessments.")
st.caption(WARNING)
st.info(LIMITATION)
st.caption(f"Full team source: {source['rows']:,} records · Data through {source['data_through']} · Nighttime 18:00–05:59")
st.caption(f"Selected dates: {dates[0]} to {dates[1]} · Areas: {'All' if areas is None else ', '.join(areas) or 'None'} · Additional filters: {sum(v is not None for v in (codes, descriptions, crime, premises))} · Districts: {'All' if selected_ids is None else len(selected_ids)} · Minimum active months: {minimum}")
st.caption("KPIs: all eligible selected districts, before the overview display limit")
cols = st.columns(4)
cols[0].metric("Nighttime reported offenses", f"{kpis['offenses']:,}")
cols[1].metric("Eligible districts", f"{kpis['districts']:,}")
cols[2].metric("Mean district persistence", f"{kpis['persistence']:.1%}")
cols[3].metric("Mapped nighttime offenses", f"{kpis['mapped']:,}")

eligible_ids = eligible["RPT Dist No"].tolist()
if st.session_state.get("active_district") not in eligible_ids:
    st.session_state["active_district"] = None
if "comparison" in st.session_state:
    st.session_state["comparison"] = [v for v in st.session_state["comparison"] if v in eligible_ids]
focus_col, clear_col = st.columns([5, 1])
with focus_col:
    active = st.selectbox("Focus district", [None] + eligible_ids,
                          format_func=lambda v: "Choose a district for evidence" if v is None else labels[v],
                          key="active_district")
with clear_col:
    def clear_focus():
        st.session_state["active_district"] = None
    st.button("Clear focus", on_click=clear_focus, width="stretch")

recent_start, recent_end = recent_period(data, filters)
recent_label = f"{recent_start.date()} to {recent_end.date()}" if recent_start is not None else "No complete months; recent counts are 0 by convention"
period_label = f"{dates[0]} to {dates[1]}"
tabs = st.tabs(["Priority Overview", "District Evidence", "Compare Districts", "Methods & Data Quality"])
with tabs[0]:
    st.subheader("Assessment worklist")
    st.caption(f"Overview: {len(overview):,} of {len(eligible):,} eligible districts · Rank: all {len(universe):,} districts after non-district filters")
    st.caption("Recent period: " + recent_label)
    if overview.empty:
        st.info("No districts meet these selections. Select values or use Reset all filters.")
    table_key = "ranking_" + hashlib.sha1(repr((signature, filters, selected_ids, minimum, top_n, sort_column)).encode()).hexdigest()[:16]
    def table_selection():
        rows = st.session_state.get(table_key, {}).get("selection", {}).get("rows", [])
        if rows and rows[0] < len(overview):
            st.session_state["active_district"] = overview.iloc[rows[0]]["RPT Dist No"]
    st.dataframe(display_table(overview.iloc[:, :11]), hide_index=True, width="stretch", height=390,
                 key=table_key, on_select=table_selection, selection_mode="single-row",
                 column_config={"RPT Dist No": "Reporting district", "AREA NAME": "Area"})
    st.caption("Select a row or use Focus district above to inspect its evidence. Original rank is retained when filtering or sorting.")
    with st.expander("Score components"):
        st.dataframe(display_table(overview[["RPT Dist No", "Frequency percentile", "Persistence percentile", "Priority score"]]), hide_index=True, width="stretch")
    scope_filters = replace(filters, districts=selected_ids)
    csv_bytes, json_bytes = export_payload(overview, source, scope_filters,
        universe_count=len(universe), eligible_count=len(eligible), minimum=minimum, top_n=top_n,
        sort_column=sort_column, descending=descending)
    download_cols = st.columns(2)
    download_cols[0].download_button("Download displayed worklist · CSV", csv_bytes, "assessment-worklist.csv", "text/csv", width="stretch")
    download_cols[1].download_button("Download filter & source metadata · JSON", json_bytes, "assessment-metadata.json", "application/json", width="stretch")
    st.caption("CSV contains the displayed overview rows in their current order, with unrounded values and all 15 backend columns. Import district codes as text to retain leading zeros.")
    map_ids = (active,) if active else tuple(overview["RPT Dist No"])
    map_filters = replace(filters, districts=map_ids)
    draw_map(cached_map(signature, map_filters, data),
             f"Approximate nighttime reports · {labels[active] if active else 'overview districts'} · {period_label}", key="overview_map")
    with st.expander("Current mapped coverage"):
        st.write("N/A" if kpis["coverage"] is None else f"{kpis['coverage']:.2%} of the eligible selected offenses have coordinates passing the broad screen.")
        st.caption("Full-source quality totals are available in Methods. Coverage is not a test of geocoding accuracy.")

with tabs[1]:
    st.subheader("District evidence")
    if active is None:
        st.info("Choose a Focus district above or select a worklist row.")
    else:
        row = eligible.loc[eligible["RPT Dist No"].eq(active)].iloc[0]
        st.markdown("### " + labels[active])
        st.write(f"Original rank {int(row['Rank'])} · Priority score {row['Priority score']:.2f} · {int(row['Nighttime reported offenses']):,} qualifying nighttime reported offenses across {int(row['Active months'])} of {int(row['Eligible months'])} eligible months.")
        st.caption("Recent period: " + recent_label)
        st.caption(f"Mapped evidence: {int(row['Valid mapped nighttime offenses']):,} / {int(row['Nighttime reported offenses']):,}. Short source codes are area-level entries and require interpretation before field assessment.")
        evidence_filters = replace(filters, districts=(active,))
        monthly, offenses, places = cached_evidence(signature, evidence_filters, data)
        st.plotly_chart(px.line(monthly, x="offense_month", y="nighttime_offenses", markers=True,
            title=f"Recurring or concentrated? Monthly nighttime reports · {period_label}",
            labels={"offense_month": "Occurrence month", "nighttime_offenses": "Reported offenses"}), width="stretch")
        a, b = st.columns(2)
        for container, summary, field, title in [(a, offenses, "NIBR Description", "Which offense categories drive the count?"),
                                                 (b, places, "Premise Desc", "In what types of places?")]:
            with container:
                bars = top_categories(summary, field)
                if bars.empty:
                    st.info("No qualifying composition records.")
                else:
                    st.plotly_chart(px.bar(bars, x="nighttime_offenses", y=field, orientation="h", title=title,
                        labels={"nighttime_offenses": "Reported offenses"}).update_layout(yaxis=dict(autorange="reversed")), width="stretch")
        st.caption("Top 10 categories plus the summed remainder. Unknown is a missing-value summary label; Location Unknown is a separate source label.")
        draw_map(cached_map(signature, evidence_filters, data), f"Approximate nighttime reports · {labels[active]} · {period_label}", key="evidence_map")

with tabs[2]:
    st.subheader("Compare districts on the same evidence")
    comparison = st.multiselect("Choose 2–5 eligible districts", eligible_ids, format_func=labels.get,
                                max_selections=5, key="comparison")
    if len(comparison) < 2:
        st.info("Select at least two districts. Choices include eligible districts outside the overview top-N.")
    else:
        result = cached_comparison(signature, filters, tuple(comparison), data)
        st.dataframe(display_table(result["districts"].iloc[:, :11]), hide_index=True, width="stretch")
        st.caption("Original ranks and scores are preserved. All selected districts use the same dates and category filters.")
        monthly = result["monthly"].copy()
        monthly["District"] = monthly["RPT Dist No"].map(labels)
        st.plotly_chart(px.line(monthly, x="offense_month", y="nighttime_offenses", color="District", markers=True,
            title=f"Monthly nighttime reported offenses · {period_label}",
            labels={"offense_month": "Occurrence month", "nighttime_offenses": "Reported offenses"}), width="stretch")
        chart_table = result["districts"].copy()
        chart_table["District"] = chart_table["RPT Dist No"].map(labels)
        a, b = st.columns(2)
        a.plotly_chart(px.bar(chart_table, x="District", y="Nighttime reported offenses", title="Nighttime reported offenses"), width="stretch")
        b.plotly_chart(px.bar(chart_table, x="District", y="Active months", title="Active calendar months"), width="stretch")

with tabs[3]:
    st.subheader("Methods & data quality")
    st.markdown("**Nighttime:** valid 18:00–05:59, including recorded midnight. **Unit:** distinct NIBRS offenses, not cases or people. **Persistence:** active / intersecting calendar months, including zero and partial months. **Score:** 60% frequency percentile + 40% persistence percentile, multiplied by 100.")
    st.write("The scoring universe is fixed by non-district filters. District selection, minimum months and top-N only change display scope. Recent counts use up to three complete calendar months; a zero with no period means no complete months were available.")
    st.markdown("**Full-source audit — not affected by dashboard filters**")
    audit_keys = ["raw_rows", "processed_rows", "exact_duplicates_removed", "repeated_offense_id_rows",
                  "records_before_2025", "invalid_or_missing_dates", "invalid_or_missing_times",
                  "midnight_codes", "missing_reporting_districts", "missing_offense_ids", "invalid_coordinates_total"]
    st.dataframe(pd.DataFrame({"Measure": [v.replace("_", " ") for v in audit_keys],
                               "Records": [quality[v] for v in audit_keys]}), hide_index=True, width="stretch")
    st.caption("Quality flags can overlap. Do not add them as if they were disjoint removed records. Missing coordinates do not remove otherwise qualifying offenses from ranking.")
    st.markdown("**Interpretation limits**")
    st.write("Reported offenses differ from actual incidents. Reporting-system changes, delays, historical anomalies and the partial latest month limit comparisons. Coordinates are approximate; the broad box does not prove a point belongs to its reporting district. Area-level source codes are labeled separately in selectors. There is no verified district population denominator, causal lighting measure or approved streetlight dataset.")
    st.caption("Source: City of Los Angeles LAPD NIBRS Offenses Dataset")
    st.link_button("Open official dataset catalog", "https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep")
    with st.expander("Loaded source and reproducibility"):
        st.json(source)
    with st.expander("Canonical field dictionary"):
        st.dataframe(dictionary, hide_index=True, width="stretch")

st.caption(f"{APP_VERSION} · Render preparation {time.perf_counter() - started:.2f}s · Full-dataset calculations; no analytical sampling")
