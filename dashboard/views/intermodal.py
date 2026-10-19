# dashboard/views/intermodal.py
# Rail/bus vs. air per corridor (Google Flights data since 19.10.2026):
#   tab 1 = project status (WIP), tab 2 = live preview from the database.
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.config import op_color, op_label, route_label
from dashboard.database import (
    load_intermodal_corridors, load_intermodal_horizon, load_intermodal_daily,
)

MODE_COLORS = {"rail": "#2563EB", "bus": "#18a04b", "air": "#f97316"}
MODE_DASH   = {"rail": "solid", "bus": "dot", "air": "dash"}
BAG_VARIANTS = ["economy_cabinbag", "economy_nobag"]

CORRIDOR_NAMES = {
    "milan-rome":       {"de": "Mailand – Rom",      "en": "Milan – Rome"},
    "madrid-barcelona": {"de": "Madrid – Barcelona", "en": "Madrid – Barcelona"},
    "barcelona-madrid": {"de": "Barcelona – Madrid", "en": "Barcelona – Madrid"},
    "paris-nice":       {"de": "Paris – Nizza",      "en": "Paris – Nice"},
}

# Airport pairs per corridor; flights/day from the local test run on 07.10.2026
# (see config/flight_routes.py). active=False -> dropped, no nonstop flights.
WIP_ROUTES = [
    ("milan-rome",       ("trenitalia", "italo"), "LIN–FCO",                   ("ita_airways",),                    "8–10",  True),
    ("milan-rome",       ("trenitalia", "italo"), "MXP–FCO, BGY–FCO",          (),                                  "0",     False),
    ("milan-rome",       ("trenitalia", "italo"), "LIN–CIA, MXP–CIA, BGY–CIA", (),                                  "0",     False),
    ("madrid-barcelona", ("ouigo_es",),           "MAD–BCN",                   ("iberia", "vueling", "air_europa"), "11–14", True),
    ("barcelona-madrid", ("ouigo_es",),           "BCN–MAD",                   ("iberia", "vueling"),               "~11",   True),
    ("paris-nice",       ("ouigo_fr",),           "ORY–NCE",                   ("transavia", "easyjet"),            "9–12",  True),
    ("paris-nice",       ("ouigo_fr",),           "CDG–NCE",                   ("air_france",),                     "8–9",   True),
]

# VM dry run 19.10.2026 (horizons +7/+30, both bag variants, not stored in the DB)
TEST_RUN_2026_10_19 = [
    ("milan-rome",       "LIN–FCO", 42,  79.00, 272.00, ("ita_airways",)),
    ("madrid-barcelona", "MAD–BCN", 52,  79.00, 223.00, ("air_europa", "iberia", "vueling")),
    ("barcelona-madrid", "BCN–MAD", 54, 101.00, 267.00, ("air_europa", "iberia", "vueling")),
    ("paris-nice",       "ORY–NCE", 40,  43.00, 215.00, ("easyjet", "transavia")),
    ("paris-nice",       "CDG–NCE", 22, 204.00, 571.00, ("air_france",)),
]


def _kpi(title, value, subtitle="", badge_color=None):
    sub = ""
    if subtitle and badge_color:
        sub = f'<div class="kpi-badge" style="color:{badge_color};border-color:{badge_color};">{subtitle}</div>'
    elif subtitle:
        sub = f'<div class="kpi-subtitle">{subtitle}</div>'
    return (f'<div class="kpi-card"><div class="kpi-title">{title}</div>'
            f'<div class="kpi-value">{value}</div>{sub}</div>')


def _ops(ops):
    return ", ".join(op_label(o) for o in ops) or "–"


# ══════════════════════════════════════════════════════════════════
# TAB 1: PROJEKTSTAND (WIP)
# ══════════════════════════════════════════════════════════════════
def _render_wip(T, lang, corridors):
    st.markdown(f"### {T['im_wip_title']}")
    st.caption(T["im_wip_intro"])

    # ── Live-Status aus der DB ──
    if not corridors.empty:
        pairs = {p for ps in corridors["airport_pairs"] for p in ps}
        airlines = {a for al in corridors["airlines"] for a in al}
        values = [
            corridors["first_air_day"].min().strftime("%d.%m.%Y"),
            str(int(corridors["air_days"].max())),
            f"{int(corridors['air_records'].sum()):,}".replace(",", "."),
            str(len(corridors)), str(len(pairs)), str(len(airlines)),
        ]
    else:
        values = ["–"] * 6
    labels = ["im_wip_kpi_since", "im_wip_kpi_days", "im_wip_kpi_records",
              "im_wip_kpi_corridors", "im_wip_kpi_pairs", "im_wip_kpi_airlines"]
    for col, key, val in zip(st.columns(6), labels, values):
        col.markdown(_kpi(T[key], val), unsafe_allow_html=True)

    # ── Strecken ──
    st.markdown(f"#### {T['im_wip_routes']}")
    st.dataframe(pd.DataFrame([{
        T["im_wip_col_corridor"]: CORRIDOR_NAMES[r][lang],
        T["im_wip_col_rail"]:     _ops(rail),
        T["im_wip_col_pair"]:     pair,
        T["im_wip_col_airlines"]: _ops(air),
        T["im_wip_col_freq"]:     freq,
        T["im_wip_col_status"]:   T["im_wip_active"] if active else T["im_wip_dropped"],
    } for r, rail, pair, air, freq, active in WIP_ROUTES]),
        use_container_width=True, hide_index=True)
    st.caption(T["im_wip_routes_note"])

    # ── Testdaten ──
    st.markdown(f"#### {T['im_wip_testdata']}")
    test = pd.DataFrame(TEST_RUN_2026_10_19,
                        columns=["route_id", "pair", "records", "low", "high", "airlines"])
    test["corridor"] = test["route_id"].map(lambda r: CORRIDOR_NAMES[r][lang])
    st.dataframe(pd.DataFrame({
        T["im_wip_col_corridor"]: test["corridor"],
        T["im_wip_col_pair"]:     test["pair"],
        T["im_wip_col_records"]:  test["records"],
        T["im_wip_col_range"]:    [f"{l:.2f} – {h:.2f} €" for l, h in zip(test["low"], test["high"])],
        T["im_wip_col_airlines"]: test["airlines"].map(_ops),
    }), use_container_width=True, hide_index=True)

    palette = px.colors.qualitative.Plotly
    corridor_color = {c: palette[i % len(palette)] for i, c in enumerate(test["corridor"].unique())}
    test["label"] = test["pair"] + "  (" + test["corridor"] + ")"
    fig = go.Figure()
    for _, r in test.iloc[::-1].iterrows():
        fig.add_trace(go.Bar(
            y=[r["label"]], x=[r["high"] - r["low"]], base=[r["low"]], orientation="h",
            marker_color=corridor_color[r["corridor"]], showlegend=False,
            text=[f"{r['low']:.0f} – {r['high']:.0f} €"], textposition="outside",
            hovertemplate=f"<b>{r['label']}</b><br>{r['low']:.2f} – {r['high']:.2f} €"
                          f"<br>{r['records']} obs.<extra></extra>",
        ))
    fig.update_xaxes(rangemode="tozero", title=T["ov_price"], range=[0, test["high"].max() * 1.15])
    fig.update_layout(title=T["im_wip_chart"], height=320, bargap=0.35,
                      margin=dict(l=10, r=10, t=50, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(T["im_wip_testdata_note"])

    # ── Methodik ──
    st.markdown(f"#### {T['im_wip_method']}")
    st.markdown(f'<div style="font-size:0.85rem;line-height:1.8;opacity:0.8;">{T["im_wip_method_text"]}</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2: LIVE-VORSCHAU
# ══════════════════════════════════════════════════════════════════
def _render_live(T, lang, corridors):
    mode_lbl = {m: T[f"im_mode_{m}"] for m in MODE_COLORS}
    if corridors.empty:
        st.info(T["im_no_data"])
        return

    first_air = corridors["first_air_day"].min()
    st.info(T["im_preview"].format(first=first_air.strftime("%d.%m.%Y"),
                                   days=int(corridors["air_days"].max())))

    # ── Steuerung ──
    labels = {
        r["route_id"]: (route_label(r["origin_name"], r["destination_name"], lang)
                        if pd.notna(r["origin_name"]) else r["route_id"])
        for _, r in corridors.iterrows()
    }
    c1, c2 = st.columns([3, 2])
    with c1:
        route_id = st.selectbox(T["im_corridor"], list(labels), format_func=labels.get, key="im_route")
    with c2:
        fare_class = st.radio(T["im_bags"], BAG_VARIANTS, horizontal=True, key="im_bags",
                              format_func=lambda fc: T[f"im_bag_{fc.split('_')[1]}"], help=T["im_bags_help"])
    pairs = corridors.loc[corridors["route_id"] == route_id, "airport_pairs"].iloc[0]
    st.caption(f"✈ {T['im_airports']}: {', '.join(sorted(pairs))}")

    df = load_intermodal_horizon(route_id, fare_class)
    if df.empty or not (df["mode"] == "air").any():
        st.info(T["im_no_data"])
        return

    df["op_label"] = df["operator"].map(op_label)
    df["mode_label"] = df["mode"].map(mode_lbl)
    horizons = sorted(df["booking_horizon_days"].unique().tolist())
    h = st.select_slider(T["im_horizon"], options=horizons,
                         value=14 if 14 in horizons else horizons[len(horizons) // 2], key="im_h")

    # ── KPIs bei Horizont h ──
    at_h = df[df["booking_horizon_days"] == h]
    ground = at_h[at_h["mode"] != "air"]
    air = at_h[at_h["mode"] == "air"]
    g_best = ground.loc[ground["price_min"].idxmin()] if not ground.empty else None
    a_best = air.loc[air["price_min"].idxmin()] if not air.empty else None

    k1, k2, k3 = st.columns(3)
    with k1:
        if g_best is not None:
            st.markdown(_kpi(T["im_cheapest_mode"].format(mode=mode_lbl[g_best["mode"]]),
                             f"{g_best['price_min']:.2f} €", op_label(g_best["operator"]),
                             op_color(g_best["operator"])), unsafe_allow_html=True)
        else:
            st.caption(T["im_no_mode"].format(mode=mode_lbl["rail"], h=h))
    with k2:
        if a_best is not None:
            st.markdown(_kpi(T["im_cheapest_mode"].format(mode=mode_lbl["air"]),
                             f"{a_best['price_min']:.2f} €", op_label(a_best["operator"]),
                             op_color(a_best["operator"])), unsafe_allow_html=True)
        else:
            st.caption(T["im_no_mode"].format(mode=mode_lbl["air"], h=h))
    with k3:
        if g_best is not None and a_best is not None:
            diff = (a_best["price_min"] - g_best["price_min"]) / g_best["price_min"] * 100
            st.markdown(_kpi(T["im_diff"], f"{diff:+.0f}%", T["im_diff_sub"].format(h=h)),
                        unsafe_allow_html=True)

    route_lbl = labels[route_id]

    # ── Chart 1: Preis nach Horizont ──
    color_map = {op_label(o): op_color(o) for o in df["operator"].unique()}
    dash_map = {mode_lbl[m]: d for m, d in MODE_DASH.items()}
    fig1 = px.line(df, x="booking_horizon_days", y="price_min", color="op_label",
                   line_dash="mode_label", line_dash_map=dash_map, color_discrete_map=color_map,
                   markers=True, title=f"{T['im_c1']} — {route_lbl}",
                   labels={"booking_horizon_days": T["ov_days_adv"], "price_min": T["im_price"],
                           "op_label": T["ov_op"], "mode_label": T["im_mode"]},
                   custom_data=["mode_label", "price_avg", "n_offers"])
    fig1.update_traces(line_width=2, marker_size=6,
                       hovertemplate="<b>%{fullData.name}</b> (%{customdata[0]})<br>+%{x} " + T["days_unit"] +
                                     "<br>Min %{y:.2f} €<br>Avg %{customdata[1]:.2f} €<br>%{customdata[2]} obs.")
    fig1.add_vline(x=h, line_dash="dot", line_color="rgba(128,128,128,0.5)")
    fig1.update_xaxes(autorange="reversed")
    fig1.update_yaxes(rangemode="tozero")
    fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: Zeitreihe pro Erhebungstag ──
    daily = load_intermodal_daily(route_id, fare_class, h)
    if not daily.empty:
        daily["mode_label"] = daily["mode"].map(mode_lbl)
        daily["cheapest_label"] = daily["cheapest_operator"].map(op_label)
        fig2 = px.line(daily, x="col_date", y="price_min", color="mode_label",
                       color_discrete_map={mode_lbl[m]: c for m, c in MODE_COLORS.items()},
                       markers=True, title=f"{T['im_c2'].format(h=h)} — {route_lbl}",
                       labels={"col_date": T["ov_date"], "price_min": T["im_price"], "mode_label": T["im_mode"]},
                       custom_data=["cheapest_label"])
        fig2.update_traces(line_width=2, marker_size=6,
                           hovertemplate="<b>%{fullData.name}</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} € · %{customdata[0]}")
        fig2.update_traces(selector=dict(name=mode_lbl["air"]), marker_size=11)
        fig2.update_yaxes(rangemode="tozero")
        fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(T["im_c2_note"].format(first=first_air.strftime("%d.%m.%Y")))


def render_intermodal(T):
    lang = st.session_state.lang
    st.subheader(T["im_head"])
    corridors = load_intermodal_corridors()

    tab_wip, tab_live = st.tabs([T["im_tab_wip"], T["im_tab_live"]])
    with tab_wip:
        _render_wip(T, lang, corridors)
    with tab_live:
        _render_live(T, lang, corridors)
