"""Display-only generalization of valid offense coordinates.

Input must be the backend's ``nighttime_offenses(..., mapped_only=True)`` frame.
Output cells contain only rounded coordinates and aggregate counts: no offense
IDs, case numbers, LOCATION text or original precise coordinates.
"""
import pandas as pd
import plotly.graph_objects as go

from .settings import MAP_DECIMALS, MAP_MAX_CELLS, MAP_VIEW_SHARE as VIEW_SHARE
from .style import FONT_STACK, HEADING_STACK, NAVY

CELL_COLUMNS = ['lat', 'lon', 'offenses', 'districts', 'district_list', 'first_month', 'last_month']
SEQUENTIAL = ['#cde2fb', '#86b6ef', '#3987e5', '#256abf', '#104281']


def generalize(mapped, decimals=MAP_DECIMALS):
    """Aggregate mapped records into rounded lat/lon cells (deterministic order)."""
    if mapped is None or mapped.empty:
        return pd.DataFrame(columns=CELL_COLUMNS)
    if mapped['UniqueNIBRNo'].dropna().duplicated().any():
        raise ValueError('Repeated UniqueNIBRNo requires review before mapping')
    work = pd.DataFrame({
        'lat': mapped['LAT'].astype(float).round(decimals),
        'lon': mapped['LON'].astype(float).round(decimals),
        'id': mapped['UniqueNIBRNo'],
        'district': mapped['RPT Dist No'].astype(str),
        'month': mapped['offense_month'],
    })
    grouped = work.groupby(['lat', 'lon'], sort=True)
    cells = grouped.agg(offenses=('id', 'nunique'), districts=('district', 'nunique'),
                        first_month=('month', 'min'), last_month=('month', 'max')).reset_index()
    lists = grouped['district'].agg(lambda s: _district_list(s)).reset_index(drop=True)
    cells['district_list'] = lists.values
    cells = cells.sort_values(['offenses', 'lat', 'lon'], ascending=[False, True, True]).reset_index(drop=True)
    cells['offenses'] = cells['offenses'].astype('int64')
    cells['districts'] = cells['districts'].astype('int64')
    return cells[CELL_COLUMNS]


def _district_list(series, limit=4):
    values = sorted(series.unique(), key=lambda v: (pd.to_numeric(v, errors='coerce') if
                                                     str(v).isdigit() else float('inf'), v))
    shown = ', '.join(values[:limit])
    return shown + (f' (+{len(values) - limit} more)' if len(values) > limit else '')


def render_cells(cells, max_cells=MAP_MAX_CELLS):
    """Cells to draw (largest counts first) and whether rendering was reduced."""
    if len(cells) <= max_cells:
        return cells, False
    return cells.head(max_cells), True


def _core_range(values, weights, share):
    """Smallest and largest value after trimming equal offense-weighted tails."""
    order = values.argsort()
    ordered, cumulative = values.iloc[order], weights.iloc[order].cumsum() / weights.sum()
    tail = (1 - share) / 2
    return float(ordered[cumulative >= tail].iloc[0]), float(ordered[cumulative >= 1 - tail].iloc[0])


def view(cells, share=VIEW_SHARE):
    """Opening center/zoom for the middle of the offenses, so a few stray points can't zoom the map out.

    Display only: every cell is still plotted and ``outside`` counts offenses beyond the opening box.
    """
    lat_low, lat_high = _core_range(cells['lat'], cells['offenses'], share)
    lon_low, lon_high = _core_range(cells['lon'], cells['offenses'], share)
    span = max(lat_high - lat_low, lon_high - lon_low)
    zoom = next((z for limit, z in ((.015, 14), (.03, 13), (.07, 12), (.14, 11), (.3, 10), (.6, 9)) if span < limit), 8)
    inside = cells['lat'].between(lat_low, lat_high) & cells['lon'].between(lon_low, lon_high)
    return dict(lat=(lat_low + lat_high) / 2, lon=(lon_low + lon_high) / 2, zoom=zoom,
                outside=int(cells.loc[~inside, 'offenses'].sum()))


def map_figure(cells, title, period):
    """Plotly map of generalized cells; returns None for an empty layer."""
    if cells.empty:
        return None
    hover = ('<b>%{customdata[0]:,} nighttime reported offenses</b> (approximate cell)<br>'
             'Reporting district(s): %{customdata[1]}<br>'
             'Months with records: %{customdata[2]} to %{customdata[3]}<br>'
             f'Period: {period}<extra></extra>')
    custom = list(zip(cells['offenses'], cells['district_list'],
                      pd.to_datetime(cells['first_month']).dt.strftime('%b %Y'),
                      pd.to_datetime(cells['last_month']).dt.strftime('%b %Y')))
    size = 5 + 13 * (cells['offenses'] / cells['offenses'].max()) ** 0.5
    fig = go.Figure(go.Scattermap(
        lat=cells['lat'], lon=cells['lon'], mode='markers', customdata=custom, hovertemplate=hover,
        marker=dict(size=size, color=cells['offenses'], colorscale=[[i / 4, c] for i, c in enumerate(SEQUENTIAL)],
                    opacity=0.75, colorbar=dict(title=dict(text='Offenses', font=dict(size=11)), thickness=14, x=0.915, xanchor='left'))))
    opening = view(cells)
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15)),
        map=dict(style='carto-positron', zoom=opening['zoom'], center=dict(lat=opening['lat'], lon=opening['lon']),
                 domain=dict(x=[0, 0.9], y=[0, 1])),
        margin=dict(l=0, r=0, t=40, b=0), height=480,
        font=dict(family=FONT_STACK, size=13), title_font=dict(family=HEADING_STACK, color=NAVY, size=17),
        paper_bgcolor='rgba(0,0,0,0)', hoverlabel=dict(font=dict(family=FONT_STACK), bgcolor='#ffffff'))
    return fig
