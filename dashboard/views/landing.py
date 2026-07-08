# dashboard/views/landing.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from dashboard.config import op_color, op_label, station_name
from dashboard.database import (
    load_crawler_overview, load_crawler_stats_by_operator,
    load_crawler_daily_counts, load_route_list,
)


_OPERATOR_META = {
    "db":           {"flag": "🇩🇪", "country": "Deutschland",  "type": "Fernbahn"},
    "db_parsebot":  {"flag": "🇩🇪", "country": "Deutschland",  "type": "Fernbahn (2. Quelle)"},
    "flixtrain":    {"flag": "🇩🇪", "country": "Europa",       "type": "Low-Cost Bahn"},
    "flixbus":      {"flag": "🇪🇺", "country": "Europa",       "type": "Fernbus"},
    "trenitalia":   {"flag": "🇮🇹", "country": "Italien",      "type": "Fernbahn"},
    "italo":        {"flag": "🇮🇹", "country": "Italien",      "type": "High-Speed"},
    "ouigo_es":     {"flag": "🇪🇸", "country": "Spanien",      "type": "Low-Cost Bahn"},
    "ouigo_fr":     {"flag": "🇫🇷", "country": "Frankreich",   "type": "Low-Cost Bahn"},
    "regiojet":     {"flag": "🇨🇿", "country": "Tschechien",   "type": "Fernbahn"},
    "ceske-drahy":  {"flag": "🇨🇿", "country": "Tschechien",   "type": "Fernbahn"},
}

_HORIZONS = [90, 60, 45, 30, 21, 14, 10, 7, 6, 5, 4, 3, 2, 1]
_MODULE_CHART_TYPES = ["area", "line", "curve", "heatmap", "bar", "scatter", "dots"]

_ANNOTATIONS = [
    ("2026-03-01", "Projektstart"),
    ("2026-04-15", "Trenitalia & Italo"),
    ("2026-05-10", "OUIGO ES/FR"),
    ("2026-06-01", "České dráhy"),
    ("2026-06-30", "db_parsebot Ausfall"),
    ("2026-07-01", "DB-Crawler → VM"),
]

_CHART_ICONS = {
    "area": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 20 L8 14 L16 16 L24 8 L32 10 L40 4 L40 24 L0 24Z" fill="currentColor" opacity="0.15"/>
        <path d="M0 20 L8 14 L16 16 L24 8 L32 10 L40 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "line": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 18 L10 14 L18 16 L26 6 L34 8 L40 2" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="26" cy="6" r="2" fill="currentColor"/>
        <circle cx="40" cy="2" r="2" fill="currentColor"/>
    </svg>""",
    "curve": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 20 C10 20 14 18 20 12 C26 6 30 4 38 4" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <path d="M2 20 C10 20 16 19 22 17 C28 15 32 12 38 10" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.45"/>
    </svg>""",
    "heatmap": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.2"/>
        <rect x="12" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.7"/>
        <rect x="22" y="2" width="8" height="8" rx="1" fill="currentColor" opacity="0.4"/>
        <rect x="32" y="2" width="6" height="8" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="2" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.6"/>
        <rect x="12" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.3"/>
        <rect x="22" y="13" width="8" height="8" rx="1" fill="currentColor" opacity="0.8"/>
        <rect x="32" y="13" width="6" height="8" rx="1" fill="currentColor" opacity="0.15"/>
    </svg>""",
    "bar": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="8" width="6" height="14" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="11" y="13" width="6" height="9" rx="1" fill="currentColor" opacity="0.6"/>
        <rect x="20" y="4" width="6" height="18" rx="1" fill="currentColor" opacity="0.9"/>
        <rect x="29" y="10" width="6" height="12" rx="1" fill="currentColor" opacity="0.5"/>
        <rect x="2" y="22" width="33" height="1" rx="0.5" fill="currentColor" opacity="0.2"/>
    </svg>""",
    "scatter": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="18" r="2.5" fill="currentColor" opacity="0.6"/>
        <circle cx="16" cy="12" r="3.5" fill="currentColor" opacity="0.8"/>
        <circle cx="24" cy="8" r="2" fill="currentColor" opacity="0.5"/>
        <circle cx="32" cy="14" r="4" fill="currentColor" opacity="0.7"/>
        <circle cx="38" cy="6" r="1.5" fill="currentColor" opacity="0.4"/>
        <path d="M4 20 L38 4" stroke="currentColor" stroke-width="0.75" stroke-dasharray="2 2" opacity="0.25"/>
    </svg>""",
    "dots": """<svg viewBox="0 0 40 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="6" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="6" cy="14" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="20" cy="6" r="3" fill="currentColor" opacity="0.5"/>
        <circle cx="20" cy="14" r="3" fill="currentColor" opacity="0.9"/>
        <circle cx="34" cy="6" r="3" fill="currentColor" opacity="0.2"/>
        <circle cx="34" cy="14" r="3" fill="currentColor" opacity="0.9"/>
    </svg>""",
}


def _css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    .lp-eyebrow {
        font-size: 0.65rem; font-weight: 600; letter-spacing: 0.18em;
        text-transform: uppercase; color: var(--text-color); opacity: 0.35;
        margin-bottom: 0.6rem; font-family: 'Inter', sans-serif;
    }
    .lp-title {
        font-family: 'Inter', sans-serif; font-size: 2.6rem; font-weight: 700;
        letter-spacing: -0.03em; color: var(--text-color); line-height: 1.05;
        margin: 0 0 0.8rem 0;
    }
    .lp-subtitle {
        font-family: 'Inter', sans-serif; font-size: 0.92rem; font-weight: 400;
        color: var(--text-color); opacity: 0.5; line-height: 1.7;
        max-width: 480px; margin: 0;
    }
    .lp-kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem 2rem; }
    .lp-kpi { border-top: 2px solid #2563EB; padding-top: 0.7rem; }
    .lp-kpi-value {
        font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 600;
        color: var(--text-color); line-height: 1; margin-bottom: 0.25rem; letter-spacing: -0.02em;
    }
    .lp-kpi-label {
        font-size: 0.65rem; font-weight: 600; color: var(--text-color); opacity: 0.35;
        text-transform: uppercase; letter-spacing: 0.12em; font-family: 'Inter', sans-serif;
    }
    .lp-rule { height: 1px; background: rgba(128,128,128,0.12); margin: 2.2rem 0; }
    .lp-section-label {
        font-size: 0.62rem; font-weight: 600; letter-spacing: 0.22em;
        text-transform: uppercase; color: var(--text-color); opacity: 0.3;
        margin-bottom: 1.2rem; font-family: 'Inter', sans-serif;
    }
    .lp-findings-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.6rem; margin-bottom: 0.5rem; }
    .lp-finding {
        border: 1px solid rgba(128,128,128,0.13); border-radius: 7px;
        padding: 1rem 1.1rem; background: var(--secondary-background-color);
        border-left: 3px solid #2563EB;
    }
    .lp-finding-label {
        font-size: 0.6rem; font-weight: 600; letter-spacing: 0.15em;
        text-transform: uppercase; color: var(--text-color); opacity: 0.35;
        margin-bottom: 0.4rem; font-family: 'Inter', sans-serif;
    }
    .lp-finding-value {
        font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; font-weight: 600;
        color: var(--text-color); line-height: 1.1; margin-bottom: 0.25rem;
    }
    .lp-finding-accent { color: #2563EB; font-weight: 600; }
    .lp-finding-sub {
        font-size: 0.72rem; color: var(--text-color); opacity: 0.45;
        font-family: 'Inter', sans-serif; line-height: 1.4;
    }
    .lp-op-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; margin-bottom: 0.5rem; }
    .lp-op-card {
        border: 1px solid rgba(128,128,128,0.13); border-radius: 7px;
        padding: 0 0 0.7rem 0; background: var(--secondary-background-color); overflow: hidden;
    }
    .lp-op-stripe { height: 4px; border-radius: 7px 7px 0 0; margin-bottom: 0.7rem; }
    .lp-op-body { padding: 0 0.9rem; }
    .lp-op-flag { font-size: 1.1rem; margin-bottom: 0.35rem; line-height: 1; }
    .lp-op-name { font-size: 0.8rem; font-weight: 700; color: var(--text-color); margin-bottom: 0.15rem; line-height: 1.2; }
    .lp-op-type { font-size: 0.65rem; color: var(--text-color); opacity: 0.38; margin-bottom: 0.3rem; }
    .lp-op-count { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 600; color: var(--text-color); opacity: 0.75; }
    .lp-op-count-label { font-size: 0.6rem; color: var(--text-color); opacity: 0.28; text-transform: uppercase; letter-spacing: 0.08em; }
    .lp-op-daterange {
        font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
        color: var(--text-color); opacity: 0.35; margin-top: 0.35rem; line-height: 1.5;
    }
    .lp-flow { display: grid; grid-template-columns: 1fr 24px 1fr 24px 1fr 24px 1fr; align-items: center; gap: 0; margin-bottom: 1.5rem; }
    .lp-flow-step {
        border: 1px solid rgba(128,128,128,0.13); border-radius: 7px;
        padding: 1rem 1rem 0.9rem 1rem; background: var(--secondary-background-color);
    }
    .lp-flow-num { font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; font-weight: 600; color: #2563EB; margin-bottom: 0.55rem; }
    .lp-flow-title { font-size: 0.85rem; font-weight: 700; color: var(--text-color); margin-bottom: 0.35rem; line-height: 1.2; }
    .lp-flow-desc { font-size: 0.7rem; color: var(--text-color); opacity: 0.42; line-height: 1.55; }
    .lp-flow-arrow { text-align: center; font-size: 0.9rem; color: var(--text-color); opacity: 0.2; }
    .lp-hz-row { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.5rem 0 0 0; }
    .lp-hz {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 500;
        padding: 0.18rem 0.5rem; border: 1px solid rgba(128,128,128,0.18); border-radius: 3px;
        color: var(--text-color); opacity: 0.5; background: var(--secondary-background-color);
    }
    .lp-density-wrap { overflow-x: auto; margin-bottom: 0.5rem; }
    .lp-density-table { border-collapse: collapse; width: 100%; font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; }
    .lp-density-table th { padding: 0.3rem 0.4rem; text-align: center; font-weight: 600; color: var(--text-color); opacity: 0.4; border-bottom: 1px solid rgba(128,128,128,0.15); }
    .lp-density-table th.row-head { text-align: left; min-width: 130px; }
    .lp-density-table td { padding: 0.25rem 0.4rem; text-align: center; border-bottom: 1px solid rgba(128,128,128,0.07); }
    .lp-density-table td.row-head { text-align: left; font-family: 'Inter', sans-serif; font-size: 0.72rem; font-weight: 500; color: var(--text-color); opacity: 0.7; }
    .lp-cell-full  { background: rgba(37,99,235,0.55); border-radius: 3px; color: transparent; width: 18px; height: 14px; display:inline-block; }
    .lp-cell-part  { background: rgba(37,99,235,0.2);  border-radius: 3px; color: transparent; width: 18px; height: 14px; display:inline-block; }
    .lp-cell-empty { background: rgba(128,128,128,0.08); border-radius: 3px; color: transparent; width: 18px; height: 14px; display:inline-block; }
    .lp-mod-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; margin-bottom: 0.5rem; }
    .lp-mod-grid-bottom { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-bottom: 1rem; }
    .lp-mod-card {
        border: 1px solid rgba(128,128,128,0.13); border-radius: 7px;
        padding: 0.9rem 1rem; background: var(--secondary-background-color);
        display: flex; flex-direction: column; gap: 0.5rem;
    }
    .lp-mod-icon { width: 40px; height: 24px; color: #2563EB; flex-shrink: 0; }
    .lp-mod-question { font-size: 0.8rem; font-weight: 600; color: var(--text-color); line-height: 1.35; }
    .lp-mod-name { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-color); opacity: 0.35; }
    .lp-mod-desc { font-size: 0.68rem; color: var(--text-color); opacity: 0.38; line-height: 1.5; margin-top: auto; }
    .lp-method { font-size: 0.82rem; color: var(--text-color); opacity: 0.55; line-height: 1.75; }
    .lp-method b { color: var(--text-color); opacity: 1; font-weight: 600; }
    .lp-method code { font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; background: rgba(128,128,128,0.1); padding: 0.05rem 0.3rem; border-radius: 3px; }
    .lp-footer {
        border-top: 1px solid rgba(128,128,128,0.12); padding: 1.2rem 0 2rem 0; margin-top: 2.5rem;
    }
    .lp-footer-top {
        display: flex; justify-content: space-between; align-items: flex-start;
        flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;
    }
    .lp-footer-l { font-size: 0.73rem; color: var(--text-color); opacity: 0.55; line-height: 1.7; }
    .lp-footer-r { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-color); opacity: 0.45; text-align: right; line-height: 1.8; }
    .lp-footer-links { display: flex; gap: 1.2rem; flex-wrap: wrap; padding-top: 0.6rem; border-top: 1px solid rgba(128,128,128,0.15); }
    .lp-footer-link {
        font-size: 0.68rem; font-weight: 500; color: #2563EB; opacity: 0.75;
        text-decoration: none; font-family: 'Inter', sans-serif; transition: opacity 0.12s;
    }
    .lp-footer-link:hover { opacity: 1; }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=300)
def _load_findings():
    from dashboard.database import get_db, is_offline_mode, _snap
    try:
        if is_offline_mode():
            df = _snap()
            if df.empty:
                return {}
            early = df[df["booking_horizon_days"] >= 60]["price_eur"].mean()
            late  = df[df["booking_horizon_days"] <= 7]["price_eur"].mean()
            discount = ((late - early) / early * 100) if early > 0 else 0
            grp = df.groupby(["origin_name", "destination_name"])["price_eur"].agg(
                low="min", high="max", n="count")
            grp = grp[grp["n"] >= 30]
            spread_route, spread_low, spread_high, spread_pct = ("–", "–"), 0.0, 0.0, 0.0
            if not grp.empty:
                grp["spread_pct"] = (grp["high"] - grp["low"]) / grp["low"] * 100
                spread_route = grp["spread_pct"].idxmax()
                spread_low   = float(grp.loc[spread_route, "low"])
                spread_high  = float(grp.loc[spread_route, "high"])
                spread_pct   = float(grp.loc[spread_route, "spread_pct"])
            top_route      = df.groupby(["origin_name","destination_name"]).size().idxmax()
            top_route_count= df.groupby(["origin_name","destination_name"]).size().max()
            days_span      = (df["collected_at"].max() - df["collected_at"].min()).days
            return {
                "discount": discount,
                "spread_route": spread_route, "spread_low": spread_low,
                "spread_high": spread_high, "spread_pct": spread_pct,
                "top_route": top_route, "top_route_count": top_route_count,
                "days_span": days_span,
                "first_date": df["collected_at"].min(),
                "last_date":  df["collected_at"].max(),
            }
        db = get_db()
        if db is None:
            return {}
        r  = db.query("SELECT AVG(price_eur) FILTER (WHERE booking_horizon_days >= 60) as early_avg, AVG(price_eur) FILTER (WHERE booking_horizon_days <= 7) as late_avg FROM price_observations WHERE booking_horizon_days IS NOT NULL").iloc[0]
        rp = db.query("""
            SELECT origin_name, destination_name, MIN(price_eur) as low, MAX(price_eur) as high
            FROM price_observations
            GROUP BY origin_name, destination_name
            HAVING COUNT(*) >= 30 AND MIN(price_eur) > 0
            ORDER BY (MAX(price_eur) - MIN(price_eur)) / MIN(price_eur) DESC
            LIMIT 1
        """)
        rr = db.query("SELECT origin_name, destination_name, COUNT(*) as n FROM price_observations GROUP BY origin_name, destination_name ORDER BY n DESC LIMIT 1").iloc[0]
        rs = db.query("SELECT MIN(collected_at) as first, MAX(collected_at) as last FROM price_observations").iloc[0]
        discount = ((r["late_avg"] - r["early_avg"]) / r["early_avg"] * 100) if r["early_avg"] else 0
        if not rp.empty:
            rp0 = rp.iloc[0]
            spread_route = (rp0["origin_name"], rp0["destination_name"])
            spread_low, spread_high = float(rp0["low"]), float(rp0["high"])
            spread_pct = (spread_high - spread_low) / spread_low * 100 if spread_low > 0 else 0.0
        else:
            spread_route, spread_low, spread_high, spread_pct = ("–", "–"), 0.0, 0.0, 0.0
        return {
            "discount": discount,
            "spread_route": spread_route, "spread_low": spread_low,
            "spread_high": spread_high, "spread_pct": spread_pct,
            "top_route": (rr["origin_name"], rr["destination_name"]),
            "top_route_count": int(rr["n"]),
            "days_span": (pd.Timestamp(rs["last"]) - pd.Timestamp(rs["first"])).days,
            "first_date": rs["first"],
            "last_date":  rs["last"],
        }
    except Exception:
        return {}


@st.cache_data(ttl=600)
def _load_operator_dateranges():
    from dashboard.database import get_db, is_offline_mode, _snap
    try:
        if is_offline_mode():
            df = _snap()
            if df.empty:
                return pd.DataFrame()
            return df.groupby("operator")["collected_at"].agg(first="min", last="max").reset_index()
        db = get_db()
        if db is None:
            return pd.DataFrame()
        return db.query("SELECT operator, MIN(collected_at) as first, MAX(collected_at) as last FROM price_observations GROUP BY operator")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def _load_density_grid():
    from dashboard.database import get_db, is_offline_mode, _snap
    try:
        if is_offline_mode():
            df = _snap()
            if df.empty:
                return pd.DataFrame()
            return df.groupby(["operator","booking_horizon_days"]).size().reset_index(name="n")
        db = get_db()
        if db is None:
            return pd.DataFrame()
        return db.query("SELECT operator, booking_horizon_days, COUNT(*) as n FROM price_observations WHERE booking_horizon_days IS NOT NULL GROUP BY operator, booking_horizon_days")
    except Exception:
        return pd.DataFrame()


def _build_growth_chart(daily_df, findings):
    if daily_df.empty:
        return None
    total_per_day = daily_df.groupby("col_date")["records"].sum().reset_index().sort_values("col_date")
    total_per_day["cumulative"] = total_per_day["records"].cumsum()
    total_per_day["col_date"]   = pd.to_datetime(total_per_day["col_date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=total_per_day["col_date"], y=total_per_day["cumulative"],
        mode="lines", fill="tozeroy",
        fillcolor="rgba(37,99,235,0.06)",
        line=dict(color="#2563EB", width=1.8),
        hovertemplate="<b>%{x|%d.%m.%Y}</b><br>%{y:,.0f} Beobachtungen<extra></extra>",
    ))

    if not total_per_day.empty:
        x_min = total_per_day["col_date"].min()
        x_max = total_per_day["col_date"].max()
        shapes, annotations = [], []
        for date_str, label in _ANNOTATIONS:
            dt = pd.Timestamp(date_str)
            if not (x_min <= dt <= x_max):
                continue
            closest = total_per_day[total_per_day["col_date"] <= dt]
            if closest.empty:
                continue
            y_val = float(closest.iloc[-1]["cumulative"])
            shapes.append(dict(type="line", x0=dt, x1=dt, y0=0, y1=y_val,
                               line=dict(color="rgba(128,128,128,0.2)", width=1, dash="dot")))
            annotations.append(dict(
                x=dt, y=y_val, text=f"<b>{label}</b>",
                showarrow=True, arrowhead=0, arrowwidth=1,
                arrowcolor="rgba(128,128,128,0.3)", ax=0, ay=-28,
                font=dict(size=9, color="rgba(128,128,128,0.55)"),
                bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
            ))
        fig.update_layout(shapes=shapes, annotations=annotations)

    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showline=False,
                   tickfont=dict(size=9, color="rgba(128,128,128,0.45)")),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.07)", zeroline=False,
                   tickfont=dict(size=9, color="rgba(128,128,128,0.45)"), tickformat=","),
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=240, hovermode="x unified", showlegend=False,
    )
    return fig


def _build_density_html(density_df, T):
    if density_df.empty:
        return "<p style='opacity:0.4;font-size:0.8rem'>Keine Daten</p>"
    operators = sorted(density_df["operator"].unique())
    horizons  = sorted(density_df["booking_horizon_days"].unique(), reverse=True)
    pivot = density_df.pivot(index="operator", columns="booking_horizon_days", values="n").fillna(0)
    max_n = pivot.values.max() if pivot.values.max() > 0 else 1

    html = '<div class="lp-density-wrap"><table class="lp-density-table"><thead><tr>'
    html += '<th class="row-head">Anbieter</th>'
    for h in horizons:
        html += f'<th>+{int(h)}</th>'
    html += '</tr></thead><tbody>'
    for op in operators:
        html += f'<tr><td class="row-head">{op_label(op)}</td>'
        for h in horizons:
            n     = pivot.loc[op, h] if op in pivot.index and h in pivot.columns else 0
            ratio = n / max_n
            cls   = "lp-cell-full" if ratio >= 0.6 else ("lp-cell-part" if ratio >= 0.1 else "lp-cell-empty")
            html += f'<td><span class="{cls}" title="{int(n)} Beob."></span></td>'
        html += '</tr>'
    html += '</tbody></table></div>'

    html += f"""
    <div style="font-size:0.6rem;color:var(--text-color);opacity:0.25;margin-top:0.5rem;display:flex;gap:0.8rem;align-items:center;">
        <span><span style="display:inline-block;width:10px;height:10px;background:rgba(37,99,235,0.55);border-radius:2px;margin-right:3px;vertical-align:middle"></span>{T["lp_density_good"]}</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:rgba(37,99,235,0.2);border-radius:2px;margin-right:3px;vertical-align:middle"></span>{T["lp_density_partial"]}</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:rgba(128,128,128,0.08);border-radius:2px;margin-right:3px;vertical-align:middle"></span>{T["lp_density_sparse"]}</span>
    </div>"""
    return html


def render_landing(T):
    _css()

    overview   = load_crawler_overview()
    df_ops     = load_crawler_stats_by_operator()
    df_daily   = load_crawler_daily_counts(days_back=120)
    findings   = _load_findings()
    density_df = _load_density_grid()
    dateranges = _load_operator_dateranges()

    dr_lookup = {}
    if not dateranges.empty:
        for _, row in dateranges.iterrows():
            try:
                dr_lookup[row["operator"]] = (
                    f"{pd.Timestamp(row['first']).strftime('%d.%m.%y')} – "
                    f"{pd.Timestamp(row['last']).strftime('%d.%m.%y')}"
                )
            except Exception:
                dr_lookup[row["operator"]] = "–"

    total_records  = int(overview.iloc[0]["total_records"]) if not overview.empty else 0
    n_operators    = int(overview.iloc[0]["n_operators"])   if not overview.empty else 0
    n_routes       = int(overview.iloc[0]["n_routes"])      if not overview.empty else 0
    last_collected = overview.iloc[0]["last_collected"]     if not overview.empty else None

    # ══════════════════════════════════════════════════════════
    # HERO
    # ══════════════════════════════════════════════════════════
    col_hero, col_kpis = st.columns([3, 2], gap="large")
    with col_hero:
        st.markdown(f"""
        <div class="lp-eyebrow">{T["lp_eyebrow"]}</div>
        <h1 class="lp-title">Rail Data Hub</h1>
        <p class="lp-subtitle">{T["lp_subtitle"]}</p>
        """, unsafe_allow_html=True)

    with col_kpis:
        st.markdown("<br>", unsafe_allow_html=True)
        rec_fmt = f"{total_records:,}".replace(",", ".")
        if findings.get("first_date"):
            try:
                first_str = pd.Timestamp(findings["first_date"]).strftime("%d.%m.%Y")
                today_str = pd.Timestamp.now().strftime("%d.%m.%Y")
                span_str  = f"{first_str}<br><span style='opacity:0.5;font-size:0.9rem'>– {today_str}</span>"
            except Exception:
                span_str = "–"
        else:
            span_str = "–"

        st.markdown(f"""
        <div class="lp-kpi-grid">
            <div class="lp-kpi">
                <div class="lp-kpi-value">{rec_fmt}</div>
                <div class="lp-kpi-label">{T["lp_kpi_obs"]}</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value">{n_operators}</div>
                <div class="lp-kpi-label">{T["lp_kpi_ops"]}</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value">{n_routes}</div>
                <div class="lp-kpi-label">{T["lp_kpi_routes"]}</div>
            </div>
            <div class="lp-kpi">
                <div class="lp-kpi-value" style="font-size:1.1rem;line-height:1.4">{span_str}</div>
                <div class="lp-kpi-label">{T["lp_kpi_period"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # HIGHLIGHT FINDINGS
    # ══════════════════════════════════════════════════════════
    if findings:
        st.markdown(f'<div class="lp-section-label">{T["lp_sec_findings"]}</div>', unsafe_allow_html=True)

        discount      = findings.get("discount", 0)
        spread_route  = findings.get("spread_route", ("–", "–"))
        spread_low    = findings.get("spread_low", 0)
        spread_high   = findings.get("spread_high", 0)
        spread_pct    = findings.get("spread_pct", 0)
        top_route     = findings.get("top_route", ("–", "–"))
        top_count     = findings.get("top_route_count", 0)
        discount_abs  = abs(discount)
        discount_dir  = T["lp_finding_more_exp"] if discount > 0 else T["lp_finding_cheaper"]
        lang = st.session_state.lang
        top_route_str = (f"{station_name(top_route[0], lang)} → {station_name(top_route[1], lang)}"
                          if isinstance(top_route, tuple) else str(top_route))
        spread_route_str = (f"{station_name(spread_route[0], lang)} → {station_name(spread_route[1], lang)}"
                             if isinstance(spread_route, tuple) else str(spread_route))
        top_count_fmt = f"{top_count:,}".replace(",", ".")
        spread_color = "#ff5f5f"

        top_ops = []
        if not df_ops.empty and isinstance(top_route, tuple):
            rl = load_route_list()
            if not rl.empty:
                match = rl[(rl["origin_name"] == top_route[0]) & (rl["destination_name"] == top_route[1])]
                if not match.empty:
                    top_ops = match.iloc[0]["operators"]
        top_color = op_color(top_ops[0]) if top_ops else "#2563EB"

        early_text = T["lp_finding_early_text"].format(pct=discount_abs, dir=discount_dir)
        cheap_text = T["lp_finding_cheap_text"].format(route=spread_route_str, low=spread_low, high=spread_high)
        route_text = T["lp_finding_route_text"].format(route=top_route_str)

        st.markdown(f"""
        <div class="lp-findings-grid">
            <div class="lp-finding" style="border-left-color:#2563EB">
                <div class="lp-finding-label">{T["lp_finding_early"]}</div>
                <div class="lp-finding-value">
                    <span class="lp-finding-accent" style="color:#2563EB">+{discount_abs:.1f}%</span>
                </div>
                <div class="lp-finding-sub">{early_text}</div>
            </div>
            <div class="lp-finding" style="border-left-color:{spread_color}">
                <div class="lp-finding-label">{T["lp_finding_cheap"]}</div>
                <div class="lp-finding-value">
                    <span class="lp-finding-accent" style="color:{spread_color}">+{spread_pct:.0f}%</span>
                </div>
                <div class="lp-finding-sub">{cheap_text}</div>
            </div>
            <div class="lp-finding" style="border-left-color:{top_color}">
                <div class="lp-finding-label">{T["lp_finding_route"]}</div>
                <div class="lp-finding-value">
                    <span class="lp-finding-accent" style="color:{top_color}">{top_count_fmt}</span>
                </div>
                <div class="lp-finding-sub">{route_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # WACHSTUMSKURVE + DATENDICHTE
    # ══════════════════════════════════════════════════════════
    st.markdown(f'<div class="lp-section-label">{T["lp_sec_growth"]}</div>', unsafe_allow_html=True)

    col_growth, col_density = st.columns([3, 2], gap="large")

    with col_growth:
        st.markdown(f"""
        <div style="font-size:0.72rem;color:var(--text-color);opacity:0.4;
                    margin-bottom:0.4rem;font-family:'Inter',sans-serif;">
            {T["lp_growth_caption"]}
        </div>
        """, unsafe_allow_html=True)
        if not df_daily.empty:
            fig_growth = _build_growth_chart(df_daily, findings)
            if fig_growth:
                st.plotly_chart(fig_growth, use_container_width=True,
                                config={"displayModeBar": False})
        else:
            st.info("Keine Zeitreihendaten verfügbar.")

    with col_density:
        st.markdown(f"""
        <div style="font-size:0.72rem;color:var(--text-color);opacity:0.4;
                    margin-bottom:0.4rem;font-family:'Inter',sans-serif;">
            {T["lp_density_caption"]}
        </div>
        """, unsafe_allow_html=True)
        st.markdown(_build_density_html(density_df, T), unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # BETREIBER
    # ══════════════════════════════════════════════════════════
    st.markdown(f'<div class="lp-section-label">{T["lp_sec_operators"]}</div>', unsafe_allow_html=True)

    if not df_ops.empty:
        df_sorted = df_ops.sort_values("records", ascending=False)
        for row_df in [df_sorted.iloc[:5], df_sorted.iloc[5:]]:
            if row_df.empty:
                continue
            cols = st.columns(5)
            for col, (_, r) in zip(cols, row_df.iterrows()):
                op        = r["operator"]
                meta      = _OPERATOR_META.get(op, {"flag": "🚆", "country": "–", "type": "–"})
                color     = op_color(op)
                name      = op_label(op)
                count     = f"{int(r['records']):,}".replace(",", ".")
                daterange = dr_lookup.get(op, "–")
                with col:
                    st.markdown(f"""
                    <div class="lp-op-card">
                        <div class="lp-op-stripe" style="background:{color}"></div>
                        <div class="lp-op-body">
                            <div class="lp-op-flag">{meta['flag']}</div>
                            <div class="lp-op-name">{name}</div>
                            <div class="lp-op-type">{meta['country']} · {meta['type']}</div>
                            <div class="lp-op-count">{count}</div>
                            <div class="lp-op-count-label">{T["lp_observations"]}</div>
                            <div class="lp-op-daterange">{daterange}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # DATENERHEBUNG
    # ══════════════════════════════════════════════════════════
    st.markdown(f'<div class="lp-section-label">{T["lp_sec_collection"]}</div>', unsafe_allow_html=True)

    steps = list(zip(["01", "02", "03", "04"], T["lp_steps_titles"], T["lp_steps_descs"]))
    flow_html = '<div class="lp-flow">'
    for i, (num, title, desc) in enumerate(steps):
        flow_html += f"""
        <div class="lp-flow-step">
            <div class="lp-flow-num">{num}</div>
            <div class="lp-flow-title">{title}</div>
            <div class="lp-flow-desc">{desc}</div>
        </div>"""
        if i < len(steps) - 1:
            flow_html += '<div class="lp-flow-arrow">→</div>'
    flow_html += '</div>'
    st.markdown(flow_html, unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:0.65rem;color:var(--text-color);opacity:0.3;margin-bottom:0.3rem;'
        f'font-family:Inter,sans-serif;letter-spacing:0.1em;text-transform:uppercase;">'
        f'{T["lp_hz_label"]}</div>'
        '<div class="lp-hz-row">' +
        "".join(f'<span class="lp-hz">{h}</span>' for h in _HORIZONS) +
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # ANALYSE-MODULE
    # ══════════════════════════════════════════════════════════
    st.markdown(f'<div class="lp-section-label">{T["lp_sec_modules"]}</div>', unsafe_allow_html=True)

    _modules = list(zip(T["lp_mod_names"], _MODULE_CHART_TYPES, T["lp_mod_questions"], T["lp_mod_details"]))

    def _mod_card(name, chart_type, question, detail):
        return f"""
        <div class="lp-mod-card">
            <div class="lp-mod-icon">{_CHART_ICONS.get(chart_type, "")}</div>
            <div>
                <div class="lp-mod-name">{name}</div>
                <div class="lp-mod-question">{question}</div>
            </div>
            <div class="lp-mod-desc">{detail}</div>
        </div>"""

    st.markdown(
        '<div class="lp-mod-grid">'        + "".join(_mod_card(*m) for m in _modules[:4]) + '</div>' +
        '<div class="lp-mod-grid-bottom">' + "".join(_mod_card(*m) for m in _modules[4:]) + '</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="lp-rule"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # METHODIK
    # ══════════════════════════════════════════════════════════
    st.markdown(f'<div class="lp-section-label">{T["lp_sec_method"]}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(f'<div class="lp-method">{T["lp_method_left"]}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="lp-method">{T["lp_method_right"]}</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════
    last_str = (
        pd.Timestamp(last_collected).strftime("%d.%m.%Y, %H:%M UTC")
        if last_collected is not None else "–"
    )
    st.markdown(f"""
    <div class="lp-footer">
        <div class="lp-footer-top">
            <div class="lp-footer-l">
                Rail Data Hub · Karlsruher Institut für Technologie<br>
                {T["lp_footer_sub"]}
            </div>
            <div class="lp-footer-r">
                {T["lp_footer_last"]}: {last_str}<br>
                {T["lp_footer_tech"]}
            </div>
        </div>
        <div class="lp-footer-links">
            <a class="lp-footer-link" href="https://github.com/Xaver-M/Rail-Data-Hub" target="_blank">
                {T["lp_footer_github"]}
            </a>
            <a class="lp-footer-link" href="https://www.kit.edu" target="_blank">
                {T["lp_footer_kit"]}
            </a>
            <a class="lp-footer-link" href="https://www.wiwi.kit.edu" target="_blank">
                {T["lp_footer_inst"]}
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)