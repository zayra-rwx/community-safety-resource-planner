"""Display-only generalization of valid offense coordinates.

Input must be the backend's ``nighttime_offenses(..., mapped_only=True)`` frame.
Output cells contain only rounded coordinates and aggregate counts: no offense
IDs, case numbers, LOCATION text or original precise coordinates.
"""
import pandas as pd
import plotly.graph_objects as go

from .settings import MAP_DECIMALS, MAP_MAX_CELLS

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
                    opacity=0.75, colorbar=dict(title='Offenses<br>per cell'))))
    lat_span = float(cells['lat'].max() - cells['lat'].min())
    lon_span = float(cells['lon'].max() - cells['lon'].min())
    span = max(lat_span, lon_span, 0.01)
    zoom = 13 if span < 0.02 else 12 if span < 0.05 else 11 if span < 0.1 else 10 if span < 0.25 else 9 \
        if span < 0.6 else 8
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15)),
        map=dict(style='carto-positron', zoom=zoom,
                 center=dict(lat=float(cells['lat'].median()), lon=float(cells['lon'].median()))),
        margin=dict(l=0, r=0, t=40, b=0), height=480)
    return fig
