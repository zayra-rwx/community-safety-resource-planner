"""Plotly figures built from adapter outputs only (no metric calculation).

Each builder returns ``None`` for empty input so the UI can show an empty state.
Identity never relies on color alone: multi-series lines also vary marker
symbol and dash, and carry a legend.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .style import chart_theme

SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4']  # fixed categorical order
SYMBOLS = ['circle', 'square', 'diamond', 'triangle-up', 'x']
DASHES = ['solid', 'dash', 'dot', 'dashdot', 'longdash']
SINGLE = '#2a78d6'
MUTED = '#898781'


def _layout(fig, title, period, y_title, height=380):
    fig.update_layout(title=dict(text=f'{title}<br><sup>{period}</sup>', x=0, font=dict(size=15)),
                      height=height, margin=dict(l=10, r=10, t=70, b=10), hovermode='x unified',
                      legend=dict(orientation='h', yanchor='bottom', y=-0.35, x=0))
    fig.update_yaxes(title_text=y_title, rangemode='tozero', tickformat=',d')
    return chart_theme(fig)


def _mark_partial(fig, months):
    """Shade months only partly inside the selected dates, so a low count isn't read as a real drop."""
    for month in months:
        month = pd.Timestamp(month)
        fig.add_shape(type='rect', xref='x', yref='paper', x0=month - pd.Timedelta(days=14),
                      x1=month + pd.Timedelta(days=14), y0=0, y1=1, fillcolor='#f0efec', line_width=0, layer='below')
        fig.add_annotation(xref='x', yref='paper', x=month, y=1, yanchor='bottom', showarrow=False,
                           text='Partial month', font=dict(size=11, color='#52514e'))


def monthly_line(monthly, title, period, names=None, partial=()):
    """Monthly nighttime counts per district, zero months included. ``names`` maps key -> display label."""
    if monthly is None or monthly.empty:
        return None
    fig = go.Figure()
    districts = list(dict.fromkeys(monthly['RPT Dist No']))
    for i, district in enumerate(districts):
        part = monthly.loc[monthly['RPT Dist No'].eq(district)]
        single = len(districts) == 1
        name = (names or {}).get(district, f'District {district}')
        fig.add_trace(go.Scatter(
            x=part['offense_month'], y=part['nighttime_offenses'], name=name,
            mode='lines+markers',
            line=dict(width=2, color=SINGLE if single else SERIES[i % 5], dash=DASHES[i % 5]),
            marker=dict(size=8, symbol=SYMBOLS[i % 5]),
            hovertemplate=f'{name}: ' + '%{y:,d} nighttime reported offenses<extra></extra>'))
    fig.update_xaxes(title_text='Occurrence month', dtick='M1' if len(monthly['offense_month'].unique()) <= 12
                     else 'M3', tickformat='%b %Y')
    fig = _layout(fig, title, period, 'Nighttime reported offenses (count)')
    fig.update_layout(showlegend=len(districts) > 1)
    _mark_partial(fig, partial)
    return fig


def composition_bar(top, label_column, title, period):
    """Horizontal bars of top categories plus a summed remainder bar."""
    if top is None or top.empty:
        return None
    rows = top.iloc[::-1]
    colors = [MUTED if r else SINGLE for r in rows['is_remainder']]
    text = [f'{c:,} ({s:.1%})' for c, s in zip(rows['nighttime_offenses'], rows['share'])]
    hover = [(f'{lbl}<br>{c:,} nighttime reported offenses ({s:.1%})'
              + (f'<br>Sum of {n:,} smaller categories' if r else ''))
             for lbl, c, s, r, n in zip(rows[label_column], rows['nighttime_offenses'], rows['share'],
                                        rows['is_remainder'], rows['remaining_categories'])]
    fig = go.Figure(go.Bar(x=rows['nighttime_offenses'], y=rows[label_column], orientation='h',
                           marker=dict(color=colors), text=text, textposition='outside', cliponaxis=False,
                           hovertext=hover, hoverinfo='text'))
    fig.update_xaxes(title_text='Nighttime reported offenses (count)', tickformat=',d',
                     range=[0, max(rows['nighttime_offenses'].max(), 1) * 1.18])
    fig.update_yaxes(automargin=True)
    fig.update_layout(title=dict(text=f'{title}<br><sup>{period}</sup>', x=0, font=dict(size=15)),
                      height=110 + 32 * len(rows), margin=dict(l=10, r=60, t=70, b=10), showlegend=False,
                      barcornerradius=4, bargap=0.28)
    return chart_theme(fig)


def comparison_panels(table, period, names=None):
    """Aligned panels: nighttime counts and active months per chosen district (same order)."""
    if table is None or table.empty:
        return None
    labels = [f"{(names or {}).get(d, d)} (rank {r:,})" for d, r in zip(table['RPT Dist No'], table['Rank'])]
    eligible = int(table['Eligible months'].iloc[0])
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.08,
                        subplot_titles=('Nighttime reported offenses (count)',
                                        f'Active months (of {eligible} eligible)'))
    fig.add_trace(go.Bar(x=table['Nighttime reported offenses'], y=labels, orientation='h', marker_color=SINGLE,
                         text=[f'{v:,}' for v in table['Nighttime reported offenses']], textposition='outside',
                         cliponaxis=False, hovertemplate='%{y}<br>%{x:,d} nighttime reported offenses<extra></extra>'),
                  row=1, col=1)
    fig.add_trace(go.Bar(x=table['Active months'], y=labels, orientation='h', marker_color=SINGLE,
                         text=[f'{v:,} / {eligible}' for v in table['Active months']], textposition='outside',
                         cliponaxis=False, hovertemplate='%{y}<br>%{x:,d} active months<extra></extra>'),
                  row=1, col=2)
    fig.update_yaxes(autorange='reversed', automargin=True)
    fig.update_xaxes(rangemode='tozero', tickformat=',d')
    fig.update_xaxes(range=[0, max(eligible, 1) * 1.15], row=1, col=2)
    fig.update_layout(title=dict(text=f'Selected districts on the same evidence<br><sup>{period}</sup>', x=0,
                                 font=dict(size=15)),
                      height=140 + 45 * len(table), margin=dict(l=10, r=40, t=90, b=10), showlegend=False,
                      barcornerradius=4, bargap=0.3)
    fig.update_annotations(font=dict(size=13, color='#52514e'))
    return chart_theme(fig)


def percent(value):
    return 'N/A' if value is None or pd.isna(value) else f'{value:.1%}'
