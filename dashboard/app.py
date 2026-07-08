# dashboard/app.py
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.config import TEXTS, CUSTOM_CSS, op_color, op_label, time_since, station_name
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

section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.15) !important;
    min-width: 280px !important;
    max-width: 280px !important;
}
section[data-testid="stSidebar"] > div { padding: 1.4rem 1rem !important; }

.rdh-logo-eye {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--text-color); opacity: 0.35; margin-bottom: 0.2rem;
}
.rdh-logo-title {
    font-family: 'Inter', sans-serif; font-size: 1.15rem; font-weight: 700;
    color: var(--text-color); letter-spacing: -0.02em; margin-bottom: 0.1rem; line-height: 1.2;
}
.rdh-logo-sub { font-size: 0.72rem; color: var(--text-color); opacity: 0.4; line-height: 1.5; margin-bottom: 1.4rem; }
.rdh-nav-section {
    font-size: 0.65rem; font-weight: 600; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--text-color); opacity: 0.3; margin: 1rem 0 0.4rem 0.1rem;
}
section[data-testid="stSidebar"] .stButton button {
    font-family: 'Inter', sans-serif !important; font-size: 0.88rem !important;
    font-weight: 500 !important; border-radius: 6px !important; border: none !important;
    text-align: left !important; padding: 0.45rem 0.75rem !important;
    width: 100% !important; transition: background 0.1s !important; box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"] {
    background: transparent !important; color: var(--text-color) !important; opacity: 0.65;
}
section[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
    background: rgba(128,128,128,0.08) !important; opacity: 1;
}
section[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: rgba(37,99,235,0.1) !important; color: #2563EB !important;
    opacity: 1 !important; font-weight: 600 !important;
}

/* Route-Picker */
.rdh-picker {
    border: 1px solid rgba(128,128,128,0.15); border-radius: 8px;
    padding: 1rem 1.2rem 0.8rem 1.2rem; margin-bottom: 1.2rem;
    background: var(--secondary-background-color);
}
.rdh-picker-eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--text-color); opacity: 0.4; margin-bottom: 0.7rem;
}
.rdh-field-label {
    font-size: 0.76rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--text-color); opacity: 0.45; margin-bottom: 0.25rem;
}
.rdh-arrow { text-align: center; padding-top: 1.55rem; font-size: 1rem; color: #2563EB; opacity: 0.7; }
.rdh-badges-wrap { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.1rem; }
.rdh-badge {
    font-size: 0.67rem; font-weight: 500; font-family: 'Inter', sans-serif;
    padding: 0.15rem 0.55rem; border-radius: 4px; border: 1px solid; background: transparent; line-height: 1.5;
}
.rdh-picker-stat {
    font-family: 'JetBrains Mono', monospace; font-size: 0.67rem;
    color: var(--text-color); opacity: 0.4; margin-top: 0.45rem;
}
.rdh-sidebar-stat { font-size: 0.67rem; color: var(--text-color); opacity: 0.4; line-height: 1.8; font-family: 'JetBrains Mono', monospace; }
.rdh-sidebar-stat strong { color: var(--text-color); opacity: 1; font-size: 0.9rem; font-weight: 600; display: block; }
.rdh-divider { height: 1px; background: rgba(128,128,128,0.12); margin: 0.9rem 0; }

div[data-testid="stSelectbox"] label { display: none !important; }
div[data-testid="stMultiSelect"] label { font-size: 0.72rem !important; opacity: 0.5; }
</style>
""", unsafe_allow_html=True)

# ── Länder-Mapping ────────────────────────────────────────────────
_COUNTRY_KEYWORDS = {
    "🇩🇪 Deutschland":  ["Berlin", "München", "Hamburg", "Frankfurt", "Köln", "Stuttgart",
                         "Basel", "Mannheim", "Nürnberg", "Leipzig", "Dresden", "Bremen",
                         "Hannover", "Dortmund", "Essen", "Duisburg", "Karlsruhe", "Augsburg",
                         "Wiesbaden", "Münster", "Bonn", "Freiburg", "Kiel", "Bielefeld"],
    "🇮🇹 Italien":      ["Roma", "Milano", "Napoli", "Torino", "Bologna", "Firenze",
                         "Venezia", "Genova", "Verona", "Padova", "Trieste", "Brescia",
                         "Modena", "Parma", "Perugia", "Ravenna", "Livorno", "Cagliari"],
    "🇫🇷 Frankreich":   ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes",
                         "Strasbourg", "Montpellier", "Rennes", "Grenoble", "Dijon", "Toulon"],
    "🇪🇸 Spanien":      ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga",
                         "Bilbao", "Alicante", "Córdoba", "Valladolid", "Vigo", "Granada"],
    "🇨🇿 Tschechien":   ["Praha", "Brno", "Ostrava", "Plzeň", "Olomouc", "České",
                         "Pardubice", "Liberec", "Hradec", "Zlín"],
    "🇦🇹 Österreich":   ["Wien", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt",
                         "Villach", "Wels", "Dornbirn", "Steyr"],
    "🇸🇰 Slowakei":     ["Bratislava", "Košice", "Prešov", "Žilina", "Nitra"],
    "🇭🇺 Ungarn":       ["Budapest", "Debrecen", "Miskolc", "Szeged", "Pécs"],
}

def _get_country(station_name: str) -> str:
    for country, keywords in _COUNTRY_KEYWORDS.items():
        if any(kw.lower() in station_name.lower() for kw in keywords):
            return country
    return "🌍 Andere"

# ── Session State ─────────────────────────────────────────────────
for key, val in [
    ("lang", "de"),
    ("current_view", "landing"),
    ("selected_origin", None),
    ("selected_destination", None),
    ("filter_countries", []),
    ("filter_operators", []),
]:
    if key not in st.session_state:
        st.session_state[key] = val

T = TEXTS[st.session_state.lang]

# ── Routen laden ──────────────────────────────────────────────────
routes_df = load_route_list()
if routes_df.empty:
    st.error(T["no_data"])
    st.stop()

# ── Länder und Operatoren aus Routendaten ableiten ────────────────
all_countries = sorted(set(
    _get_country(row["origin_name"])
    for _, row in routes_df.iterrows()
) | set(
    _get_country(row["destination_name"])
    for _, row in routes_df.iterrows()
))

all_operators_in_routes = sorted(set(
    op for ops in routes_df["operators"] for op in ops
))

def _get_operators_for_countries(routes, countries):
    if not countries:
        return sorted(set(op for ops in routes["operators"] for op in ops))
    matching = routes[routes.apply(
        lambda r: _get_country(r["origin_name"]) in countries and
                  _get_country(r["destination_name"]) in countries, axis=1
    )]
    return sorted(set(op for ops in matching["operators"] for op in ops))

# ── Filter anwenden ───────────────────────────────────────────────
filtered_routes = routes_df.copy()

if st.session_state.filter_countries:
    def _route_matches_countries(row):
        orig_country = _get_country(row["origin_name"])
        dest_country = _get_country(row["destination_name"])
        return (orig_country in st.session_state.filter_countries and
                dest_country in st.session_state.filter_countries)
    filtered_routes = filtered_routes[filtered_routes.apply(_route_matches_countries, axis=1)]

if st.session_state.filter_operators:
    filtered_routes = filtered_routes[
        filtered_routes["operators"].apply(
            lambda ops: any(op in st.session_state.filter_operators for op in ops)
        )
    ]

if filtered_routes.empty:
    filtered_routes = routes_df.copy()

# ── Cascading-Logik ───────────────────────────────────────────────
all_origins = sorted(filtered_routes["origin_name"].dropna().unique().tolist())
if st.session_state.selected_origin not in all_origins:
    st.session_state.selected_origin = all_origins[0] if all_origins else None

destinations_for_origin = sorted(
    filtered_routes[filtered_routes["origin_name"] == st.session_state.selected_origin]["destination_name"]
    .dropna().unique().tolist()
)
if st.session_state.selected_destination not in destinations_for_origin:
    st.session_state.selected_destination = destinations_for_origin[0] if destinations_for_origin else None

current_route_df = filtered_routes[
    (filtered_routes["origin_name"] == st.session_state.selected_origin) &
    (filtered_routes["destination_name"] == st.session_state.selected_destination)
]
current_route = current_route_df.iloc[0] if not current_route_df.empty else None

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="rdh-logo-eye">KIT · Inst. f. Wirtschaftswiss.</div>
    <div class="rdh-logo-title">Rail Data Hub</div>
    <div class="rdh-logo-sub">{T["sidebar_sub"]}</div>
    """, unsafe_allow_html=True)

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

    st.markdown(f'<div class="rdh-nav-section">{T["sidebar_nav"]}</div>', unsafe_allow_html=True)

    nav_items = [
        ("landing",  T["nav_start"]),
        ("tabs",     T["nav_analyse"]),
        ("operator", T["nav_compare"]),
        ("crawler",  T["nav_crawler"]),
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
        rec_fmt  = f"{int(current_route['record_count']):,}".replace(",", ".")
        last_fmt = time_since(current_route["last_collected"], T)
        st.markdown(f"""
        <div class="rdh-sidebar-stat">
            {T["sidebar_obs"]}<br>
            <strong>{rec_fmt}</strong>
            {T["sidebar_last"]}: {last_fmt}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="rdh-divider"></div>', unsafe_allow_html=True)

    if st.button(T["reload_data"], use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# LANDING
# ══════════════════════════════════════════════════════════════════
if st.session_state.current_view == "landing":
    render_landing(T)

# ══════════════════════════════════════════════════════════════════
# ANALYSE-VIEWS
# ══════════════════════════════════════════════════════════════════
else:
    # ── Route-Picker ──────────────────────────────────────────────
    st.markdown('<div class="rdh-picker">', unsafe_allow_html=True)
    st.markdown(f'<div class="rdh-picker-eyebrow">{T["picker_route"]}</div>', unsafe_allow_html=True)

    # Filter-Zeile
    col_country, col_operator, col_reset = st.columns([3, 3, 1])

    with col_country:
        new_countries = st.multiselect(
            T["picker_country"], options=all_countries,
            default=st.session_state.filter_countries,
            placeholder=T["picker_all_countries"],
            key="ms_countries"
        )
        if new_countries != st.session_state.filter_countries:
            st.session_state.filter_countries = new_countries
            st.session_state.selected_origin = None
            st.session_state.selected_destination = None
            st.session_state.pop("sb_origin", None)
            st.session_state.pop("sb_dest", None)
            st.rerun()

    with col_operator:
        available_operators = _get_operators_for_countries(routes_df, st.session_state.filter_countries)
        valid_ops = [o for o in st.session_state.filter_operators if o in available_operators]
        if valid_ops != st.session_state.filter_operators:
            st.session_state.filter_operators = valid_ops
        new_operators = st.multiselect(
            T["picker_operators"], options=available_operators,
            default=st.session_state.filter_operators,
            format_func=op_label,
            placeholder=T["picker_all_operators"],
            key="ms_operators"
        )
        if new_operators != st.session_state.filter_operators:
            st.session_state.filter_operators = new_operators
            st.session_state.selected_origin = None
            st.session_state.selected_destination = None
            st.session_state.pop("sb_origin", None)
            st.session_state.pop("sb_dest", None)
            st.rerun()

    def _reset_filters():
        st.session_state.filter_countries = []
        st.session_state.filter_operators = []
        st.session_state.ms_countries = []
        st.session_state.ms_operators = []
        st.session_state.selected_origin = None
        st.session_state.selected_destination = None
        st.session_state.pop("sb_origin", None)
        st.session_state.pop("sb_dest", None)

    with col_reset:
        st.markdown("<div style='padding-top:1.6rem'>", unsafe_allow_html=True)
        st.button(T["picker_reset"], use_container_width=True, type="secondary",
                  on_click=_reset_filters)
        st.markdown("</div>", unsafe_allow_html=True)

    # Routen-Zähler
    n_filtered = len(filtered_routes)
    n_total    = len(routes_df)
    if st.session_state.filter_countries or st.session_state.filter_operators:
        st.caption(f'🔍 {n_filtered} {T["picker_of"]} {n_total} {T["picker_routes"]}')

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Cascading Dropdowns
    col_orig, col_arr, col_dest, col_meta = st.columns([5, 1, 5, 5])

    with col_orig:
        st.markdown(f'<div class="rdh-field-label">{T["from_label"]}</div>', unsafe_allow_html=True)
        new_origin = st.selectbox(
            "origin", options=all_origins,
            index=all_origins.index(st.session_state.selected_origin)
                  if st.session_state.selected_origin in all_origins else 0,
            key="sb_origin", label_visibility="collapsed",
            format_func=lambda n: station_name(n, st.session_state.lang)
        )
        if new_origin != st.session_state.selected_origin:
            st.session_state.selected_origin = new_origin
            new_dests = sorted(
                filtered_routes[filtered_routes["origin_name"] == new_origin]["destination_name"]
                .dropna().unique().tolist()
            )
            st.session_state.selected_destination = new_dests[0] if new_dests else None
            st.session_state.pop("sb_dest", None)
            st.rerun()

    def _swap_route():
        swapped_origin = st.session_state.selected_destination
        swapped_dest = st.session_state.selected_origin
        reverse_exists = not filtered_routes[
            (filtered_routes["origin_name"] == swapped_origin) &
            (filtered_routes["destination_name"] == swapped_dest)
        ].empty
        if swapped_origin in all_origins and reverse_exists:
            st.session_state.selected_origin = swapped_origin
            st.session_state.selected_destination = swapped_dest
            st.session_state.sb_origin = swapped_origin
            st.session_state.sb_dest = swapped_dest
        else:
            st.session_state.swap_warning = True

    with col_arr:
        st.markdown('<div style="padding-top:1.55rem"></div>', unsafe_allow_html=True)
        st.button("⇄", key="btn_swap_route", help=T["swap_route"], use_container_width=True,
                  on_click=_swap_route)

    if st.session_state.pop("swap_warning", False):
        st.toast(T["swap_unavailable"], icon="⚠️")

    with col_dest:
        st.markdown(f'<div class="rdh-field-label">{T["to_label"]}</div>', unsafe_allow_html=True)
        new_dest = st.selectbox(
            "dest", options=destinations_for_origin,
            index=destinations_for_origin.index(st.session_state.selected_destination)
                  if st.session_state.selected_destination in destinations_for_origin else 0,
            key="sb_dest", label_visibility="collapsed",
            format_func=lambda n: station_name(n, st.session_state.lang)
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
            rec_fmt  = f"{int(current_route['record_count']):,}".replace(",", ".")
            last_fmt = time_since(current_route["last_collected"], T)
            st.markdown(f"""
            <div style="padding-top:0.25rem">
                <div class="rdh-field-label">{T["operators_on_route"]}</div>
                <div class="rdh-badges-wrap">{badges}</div>
                <div class="rdh-picker-stat">{rec_fmt} {T["lp_observations"]} · {last_fmt}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if current_route is None:
        st.info(T["no_data"])
        st.stop()

    # ── View-Routing ──────────────────────────────────────────────
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