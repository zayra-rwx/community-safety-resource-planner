"""Visual layer: fonts, colors, motion and the page header.

Presentation only. Nothing here reads data or calculates metrics, so styling
changes never require touching analysis or adapters.
"""
from html import escape

import streamlit as st

FONT_BODY = 'Inter'
FONT_HEADING = 'Plus Jakarta Sans'
FONT_STACK = f'"{FONT_BODY}", system-ui, -apple-system, "Segoe UI", sans-serif'
HEADING_STACK = f'"{FONT_HEADING}", {FONT_STACK}'

# Chart chrome and ink (reference palette); series colors live in charts.py.
INK = '#0b0b0b'
INK_SECONDARY = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
AXIS = '#c3c2b7'
NAVY = '#0d366b'
BLUE = '#1c5cab'

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

:root {{
  --ink: {INK}; --ink-2: {INK_SECONDARY}; --muted: {MUTED};
  --navy: {NAVY}; --blue: {BLUE}; --amber: #f5b942;
  --card: #ffffff; --plane: #f9f9f7; --line: rgba(11,11,11,0.09);
  --shadow: 0 1px 2px rgba(13,54,107,0.06), 0 4px 14px rgba(13,54,107,0.06);
  --shadow-hover: 0 2px 4px rgba(13,54,107,0.08), 0 10px 28px rgba(13,54,107,0.12);
  --ease: cubic-bezier(.2,.7,.2,1);
}}

/* Type: heavier body text and bold display headings */
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, select,
[data-testid="stMetricLabel"], [data-testid="stCaptionContainer"] {{
  font-family: {FONT_STACK}; }}
.stApp {{ color: var(--ink); }}
.stMarkdown p, .stMarkdown li, label {{ font-weight: 500; }}
h1, h2, h3, h4, h5, h6, [data-testid="stMetricValue"] {{
  font-family: {HEADING_STACK} !important; letter-spacing: -0.02em; color: var(--navy) !important; }}
h1 {{ font-weight: 800 !important; }}
h2, h3 {{ font-weight: 700 !important; }}
h4, h5 {{ font-weight: 700 !important; }}
[data-testid="stCaptionContainer"] {{ color: var(--ink-2); font-weight: 500; opacity: 1 !important; }}
.block-container {{ padding-top: 3.6rem; max-width: 1500px; }}

/* Motion: content fades up when it first appears; respect reduced motion */
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
[data-testid="stElementContainer"] {{ animation: fadeUp .5s var(--ease) both; }}
[data-testid="stTabPanel"] {{ animation: fadeIn .4s var(--ease) both; }}
[data-stale="true"] {{ transition: opacity .35s var(--ease); }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }} }}

/* Header */
.hero {{ position: relative; overflow: hidden; border-radius: 20px; padding: 22px 30px 20px;
  background: radial-gradient(circle at 88% 18%, rgba(245,185,66,0.38), transparent 32%),
              linear-gradient(135deg, #0a2a55 0%, {NAVY} 45%, #184f95 100%);
  color: #fff; box-shadow: 0 12px 34px rgba(13,54,107,0.25); margin-bottom: 14px; }}
.hero [data-testid="stHeaderActionElements"], .hero h1 a {{ display: none !important; }}
.hero .eyebrow {{ font: 700 .74rem/1 {FONT_STACK}; letter-spacing: .16em; text-transform: uppercase;
  color: #f8d68a; margin-bottom: 10px; }}
.hero h1 {{ color: #fff !important; font-size: 2rem; line-height: 1.15; margin: 0 0 6px; padding: 0; }}
.hero p {{ color: rgba(255,255,255,0.86); font-size: 1.04rem; font-weight: 500; max-width: 860px; margin: 0; }}
.callouts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 0 0 12px; }}
@media (max-width: 900px) {{ .callouts {{ grid-template-columns: 1fr; }} }}
.callout {{ display: flex; gap: 12px; align-items: flex-start; background: var(--card);
  border: 1px solid var(--line); border-left: 4px solid var(--c); border-radius: 14px;
  padding: 14px 16px; box-shadow: var(--shadow); font-size: .93rem; line-height: 1.5; color: var(--ink); }}
.callout b {{ display: block; font-family: {HEADING_STACK}; color: var(--c); margin-bottom: 2px; }}
.callout .icon {{ flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center;
  background: var(--c); color: #fff; font-weight: 800; font-size: .85rem; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 6px; }}
.chip {{ background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 6px 13px;
  font-size: .84rem; font-weight: 500; color: var(--ink-2); box-shadow: var(--shadow); }}
.chip b {{ color: var(--navy); font-weight: 700; }}

/* KPI cards */
[data-testid="stMetric"] {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 16px 18px; box-shadow: var(--shadow);
  transition: transform .25s var(--ease), box-shadow .25s var(--ease); }}
[data-testid="stMetric"]:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-hover); }}
[data-testid="stMetricValue"] {{ font-size: 1.85rem !important; font-weight: 800 !important; }}
[data-testid="stMetricLabel"] p {{ font-weight: 600; color: var(--ink-2); }}
[data-testid="stMetricLabel"] * {{ white-space: normal !important; overflow: visible !important;
  text-overflow: clip !important; }}

/* Tabs */
[data-testid="stTabs"] [role="tablist"] {{ gap: 6px; border-bottom: 1px solid var(--line); }}
[data-testid="stTab"] {{ border-radius: 10px 10px 0 0; padding: 10px 16px !important;
  transition: background .2s var(--ease); }}
[data-testid="stTab"] p {{ font-family: {HEADING_STACK}; font-weight: 700; font-size: .98rem; color: var(--ink-2);
  transition: color .2s var(--ease); }}
[data-testid="stTab"]:hover {{ background: rgba(28,92,171,0.07); }}
[data-testid="stTab"][aria-selected="true"] p {{ color: var(--blue); }}
.react-aria-SelectionIndicator {{ background: var(--blue) !important; height: 3px !important; border-radius: 3px; }}

/* Buttons and inputs */
.stButton button, .stDownloadButton button, .stLinkButton a {{ border-radius: 11px; font-weight: 600;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), background .18s var(--ease); }}
.stButton button:hover, .stDownloadButton button:hover, .stLinkButton a:hover {{
  transform: translateY(-1px); box-shadow: var(--shadow-hover); }}
[data-baseweb="select"] > div, [data-baseweb="input"] {{ border-radius: 10px !important; }}

/* Panels */
[data-testid="stExpander"] details {{ border-radius: 14px; border: 1px solid var(--line); background: var(--card);
  box-shadow: var(--shadow); }}
[data-testid="stExpander"] summary p {{ font-weight: 700; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{ border-radius: 12px; overflow: hidden; }}
[data-testid="stPlotlyChart"] {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 8px 10px; box-shadow: var(--shadow); }}
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #f3f5f9 0%, #eef1f6 100%);
  border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] h2 {{ font-size: 1.25rem; }}
[data-testid="stSidebar"] h3 {{ font-size: 1.02rem; margin-top: .6rem; }}
</style>
"""


def inject():
    """Add the stylesheet once per rerun (Streamlit replaces it in place)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title, purpose, eyebrow):
    st.markdown(f'<div class="hero"><div class="eyebrow">{escape(eyebrow)}</div>'
                f'<h1>{escape(title)}</h1><p>{escape(purpose)}</p></div>', unsafe_allow_html=True)


def callouts(warning, limitation):
    """The required non-causal warning and streetlight limitation, each with an icon and label."""
    st.markdown(
        '<div class="callouts">'
        f'<div class="callout" style="--c:#b26b00"><span class="icon">!</span>'
        f'<div><b>Not a causal finding</b>{escape(warning)}</div></div>'
        f'<div class="callout" style="--c:{BLUE}"><span class="icon">i</span>'
        f'<div><b>Streetlight data unavailable</b>{escape(limitation)}</div></div>'
        '</div>', unsafe_allow_html=True)


def chips(items):
    """Row of (label, value) facts under the header."""
    html = ''.join(f'<span class="chip">{escape(k)} <b>{escape(v)}</b></span>' for k, v in items)
    st.markdown(f'<div class="chips">{html}</div>', unsafe_allow_html=True)


def chart_theme(fig):
    """Shared Plotly typography and recessive chrome for every figure."""
    fig.update_layout(font=dict(family=FONT_STACK, color=INK_SECONDARY, size=13),
                      title_font=dict(family=HEADING_STACK, color=NAVY, size=17),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      hoverlabel=dict(font=dict(family=FONT_STACK, size=13), bgcolor='#ffffff',
                                      bordercolor=AXIS),
                      transition=dict(duration=400, easing='cubic-in-out'))
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont=dict(color=MUTED))
    return fig
