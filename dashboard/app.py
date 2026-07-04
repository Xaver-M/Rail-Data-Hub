# dashboard/app.py
import streamlit as st
import sys
import os

# Pfade sauber setzen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.config import TEXTS, CUSTOM_CSS, op_color, op_label, time_since
from dashboard.database import load_route_list

# Page-Konfiguration
st.set_page_config(
    page_title="RailDataHub Pro",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Session-State Initialisierung
if "lang" not in st.session_state:
    st.session_state.lang = "de"
if "current_view" not in st.session_state:
    st.session_state.current_view = "tabs"

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR & GLOBAL CONTROLS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🚄 RailDataHub")

    col_l1, col_l2 = st.columns(2)
    if col_l1.button("🇬🇧 English", use_container_width=True, type="primary" if st.session_state.lang == "en" else "secondary"):
        st.session_state.lang = "en"
        st.rerun()
    if col_l2.button("🇩🇪 Deutsch", use_container_width=True, type="primary" if st.session_state.lang == "de" else "secondary"):
        st.session_state.lang = "de"
        st.rerun()

    T = TEXTS[st.session_state.lang]
    st.caption("⚡ TimescaleDB Mode Active")
    st.divider()

    with st.spinner("Loading routes..."):
        routes_df = load_route_list()

    if routes_df.empty:
        st.error(T["no_data"])
        st.stop()

    st.markdown(T["enter_route"])
    c_from, c_to = st.columns(2)
    orig_search = c_from.text_input(T["from_label"], placeholder=T["origin_ph"])
    dest_search = c_to.text_input(T["to_label"], placeholder=T["dest_ph"])

    filtered_df = routes_df
    if orig_search:
        filtered_df = filtered_df[filtered_df["origin_name"].str.contains(orig_search, case=False, na=False)]
    if dest_search:
        filtered_df = filtered_df[filtered_df["destination_name"].str.contains(dest_search, case=False, na=False)]

    if filtered_df.empty:
        st.warning(T["route_not_found"])
        filtered_df = routes_df

    route_labels = filtered_df["label"].tolist()

    if "selected_label" not in st.session_state or st.session_state.selected_label not in route_labels:
        st.session_state.selected_label = route_labels[0]

    selected_label = st.selectbox(
        T["route_label"], options=route_labels,
        index=route_labels.index(st.session_state.selected_label) if st.session_state.selected_label in route_labels else 0,
        label_visibility="collapsed", key="route_selector",
    )
    st.session_state.selected_label = selected_label
    current_route = filtered_df[filtered_df["label"] == selected_label].iloc[0]

    st.divider()
    st.markdown(T["operators_on_route"])
    for op in current_route["operators"]:
        st.markdown(f'<span style="color:{op_color(op)}">●</span> {op_label(op)}', unsafe_allow_html=True)

    st.divider()
    if st.button("📊 Main Content / Tabs", use_container_width=True, type="primary" if st.session_state.current_view == "tabs" else "secondary"):
        st.session_state.current_view = "tabs"
        st.rerun()

    if st.button(T["tab_operator"], use_container_width=True, type="primary" if st.session_state.current_view == "operator" else "secondary"):
        st.session_state.current_view = "operator"
        st.rerun()

    if st.button(T["tab_crawler"], use_container_width=True, type="primary" if st.session_state.current_view == "crawler" else "secondary"):
        st.session_state.current_view = "crawler"
        st.rerun()

    st.divider()
    st.metric(T["data_points"], f"{int(current_route['record_count']):,}".replace(",", "."))
    st.caption(f"{T['last_label']} {time_since(current_route['last_collected'], T)}")
    if st.button(T["reload_data"], use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT ROUTING & UPPER TABS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.current_view == "tabs":
    tab_titles = [
        T["tab_overview"],
        T["tab_train"],
        T["tab_horizon"],
        T["tab_daytime"],
        T["tab_normalized"]
    ]
    tabs = st.tabs(tab_titles)

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