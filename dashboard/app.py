# dashboard/app.py
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.config import TEXTS, CUSTOM_CSS, op_color, op_label, time_since
from dashboard.database import load_route_list
from dashboard.views.landing import render_landing

st.set_page_config(
    page_title="Rail Data Hub",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Globale Basis ── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.15) !important;
    min-width: 280px !important;
    max-width: 280px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 1.4rem 1rem !important;
}

/* ── Sidebar Logo ── */
.rdh-logo-eye {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.35;
    margin-bottom: 0.2rem;
}
.rdh-logo-title {
    font-family: 'Inter', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-color);
    letter-spacing: -0.02em;
    margin-bottom: 0.1rem;
    line-height: 1.2;
}
.rdh-logo-sub {
    font-size: 0.72rem;
    color: var(--text-color);
    opacity: 0.4;
    line-height: 1.5;
    margin-bottom: 1.4rem;
}

/* ── Nav-Buttons ── */
.rdh-nav-section {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.3;
    margin: 1rem 0 0.4rem 0.1rem;
}

/* Streamlit-Buttons in Sidebar neutral stylen */
section[data-testid="stSidebar"] .stButton button {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    border: none !important;
    text-align: left !important;
    padding: 0.45rem 0.75rem !important;
    width: 100% !important;
    transition: background 0.1s !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
    background: transparent !important;
    color: var(--text-color) !important;
    opacity: 0.65;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
    background: rgba(128,128,128,0.08) !important;
    opacity: 1;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: rgba(37,99,235,0.1) !important;
    color: #2563EB !important;
    opacity: 1 !important;
    font-weight: 600 !important;
}

/* ── Route-Picker ── */
.rdh-picker {
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 8px;
    padding: 1rem 1.2rem 0.8rem 1.2rem;
    margin-bottom: 1.2rem;
    background: var(--secondary-background-color);
}
.rdh-picker-eyebrow {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.4;
    margin-bottom: 0.7rem;
}
.rdh-field-label {
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-color);
    opacity: 0.45;
    margin-bottom: 0.25rem;
}
.rdh-arrow {
    text-align: center;
    padding-top: 1.55rem;
    font-size: 1rem;
    color: #2563EB;
    opacity: 0.7;
}

/* ── Operator-Badges im Picker ── */
.rdh-badges-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.1rem;
}
.rdh-badge {
    font-size: 0.67rem;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
    padding: 0.15rem 0.55rem;
    border-radius: 4px;
    border: 1px solid;
    background: transparent;
    line-height: 1.5;
}
.rdh-picker-stat {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.67rem;
    color: var(--text-color);
    opacity: 0.4;
    margin-top: 0.45rem;
}
.rdh-picker-stat b {
    color: var(--text-color);
    opacity: 1;
    font-weight: 600;
}

/* ── Sidebar Mini-Stats ── */
.rdh-sidebar-stat {
    font-size: 0.67rem;
    color: var(--text-color);
    opacity: 0.4;
    line-height: 1.8;
    font-family: 'JetBrains Mono', monospace;
}
.rdh-sidebar-stat strong {
    color: var(--text-color);
    opacity: 1;
    font-size: 0.9rem;
    font-weight: 600;
    display: block;
}

/* ── Divider ── */
.rdh-divider {
    height: 1px;
    background: rgba(128,128,128,0.12);
    margin: 0.9rem 0;
}

/* Selectbox-Labels ausblenden (eigene Labels davor) */
div[data-testid="stSelectbox"] label { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────
for key, val in [
    ("lang", "de"),
    ("current_view", "landing"),
    ("selected_origin", None),
    ("selected_destination", None),
]:
    if key not in st.session_state:
        st.session_state[key] = val

T = TEXTS[st.session_state.lang]

# ── Routen laden ──────────────────────────────────────────────
routes_df = load_route_list()
if routes_df.empty:
    st.error(T["no_data"])
    st.stop()

# ── Cascading-Logik ───────────────────────────────────────────
all_origins = sorted(routes_df["origin_name"].dropna().unique().tolist())
if st.session_state.selected_origin not in all_origins:
    st.session_state.selected_origin = all_origins[0]

destinations_for_origin = sorted(
    routes_df[routes_df["origin_name"] == st.session_state.selected_origin]["destination_name"]
    .dropna().unique().tolist()
)
# Sofort auf validen Wert setzen – verhindert inkonsistenten Zustand im Picker
if (st.session_state.selected_destination not in destinations_for_origin
        and destinations_for_origin):
    st.session_state.selected_destination = destinations_for_origin[0]

current_route_df = routes_df[
    (routes_df["origin_name"] == st.session_state.selected_origin) &
    (routes_df["destination_name"] == st.session_state.selected_destination)
]
current_route = current_route_df.iloc[0] if not current_route_df.empty else None

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="rdh-logo-eye">KIT · Inst. f. Wirtschaftswiss.</div>
    <div class="rdh-logo-title">Rail Data Hub</div>
    <div class="rdh-logo-sub">Preisbeobachtung im<br>Schienenpersonenverkehr</div>
    """, unsafe_allow_html=True)

    # Sprache
    cl, cr = st.columns(2)
    if cl.button("🇩🇪 DE", use_container_width=True,
                 type="primary" if st.session_state.lang == "de" else "secondary"):
        st.session_state.lang = "de"
        st.rerun()
    if cr.button("🇬🇧 EN", use_container_width=True,
                 type="primary" if st.session_state.lang == "en" else "secondary"):
        st.session_state.lang = "en"
        st.rerun()

    st.markdown('<div class="rdh-divider"></div>', unsafe_allow_html=True)

    from dashboard.database import is_offline_mode
    if is_offline_mode():
        st.warning("⚠ Offline · lokaler Snapshot", icon="⚠")
    else:
        st.caption("⚡ Live · TimescaleDB")

    st.markdown('<div class="rdh-nav-section">Navigation</div>', unsafe_allow_html=True)

    nav_items = [
        ("landing",  "Start"),
        ("tabs",     "Analyse"),
        ("operator", "Anbietervergleich"),
        ("crawler",  "Crawler-Status"),
    ]
    for view_key, label in nav_items:
        is_active = st.session_state.current_view == view_key
        if st.button(label, key=f"nav_{view_key}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.current_view = view_key
            st.rerun()

    st.markdown('<div class="rdh-divider"></div>', unsafe_allow_html=True)

    if current_route is not None:
        rec_fmt = f"{int(current_route['record_count']):,}".replace(",", ".")
        last_fmt = time_since(current_route["last_collected"], T)
        st.markdown(f"""
        <div class="rdh-sidebar-stat">
            Beobachtungen<br>
            <strong>{rec_fmt}</strong>
            Stand: {last_fmt}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="rdh-divider"></div>', unsafe_allow_html=True)

    if st.button("Daten neu laden", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════
if st.session_state.current_view == "landing":
    render_landing(T)

# ══════════════════════════════════════════════════════════════
# ANALYSE-VIEWS — Route-Picker oben
# ══════════════════════════════════════════════════════════════
else:
    # ── Route-Picker ──────────────────────────────────────────
    st.markdown('<div class="rdh-picker">', unsafe_allow_html=True)
    st.markdown('<div class="rdh-picker-eyebrow">Strecke</div>', unsafe_allow_html=True)

    col_orig, col_arr, col_dest, col_meta = st.columns([5, 1, 5, 5])

    with col_orig:
        st.markdown('<div class="rdh-field-label">Abfahrt</div>', unsafe_allow_html=True)
        new_origin = st.selectbox(
            "origin", options=all_origins,
            index=all_origins.index(st.session_state.selected_origin)
                  if st.session_state.selected_origin in all_origins else 0,
            key="sb_origin", label_visibility="collapsed"
        )
        if new_origin != st.session_state.selected_origin:
            st.session_state.selected_origin = new_origin
            # Sofort erste valide Destination der neuen Origin setzen
            new_dests = sorted(
                routes_df[routes_df["origin_name"] == new_origin]["destination_name"]
                .dropna().unique().tolist()
            )
            st.session_state.selected_destination = new_dests[0] if new_dests else None
            st.rerun()

    with col_arr:
        st.markdown('<div class="rdh-arrow">→</div>', unsafe_allow_html=True)

    with col_dest:
        st.markdown('<div class="rdh-field-label">Ankunft</div>', unsafe_allow_html=True)
        new_dest = st.selectbox(
            "dest", options=destinations_for_origin,
            index=destinations_for_origin.index(st.session_state.selected_destination)
                  if st.session_state.selected_destination in destinations_for_origin else 0,
            key="sb_dest", label_visibility="collapsed"
        )
        if new_dest != st.session_state.selected_destination:
            st.session_state.selected_destination = new_dest
            st.rerun()

    with col_meta:
        if current_route is not None:
            ops = current_route["operators"]
            badges = "".join([
                f'<span class="rdh-badge" style="color:{op_color(o)};border-color:{op_color(o)};">'
                f'{op_label(o)}</span>'
                for o in ops
            ])
            rec_fmt = f"{int(current_route['record_count']):,}".replace(",", ".")
            last_fmt = time_since(current_route["last_collected"], T)
            st.markdown(f"""
            <div style="padding-top:0.25rem">
                <div class="rdh-field-label">Anbieter</div>
                <div class="rdh-badges-wrap">{badges}</div>
                <div class="rdh-picker-stat">{rec_fmt} Beobachtungen &nbsp;·&nbsp; {last_fmt}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if current_route is None:
        st.info("Keine Daten für diese Strecke.")
        st.stop()

    # ── View-Routing ──────────────────────────────────────────
    if st.session_state.current_view == "tabs":
        tabs = st.tabs([
            T["tab_overview"],
            T["tab_train"],
            T["tab_horizon"],
            T["tab_daytime"],
            T["tab_normalized"],
        ])
        with tabs[0]:
            from dashboard.views.overview import render_overview
            render_overview(current_route, T)
        with tabs[1]:
            from dashboard.views.individual_train import render_individual_train
            render_individual_train(current_route, T)
        with tabs[2]:
            from dashboard.views.booking_horizon import render_booking_horizon
            render_booking_horizon(current_route, T)
        with tabs[3]:
            from dashboard.views.time_of_day import render_time_of_day
            render_time_of_day(current_route, T)
        with tabs[4]:
            from dashboard.views.normalized_prices import render_normalized_prices
            render_normalized_prices(current_route, T)

    elif st.session_state.current_view == "operator":
        from dashboard.views.operator_comp import render_operator_comparison
        render_operator_comparison(current_route, T)

    elif st.session_state.current_view == "crawler":
        from dashboard.views.crawler_status import render_crawler_status
        render_crawler_status(T)