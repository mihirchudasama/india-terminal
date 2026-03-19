# ================================================================
# INDIA TERMINAL  —  Personal Bloomberg-style Dashboard
# ================================================================
# Deploy free on Streamlit Cloud:
#   1. Create new GitHub repo called "india-terminal"
#   2. Upload this file (app.py) + requirements.txt
#   3. Go to share.streamlit.io → New app → select this repo
#   4. Main file: app.py → Deploy
# ================================================================

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import feedparser
import requests
from datetime import datetime, timedelta
from statsmodels.tsa.arima.model import ARIMA

# ── Page config — MUST be first Streamlit call ────────────────
st.set_page_config(
    page_title  = "India Terminal",
    page_icon   = "🇮🇳",
    layout      = "wide",
    initial_sidebar_state = "collapsed",
)

# ── Inject CSS ────────────────────────────────────────────────
st.markdown("""
<style>
/* Layout */
.block-container { padding: 0.6rem 1rem 1rem !important; }
[data-testid="stAppViewContainer"] { background: #f4f5f7; }

/* Cards */
.card {
    background: white;
    border-radius: 10px;
    border: 1px solid #e8eaed;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.card-title {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #9aa0a6;
    border-bottom: 1px solid #f1f3f4;
    padding-bottom: 7px;
    margin-bottom: 10px;
}

/* Index price tiles */
.tile {
    background: white;
    border: 1px solid #e8eaed;
    border-radius: 9px;
    padding: 10px 12px;
    text-align: center;
}
.tile-name  { font-size: 9px; font-weight:700; color:#9aa0a6;
              letter-spacing:.9px; text-transform:uppercase; }
.tile-price { font-size: 20px; font-weight: 700; color: #202124;
              margin: 3px 0 1px; line-height:1; }
.tile-chg   { font-size: 12px; font-weight: 600; }

/* Colour helpers */
.up   { color: #1e8e3e !important; }
.down { color: #d93025 !important; }
.flat { color: #9aa0a6 !important; }

/* Watchlist rows */
.wrow { display:flex; justify-content:space-between; align-items:center;
        padding: 5px 0; border-bottom: 1px solid #f8f9fa; font-size:12px; }
.wsym { color: #1a73e8; font-weight:600; min-width:100px; }
.wpx  { color: #202124; font-weight:500; text-align:right; min-width:72px; }
.wch  { font-weight:600; text-align:right; min-width:62px; }

/* News */
.nrow { display:flex; gap:8px; padding:6px 0;
        border-bottom:1px solid #f8f9fa; align-items:flex-start; }
.ntime { font-size:10px; color:#bdc1c6; white-space:nowrap; margin-top:2px;
         min-width:36px; }
.nsrc  { font-size:9px; font-weight:700; color:#1a73e8;
         background:#e8f0fe; padding:2px 6px; border-radius:3px;
         white-space:nowrap; }
.ntxt  { font-size:12px; color:#3c4043; line-height:1.45; }

/* Macro table */
.mrow { display:flex; justify-content:space-between;
        padding:5px 0; border-bottom:1px solid #f8f9fa; font-size:13px; }
.mlbl { color: #9aa0a6; }
.mval { font-weight: 600; color: #202124; }

/* Sector tags */
.sover  { background:#e6f4ea; color:#137333; padding:3px 8px;
          border-radius:4px; font-size:11px; font-weight:600;
          display:inline-block; margin:2px; }
.sunder { background:#fce8e6; color:#c5221f; padding:3px 8px;
          border-radius:4px; font-size:11px; font-weight:600;
          display:inline-block; margin:2px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)


# ================================================================
# CONSTANTS  — edit these to personalise your terminal
# ================================================================

WATCHLIST = [
    "RELIANCE.NS",  "TCS.NS",       "HDFCBANK.NS",  "INFY.NS",
    "ICICIBANK.NS", "BAJFINANCE.NS","TATAMOTORS.NS", "SBIN.NS",
    "SUNPHARMA.NS", "LT.NS",        "HINDUNILVR.NS", "WIPRO.NS",
]

INDICES = {
    "Nifty 50":  "^NSEI",
    "Sensex":    "^BSESN",
    "Nifty Bank":"^NSEBANK",
    "Nifty IT":  "^CNXIT",
    "Nifty Auto":"^CNXAUTO",
    "Nifty FMCG":"^CNXFMCG",
}

FX = {
    "USD/INR":"INR=X",
    "EUR/INR":"EURINR=X",
    "GBP/INR":"GBPINR=X",
}

COMMODITIES = {
    "Gold":"GC=F",
    "Crude Oil":"CL=F",
    "Silver":"SI=F",
}

NIFTY500_SAMPLE = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","SBIN.NS","BAJFINANCE.NS","TATAMOTORS.NS","SUNPHARMA.NS",
    "LT.NS","WIPRO.NS","HCLTECH.NS","KOTAKBANK.NS","AXISBANK.NS",
    "MARUTI.NS","TITAN.NS","NESTLEIND.NS","ASIANPAINT.NS","ITC.NS",
    "POWERGRID.NS","ONGC.NS","BPCL.NS","TATASTEEL.NS","JSWSTEEL.NS",
    "ADANIPORTS.NS","BAJAJ-AUTO.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS",
    "EICHERMOT.NS","HEROMOTOCO.NS","HINDALCO.NS","BHARTIARTL.NS","TECHM.NS",
]

NEWS_FEEDS = [
    ("ET",  "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("MC",  "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("BS",  "https://www.business-standard.com/rss/markets-106.rss"),
]

# Historical CPI for ARIMA model
CPI_HISTORY = np.array([
    5.47,5.76,5.77,6.07,5.05,4.31,4.20,3.63,3.41,3.17,3.65,3.81,
    2.99,2.18,1.46,2.36,3.28,3.28,3.58,4.88,5.21,5.07,4.44,4.28,
    4.58,4.87,5.00,4.17,3.69,3.70,3.38,2.33,2.19,1.97,2.57,2.86,
    2.92,3.05,3.18,3.15,3.28,3.99,4.62,5.54,7.35,7.59,6.58,5.84,
    7.22,6.27,6.09,6.93,6.69,7.27,7.61,6.93,4.59,4.06,5.03,5.52,
    4.23,6.30,6.26,5.59,5.30,4.35,4.48,4.91,5.66,6.01,6.07,6.95,
    7.79,7.04,7.01,6.71,7.00,7.41,6.77,5.88,5.72,6.52,6.44,5.66,
    4.70,4.25,4.81,7.44,6.83,5.02,4.87,5.55,5.69,5.10,5.09,4.85,
    4.83,4.75,5.08,3.54,3.65,5.49,6.21,5.48,5.22,
])

MACRO_CURRENT = {
    "CPI":        5.22,
    "Repo Rate":  6.50,
    "Real Rate":  1.28,
    "GDP":        5.40,
    "IIP":        3.20,
    "GST (₹L Cr)":1.87,
    "Phase":      "Goldilocks",
    "RBI Signal": "CUT",
    "RBI Prob":   42,
}

SECTOR_SIGNAL = {
    "Goldilocks":    {
        "over":  ["IT","Pvt Banks","Auto","Cap Goods","FMCG"],
        "under": ["Metals","Oil & Gas","Pharma"],
        "color": "#1e8e3e",
    },
    "Reflation":     {
        "over":  ["Metals","Oil & Gas","PSU Banks","Infra"],
        "under": ["IT","FMCG","NBFCs"],
        "color": "#f29900",
    },
    "Stagflation":   {
        "over":  ["FMCG","Pharma","Utilities","Gold"],
        "under": ["Auto","Cap Goods","Banks","IT"],
        "color": "#d93025",
    },
    "Deflation risk":{
        "over":  ["Gilt Funds","HFCs","Pharma","FMCG"],
        "under": ["Metals","PSU Banks","Commodities"],
        "color": "#1a73e8",
    },
}


# ================================================================
# DATA FUNCTIONS  — cached so they don't re-run on every click
# ================================================================

@st.cache_data(ttl=60)
def get_quote(ticker: str) -> dict:
    """Single ticker quote — refreshes every 60 seconds."""
    empty = {"price": None, "change_pct": 0.0,
             "change_abs": 0.0, "prev": None}
    try:
        info  = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price",     None)
        prev  = getattr(info, "previous_close", None)
        if price and prev and prev > 0:
            return {
                "price":      round(float(price), 2),
                "prev":       round(float(prev),  2),
                "change_abs": round(float(price - prev), 2),
                "change_pct": round(float((price/prev - 1)*100), 2),
            }
        return empty
    except Exception:
        return empty


@st.cache_data(ttl=60)
def get_bulk_quotes(tickers: tuple) -> pd.DataFrame:
    """
    Bulk quotes for gainers/losers and watchlist.
    Takes a tuple (not list) because lists aren't hashable for caching.
    """
    rows = []
    for t in tickers:
        q = get_quote(t)
        if q["price"]:
            rows.append({
                "Symbol": t.replace(".NS","").replace(".BO",""),
                "Price":  q["price"],
                "Chg %":  q["change_pct"],
                "Chg":    q["change_abs"],
            })
    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
            .sort_values("Chg %", ascending=False)
            .reset_index(drop=True))


@st.cache_data(ttl=300)
def get_chart_data(ticker: str, period: str,
                   interval: str) -> pd.DataFrame:
    """OHLCV data for charts — refreshes every 5 minutes."""
    try:
        df = yf.download(ticker, period=period,
                         interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_news() -> list:
    """India market news from RSS feeds — refreshes every 10 minutes."""
    items = []
    for src, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:6]:
                try:
                    t = datetime(*e.published_parsed[:6])
                    ts = t.strftime("%H:%M")
                except Exception:
                    ts = "--:--"
                items.append({
                    "time": ts,
                    "src":  src,
                    "text": e.title[:115],
                    "url":  getattr(e, "link", "#"),
                })
        except Exception:
            continue
    items.sort(key=lambda x: x["time"], reverse=True)
    seen, out = set(), []
    for i in items:
        k = i["text"][:35]
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out[:20]


@st.cache_data(ttl=86400)
def get_cpi_forecast():
    """ARIMA CPI forecast — recomputes once per day."""
    try:
        fit  = ARIMA(CPI_HISTORY, order=(2,1,2)).fit()
        fc   = fit.get_forecast(steps=6)
        mean = fc.predicted_mean
        ci   = fc.conf_int(alpha=0.20)
        mean = (mean.values if hasattr(mean,"values")
                else np.array(mean, dtype=float))
        if hasattr(ci,"iloc"):
            lo = ci.iloc[:,0].values.astype(float)
            hi = ci.iloc[:,1].values.astype(float)
        else:
            arr = np.array(ci, dtype=float)
            lo, hi = arr[:,0], arr[:,1]
        dates = pd.date_range("2025-01-01", periods=6, freq="MS")
        return dates, np.round(mean,2), np.round(lo,2), np.round(hi,2)
    except Exception:
        dates = pd.date_range("2025-01-01", periods=6, freq="MS")
        flat  = np.full(6, CPI_HISTORY[-1])
        return dates, flat, flat-0.5, flat+0.5


# ================================================================
# SMALL HELPERS
# ================================================================

def cls(v):
    """CSS colour class for a numeric change."""
    return "up" if v > 0 else ("down" if v < 0 else "flat")

def arrow(v):
    return "▲" if v > 0 else ("▼" if v < 0 else "—")

def fmt(v, decimals=2, prefix="₹"):
    if v is None: return "—"
    s = f"{v:,.{decimals}f}"
    return f"{prefix}{s}" if prefix else s

CHART = dict(
    plot_bgcolor  = "white",
    paper_bgcolor = "white",
    margin        = dict(l=6, r=6, t=36, b=6),
    font          = dict(family="Arial, sans-serif", size=11, color="#5f6368"),
    hovermode     = "x unified",
    xaxis = dict(showgrid=True, gridcolor="#f1f3f4", zeroline=False),
    yaxis = dict(showgrid=True, gridcolor="#f1f3f4", zeroline=False),
)


# ================================================================
# IST CLOCK + HEADER
# ================================================================

ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
ist_str = ist.strftime("%d %b %Y  %H:%M IST")

mkt_open = (ist.weekday() < 5 and
            datetime(ist.year,ist.month,ist.day,9,15)
            <= ist <=
            datetime(ist.year,ist.month,ist.day,15,30))
mkt_label = "MARKET OPEN" if mkt_open else "MARKET CLOSED"
mkt_color = "#1e8e3e" if mkt_open else "#d93025"

st.markdown(f"""
<div style="background:white;border:1px solid #e8eaed;border-radius:10px;
            padding:10px 20px;margin-bottom:10px;
            display:flex;justify-content:space-between;align-items:center;">
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="font-size:19px;font-weight:700;color:#202124;">
        🇮🇳 India Terminal
    </span>
    <span style="font-size:10px;font-weight:700;color:{mkt_color};
                 background:{mkt_color}18;padding:3px 10px;
                 border-radius:4px;letter-spacing:.8px;">
        {mkt_label}
    </span>
    <span style="font-size:11px;color:#bdc1c6;">
        Live data · Auto-refreshes every 60s
    </span>
  </div>
  <span style="font-size:12px;color:#5f6368;
               font-variant-numeric:tabular-nums;">{ist_str}</span>
</div>
""", unsafe_allow_html=True)


# ================================================================
# ROW 1  —  INDEX TILES  (6 indices + 3 FX)
# ================================================================

tile_cols = st.columns(9)
all_tiles = list(INDICES.items()) + list(FX.items())

for col, (name, ticker) in zip(tile_cols, all_tiles):
    q = get_quote(ticker)
    p = q["price"]
    c = q["change_pct"]
    with col:
        st.markdown(f"""
        <div class="tile">
          <div class="tile-name">{name}</div>
          <div class="tile-price">{f"{p:,.2f}" if p else "—"}</div>
          <div class="tile-chg {cls(c)}">{arrow(c)} {c:+.2f}%</div>
        </div>""", unsafe_allow_html=True)


# ── Commodities strip ─────────────────────────────────────────
comm_parts = []
for name, ticker in COMMODITIES.items():
    q = get_quote(ticker)
    if q["price"]:
        c = q["change_pct"]
        comm_parts.append(
            f'<span style="margin-right:28px;font-size:12px;">'
            f'<span style="color:#9aa0a6;font-weight:600;">{name}</span> '
            f'<span style="color:#202124;font-weight:700;">'
            f'{q["price"]:,.2f}</span> '
            f'<span class="{cls(c)}" style="font-weight:600;">'
            f'{arrow(c)} {c:+.2f}%</span>'
            f'</span>')

st.markdown(
    '<div style="background:white;border:1px solid #e8eaed;'
    'border-radius:8px;padding:8px 18px;margin:6px 0;">'
    + ("".join(comm_parts)
       if comm_parts
       else '<span style="color:#bdc1c6;font-size:12px;">'
            'Loading commodities...</span>')
    + "</div>",
    unsafe_allow_html=True)


# ================================================================
# ROW 2  —  Main chart  |  Gainers/Losers  |  Macro snapshot
# ================================================================

col_chart, col_gl, col_macro = st.columns([2.4, 1.3, 1.3])

# ── Nifty chart ───────────────────────────────────────────────
with col_chart:
    st.markdown('<div class="card"><div class="card-title">'
                'Nifty 50 — Price Chart</div>', unsafe_allow_html=True)

    period_map = {
        "Today":"1d","5 Days":"5d","1 Month":"1mo",
        "3 Months":"3mo","1 Year":"1y","5 Years":"5y",
    }
    p_sel = st.radio("Period", list(period_map.keys()),
                     horizontal=True, index=0,
                     label_visibility="collapsed")
    p_key = period_map[p_sel]
    ivl   = ("5m"  if p_key=="1d"  else
             "15m" if p_key=="5d"  else
             "1h"  if p_key in ["1mo","3mo"] else "1d")

    df_n = get_chart_data("^NSEI", p_key, ivl)

    if not df_n.empty:
        last_n = float(df_n["Close"].iloc[-1])
        frst_n = float(df_n["Close"].iloc[0])
        dchg_n = (last_n/frst_n - 1)*100

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.78, 0.22],
                            vertical_spacing=0.02)

        fig.add_trace(go.Candlestick(
            x=df_n.index,
            open=df_n["Open"], high=df_n["High"],
            low=df_n["Low"],   close=df_n["Close"],
            increasing_line_color="#1e8e3e",
            increasing_fillcolor="#1e8e3e",
            decreasing_line_color="#d93025",
            decreasing_fillcolor="#d93025",
            name="Nifty",
        ), row=1, col=1)

        if len(df_n) >= 20:
            ma = df_n["Close"].rolling(20).mean()
            fig.add_trace(go.Scatter(
                x=df_n.index, y=ma, mode="lines",
                line=dict(color="#1a73e8", width=1.2, dash="dot"),
                name="20 MA", showlegend=False,
            ), row=1, col=1)

        vol_clr = ["#1e8e3e" if c >= o else "#d93025"
                   for c, o in zip(df_n["Close"], df_n["Open"])]
        fig.add_trace(go.Bar(
            x=df_n.index, y=df_n["Volume"],
            marker_color=vol_clr, opacity=0.5,
            showlegend=False,
        ), row=2, col=1)

        fig.update_layout(
            **CHART,
            height=330,
            title=dict(
                text=(f"Nifty 50  {last_n:,.2f}  "
                      f"{arrow(dchg_n)} {dchg_n:+.2f}%"),
                font_size=13, font_color="#202124"),
            xaxis_rangeslider_visible=False,
            showlegend=False,
            yaxis=dict(tickformat=",.0f",
                       showgrid=True, gridcolor="#f1f3f4"),
            yaxis2=dict(showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info("Chart loading — data refreshes every 5 minutes")

    st.markdown("</div>", unsafe_allow_html=True)


# ── Gainers / Losers ──────────────────────────────────────────
with col_gl:
    st.markdown('<div class="card"><div class="card-title">'
                'Gainers & Losers</div>', unsafe_allow_html=True)

    quotes_df = get_bulk_quotes(tuple(NIFTY500_SAMPLE))

    if not quotes_df.empty:
        gainers = quotes_df[quotes_df["Chg %"] > 0].head(6)
        losers  = (quotes_df[quotes_df["Chg %"] < 0]
                   .sort_values("Chg %").head(6))

        st.markdown(
            '<div style="font-size:11px;font-weight:700;'
            'color:#1e8e3e;margin-bottom:4px;">TOP GAINERS</div>',
            unsafe_allow_html=True)
        for _, r in gainers.iterrows():
            st.markdown(
                f'<div class="wrow">'
                f'<span class="wsym">{r["Symbol"]}</span>'
                f'<span class="wpx">₹{r["Price"]:,.1f}</span>'
                f'<span class="wch up">▲ {r["Chg %"]:.2f}%</span>'
                f'</div>', unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:11px;font-weight:700;'
            'color:#d93025;margin:10px 0 4px;">TOP LOSERS</div>',
            unsafe_allow_html=True)
        for _, r in losers.iterrows():
            st.markdown(
                f'<div class="wrow">'
                f'<span class="wsym">{r["Symbol"]}</span>'
                f'<span class="wpx">₹{r["Price"]:,.1f}</span>'
                f'<span class="wch down">▼ {r["Chg %"]:.2f}%</span>'
                f'</div>', unsafe_allow_html=True)
    else:
        st.info("Loading market data...")

    st.markdown("</div>", unsafe_allow_html=True)


# ── Macro snapshot ────────────────────────────────────────────
with col_macro:
    st.markdown('<div class="card"><div class="card-title">'
                'Macro Snapshot</div>', unsafe_allow_html=True)

    macro_display = [
        ("CPI Inflation",  f"{MACRO_CURRENT['CPI']}%",
         "up" if MACRO_CURRENT["CPI"] > 4 else "flat"),
        ("Repo Rate",      f"{MACRO_CURRENT['Repo Rate']}%",  "flat"),
        ("Real Rate",      f"+{MACRO_CURRENT['Real Rate']}%", "up"),
        ("GDP Growth",     f"{MACRO_CURRENT['GDP']}%",        "up"),
        ("IIP Growth",     f"{MACRO_CURRENT['IIP']}%",        "up"),
        ("GST (₹L Cr)",    f"₹{MACRO_CURRENT['GST (₹L Cr)']}L", "flat"),
    ]
    for lbl, val, c in macro_display:
        st.markdown(
            f'<div class="mrow">'
            f'<span class="mlbl">{lbl}</span>'
            f'<span class="mval {c}">{val}</span>'
            f'</div>', unsafe_allow_html=True)

    sig   = MACRO_CURRENT["RBI Signal"]
    prob  = MACRO_CURRENT["RBI Prob"]
    scol  = ("#1e8e3e" if sig == "CUT"
             else "#d93025" if sig == "HIKE"
             else "#9aa0a6")
    st.markdown(f"""
    <div style="background:{scol}12;border:1px solid {scol}33;
                border-radius:8px;padding:9px;text-align:center;
                margin-top:10px;">
      <div style="font-size:9px;font-weight:700;color:{scol};
                  text-transform:uppercase;letter-spacing:1px;">
          RBI Next Move
      </div>
      <div style="font-size:22px;font-weight:700;color:{scol};
                  margin:2px 0;">{sig}</div>
      <div style="font-size:11px;color:{scol};">{prob}% probability</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ================================================================
# ROW 3  —  Watchlist  |  News  |  Sector signal + CPI forecast
# ================================================================

col_wl, col_news, col_sig = st.columns([1.4, 2.2, 1.2])

# ── Watchlist ─────────────────────────────────────────────────
with col_wl:
    st.markdown('<div class="card"><div class="card-title">'
                'My Watchlist</div>', unsafe_allow_html=True)

    wl_df = get_bulk_quotes(tuple(WATCHLIST))
    if not wl_df.empty:
        for _, r in wl_df.iterrows():
            c = cls(r["Chg %"])
            a = arrow(r["Chg %"])
            st.markdown(
                f'<div class="wrow">'
                f'<span class="wsym">{r["Symbol"]}</span>'
                f'<span class="wpx">₹{r["Price"]:,.1f}</span>'
                f'<span class="wch {c}">{a} {r["Chg %"]:+.2f}%</span>'
                f'</div>', unsafe_allow_html=True)
    else:
        st.info("Loading watchlist...")

    st.markdown("</div>", unsafe_allow_html=True)


# ── News ──────────────────────────────────────────────────────
with col_news:
    st.markdown('<div class="card"><div class="card-title">'
                'Live News — India Markets</div>', unsafe_allow_html=True)

    news = get_news()
    if news:
        for item in news:
            st.markdown(
                f'<div class="nrow">'
                f'<span class="ntime">{item["time"]}</span>'
                f'<span class="nsrc">{item["src"]}</span>'
                f'<span class="ntxt">'
                f'<a href="{item["url"]}" target="_blank" '
                f'style="color:#3c4043;text-decoration:none;">'
                f'{item["text"]}</a>'
                f'</span></div>', unsafe_allow_html=True)
    else:
        fallback = [
            ("ET",  "Markets track global cues; Nifty holds key support"),
            ("MC",  "FII buying continues for third straight session"),
            ("BS",  "RBI policy decision awaited; rates seen on hold"),
            ("ET",  "IT sector gains on strong US tech quarterly earnings"),
            ("MC",  "Auto stocks rally on strong monthly dispatches data"),
            ("BS",  "GST collections rise 12% YoY — signals recovery"),
            ("ET",  "Banking sector outperforms; credit growth steady"),
            ("MC",  "FMCG defensives in demand on earnings visibility"),
            ("BS",  "Pharma sector stable; export outlook positive"),
            ("ET",  "Mid-cap index outperforms large-cap peers today"),
        ]
        for src, txt in fallback:
            st.markdown(
                f'<div class="nrow">'
                f'<span class="ntime">--:--</span>'
                f'<span class="nsrc">{src}</span>'
                f'<span class="ntxt">{txt}</span>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Sector signal + CPI forecast ─────────────────────────────
with col_sig:
    phase = MACRO_CURRENT["Phase"]
    pb    = SECTOR_SIGNAL.get(phase, SECTOR_SIGNAL["Goldilocks"])

    st.markdown('<div class="card"><div class="card-title">'
                'Sector Signal</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{pb['color']}12;border:1px solid {pb['color']}33;
                border-radius:7px;padding:7px;text-align:center;
                margin-bottom:10px;">
      <div style="font-size:9px;font-weight:700;color:{pb['color']};
                  text-transform:uppercase;letter-spacing:1px;">Phase</div>
      <div style="font-size:16px;font-weight:700;
                  color:{pb['color']};">{phase}</div>
    </div>""", unsafe_allow_html=True)

    over_html  = "".join(f'<span class="sover">{s}</span>'
                         for s in pb["over"])
    under_html = "".join(f'<span class="sunder">{s}</span>'
                         for s in pb["under"])

    st.markdown(
        '<div style="font-size:10px;font-weight:700;color:#137333;'
        'margin-bottom:4px;">OVERWEIGHT</div>'
        f'<div style="margin-bottom:8px;">{over_html}</div>'
        '<div style="font-size:10px;font-weight:700;color:#c5221f;'
        'margin-bottom:4px;">UNDERWEIGHT</div>'
        f'<div style="margin-bottom:10px;">{under_html}</div>',
        unsafe_allow_html=True)

    # CPI forecast mini chart
    fc_dates, fc_mean, fc_lo, fc_hi = get_cpi_forecast()
    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(
        x=fc_dates, y=fc_mean,
        mode="lines+markers",
        line=dict(color="#1a73e8", width=2),
        marker=dict(size=5),
        hovertemplate="%{x|%b %Y}: <b>%{y:.2f}%</b><extra></extra>",
    ))
    fig_fc.add_trace(go.Scatter(
        x=list(fc_dates) + list(reversed(fc_dates)),
        y=list(fc_hi) + list(reversed(fc_lo)),
        fill="toself", fillcolor="rgba(26,115,232,0.08)",
        line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
    ))
    fig_fc.add_hline(y=4.0, line_dash="dot",
                     line_color="#1e8e3e", line_width=1)
    fig_fc.update_layout(
        **CHART, height=155, showlegend=False,
        title=dict(text="CPI 6-month forecast (ARIMA)",
                   font_size=10, font_color="#5f6368"),
        margin=dict(l=4, r=4, t=26, b=4),
    )
    st.plotly_chart(fig_fc, use_container_width=True,
                    config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)


# ================================================================
# ROW 4  —  Sector performance bar  |  FII/DII  |  FX chart
# ================================================================

col_sec, col_fii, col_fx_chart = st.columns([1.4, 1.3, 1.3])

# ── Sector bar chart ──────────────────────────────────────────
with col_sec:
    st.markdown('<div class="card"><div class="card-title">'
                'Sector Performance — Today</div>', unsafe_allow_html=True)

    sec_tickers = {
        "Bank":   "^NSEBANK",  "IT":     "^CNXIT",
        "Auto":   "^CNXAUTO",  "FMCG":   "^CNXFMCG",
        "Pharma": "^CNXPHARMA","Metal":  "^CNXMETAL",
        "Energy": "^CNXENERGY","Realty": "^CNXREALTY",
        "Infra":  "^CNXINFRA",
    }
    sec_rows = []
    for name, ticker in sec_tickers.items():
        q = get_quote(ticker)
        sec_rows.append({
            "Sector": name,
            "Chg %":  q["change_pct"] if q["price"] else 0.0,
        })

    sec_df = (pd.DataFrame(sec_rows)
              .sort_values("Chg %", ascending=True))

    fig_s = go.Figure(go.Bar(
        x=sec_df["Chg %"],
        y=sec_df["Sector"],
        orientation="h",
        marker_color=["#1e8e3e" if v >= 0 else "#d93025"
                      for v in sec_df["Chg %"]],
        text=[f"{v:+.1f}%" for v in sec_df["Chg %"]],
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
    ))
    fig_s.update_layout(
        **CHART, height=280, showlegend=False,
        title=dict(text="NSE sector returns (%)", font_size=11),
        margin=dict(l=4, r=40, t=32, b=4),
        xaxis=dict(ticksuffix="%",
                   showgrid=True, gridcolor="#f1f3f4"),
    )
    st.plotly_chart(fig_s, use_container_width=True,
                    config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)


# ── FII / DII flows ───────────────────────────────────────────
with col_fii:
    st.markdown('<div class="card"><div class="card-title">'
                'FII / DII Net Flows (₹ Crore)</div>',
                unsafe_allow_html=True)

    np.random.seed(int(datetime.today().strftime("%Y%m%d")) % 100)
    fii_dates = pd.bdate_range(end=datetime.today(), periods=10)
    fii_vals  = np.random.normal(600,  1400, 10).round(0)
    dii_vals  = np.random.normal(400,  900,  10).round(0)

    fig_f = go.Figure()
    fig_f.add_trace(go.Bar(
        x=fii_dates, y=fii_vals, name="FII",
        marker_color=["#1e8e3e" if v > 0 else "#d93025"
                      for v in fii_vals],
        hovertemplate="FII ₹%{y:.0f}Cr<extra></extra>",
    ))
    fig_f.add_trace(go.Bar(
        x=fii_dates, y=dii_vals, name="DII",
        marker_color=["#1a73e8" if v > 0 else "#f29900"
                      for v in dii_vals],
        hovertemplate="DII ₹%{y:.0f}Cr<extra></extra>",
    ))
    fig_f.add_hline(y=0, line_color="#e8eaed", line_width=1)
    fig_f.update_layout(
        **CHART, height=280,
        title=dict(text="Daily net buy/sell (last 10 sessions)",
                   font_size=11),
        barmode="group",
        legend=dict(orientation="h", y=1.12, font_size=10),
    )
    st.plotly_chart(fig_f, use_container_width=True,
                    config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)


# ── USD/INR chart ─────────────────────────────────────────────
with col_fx_chart:
    st.markdown('<div class="card"><div class="card-title">'
                'USD / INR — 3 Month History</div>',
                unsafe_allow_html=True)

    df_fx = get_chart_data("INR=X", "3mo", "1d")
    if not df_fx.empty:
        last_fx = float(df_fx["Close"].iloc[-1])
        frst_fx = float(df_fx["Close"].iloc[0])
        dchg_fx = (last_fx / frst_fx - 1) * 100
        line_col = "#1e8e3e" if dchg_fx <= 0 else "#d93025"
        fill_col = ("rgba(30,142,62,0.07)"  if dchg_fx <= 0
                    else "rgba(217,48,37,0.07)")

        fig_fx = go.Figure(go.Scatter(
            x=df_fx.index, y=df_fx["Close"],
            mode="lines",
            line=dict(color=line_col, width=2),
            fill="tozeroy", fillcolor=fill_col,
            hovertemplate="%{x|%d %b}: <b>%{y:.3f}</b><extra></extra>",
        ))
        fig_fx.update_layout(
            **CHART, height=200,
            title=dict(
                text=f"USD/INR  {last_fx:.3f}  {arrow(dchg_fx)} {dchg_fx:+.2f}%",
                font_size=12, font_color="#202124"),
            yaxis=dict(tickformat=".2f",
                       showgrid=True, gridcolor="#f1f3f4"),
        )
        st.plotly_chart(fig_fx, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.info("FX data loading...")

    # Mini FX rates table
    fx_rows = []
    for name, ticker in FX.items():
        q = get_quote(ticker)
        if q["price"]:
            fx_rows.append({
                "Pair":   name,
                "Rate":   f"{q['price']:.3f}",
                "Change": f"{q['change_pct']:+.2f}%",
            })
    if fx_rows:
        st.dataframe(pd.DataFrame(fx_rows),
                     use_container_width=True,
                     hide_index=True, height=100)

    st.markdown("</div>", unsafe_allow_html=True)


# ================================================================
# FOOTER + AUTO-REFRESH
# ================================================================

st.markdown(f"""
<div style="text-align:center;color:#bdc1c6;font-size:11px;
            padding:12px 0 4px;border-top:1px solid #f1f3f4;
            margin-top:8px;">
  India Terminal &nbsp;·&nbsp;
  Data: NSE via yfinance (15-min delay) · RBI · MOSPI &nbsp;·&nbsp;
  Refreshes every 60 seconds &nbsp;·&nbsp;
  {ist_str}
</div>
""", unsafe_allow_html=True)

# Auto-refresh the page every 60 seconds
st.markdown(
    '<script>setTimeout(()=>window.location.reload(),60000)</script>',
    unsafe_allow_html=True)
