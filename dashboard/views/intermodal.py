# dashboard/views/intermodal.py
# Rail/bus vs. air per corridor (Google Flights data since 19.10.2026):
#   which is cheaper · door to door · price development · data basis & method.
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.config import op_color, op_label, price_basis_toggle
from dashboard.database import (
    load_intermodal_corridors, load_intermodal_horizon, load_intermodal_daily,
    load_intermodal_matrix, load_intermodal_door, load_distances, load_intermodal_pair_airlines,
)


def _load_flight_config():
    # Under streamlit "config" resolves to dashboard/config.py, so the top-level
    # config/flight_routes.py is loaded by path.
    path = Path(__file__).resolve().parents[2] / "config" / "flight_routes.py"
    spec = importlib.util.spec_from_file_location("rdh_flight_routes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_flights = _load_flight_config()
FLIGHT_ROUTES, FLIGHT_HORIZONS = _flights.FLIGHT_ROUTES, _flights.FLIGHT_HORIZONS

MODE_COLORS = {"rail": "#2563EB", "bus": "#18a04b", "air": "#f97316"}
MODE_DASH   = {"rail": "solid", "bus": "dot", "air": "dash"}
BAG_VARIANTS = ["economy_cabinbag", "economy_nobag"]

# City names per side, used for corridor labels "A – B" (route_id "a-b")
CITY_NAMES = {
    "milan": ("Mailand", "Milan"), "rome": ("Rom", "Rome"), "madrid": ("Madrid", "Madrid"),
    "barcelona": ("Barcelona", "Barcelona"), "paris": ("Paris", "Paris"), "nice": ("Nizza", "Nice"),
    "london": ("London", "London"), "brussels": ("Brüssel", "Brussels"), "amsterdam": ("Amsterdam", "Amsterdam"),
    "lyon": ("Lyon", "Lyon"), "vienna": ("Wien", "Vienna"), "prague": ("Prag", "Prague"),
    "venice": ("Venedig", "Venice"), "munich": ("München", "Munich"), "budapest": ("Budapest", "Budapest"),
    "warsaw": ("Warschau", "Warsaw"), "bratislava": ("Bratislava", "Bratislava"), "berlin": ("Berlin", "Berlin"),
    "bucharest": ("Bukarest", "Bucharest"), "stockholm": ("Stockholm", "Stockholm"), "oslo": ("Oslo", "Oslo"),
}
CORRIDOR_NAMES = {
    r.route_id: {lang: " – ".join(CITY_NAMES[c][i] for c in r.route_id.split("-", 1))
                 for i, lang in enumerate(("de", "en"))}
    for r in FLIGHT_ROUTES if all(c in CITY_NAMES for c in r.route_id.split("-", 1))
}

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
# TAB: DATENBASIS & METHODIK
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

    # ── Strecken: alle konfigurierten Flughafenpaare, Fluglinien aus der DB ──
    observed = load_intermodal_pair_airlines()
    observed = ({(r, p): tuple(a) for r, p, a in zip(observed["route_id"], observed["pair"], observed["airlines"])}
                if not observed.empty else {})
    rows = []
    for fr in FLIGHT_ROUTES:
        for o, d in fr.airport_pairs:
            airlines = observed.get((fr.route_id, f"{o}-{d}"))
            rows.append({
                T["im_wip_col_corridor"]: _corridor_name(fr.route_id, lang),
                T["im_wip_col_rail"]:     _ops(fr.rail_operators) if fr.rail_operators else T["im_wip_air_only"],
                T["im_wip_col_pair"]:     f"{o}–{d}",
                T["im_wip_col_airlines"]: _ops(airlines) if airlines else "–",
                T["im_wip_col_status"]:   T["im_wip_active"] if airlines else T["im_wip_pending"],
            })
    st.markdown(f"#### {T['im_wip_routes']}")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(T["im_wip_routes_note"])

    # ── Methodik ──
    st.markdown(f"#### {T['im_wip_method']}")
    st.markdown(f'<div style="font-size:0.85rem;line-height:1.8;opacity:0.8;">{T["im_wip_method_text"]}</div>',
                unsafe_allow_html=True)

    # ── Testlauf vor dem Produktivbetrieb (historisch) ──
    with st.expander(T["im_wip_testdata"], expanded=False):
        test = pd.DataFrame(TEST_RUN_2026_10_19,
                            columns=["route_id", "pair", "records", "low", "high", "airlines"])
        test["corridor"] = test["route_id"].map(lambda r: _corridor_name(r, lang))
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


# ══════════════════════════════════════════════════════════════════
# TAB: PREISVERLAUF
# ══════════════════════════════════════════════════════════════════
def _render_live(T, lang, corridors):
    mode_lbl = {m: T[f"im_mode_{m}"] for m in MODE_COLORS}
    if corridors.empty:
        st.info(T["im_no_data"])
        return

    first_air = corridors["first_air_day"].min()
    st.caption(T["im_preview"].format(first=first_air.strftime("%d.%m.%Y"),
                                      days=int(corridors["air_days"].max())))

    # ── Steuerung ──
    route_id, fare_class = _controls(T, lang, corridors, "im")
    basis = price_basis_toggle("im_basis", T, with_median=True)
    y_col = f"price_{basis}"
    stat = {"min": T["price_min"], "avg": T["price_avg"], "median": T["price_median"],
            "max": T["price_max_label"]}[basis]
    pairs = corridors.loc[corridors["route_id"] == route_id, "airport_pairs"].iloc[0]
    st.caption(f"✈ {T['im_airports']}: {', '.join(sorted(pairs))}")

    df = load_intermodal_horizon(route_id, fare_class)
    if df.empty or not (df["mode"] == "air").any():
        st.info(T["im_no_data"])
        return

    df["op_label"] = df["operator"].map(op_label)
    df["mode_label"] = df["mode"].map(mode_lbl)
    # only horizons with air data (flights use every second rail horizon)
    horizons = sorted(df.loc[df["mode"] == "air", "booking_horizon_days"].unique().tolist())
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

    route_lbl = _corridor_name(route_id, lang)

    # ── Chart 1: Preis nach Horizont ──
    color_map = {op_label(o): op_color(o) for o in df["operator"].unique()}
    dash_map = {mode_lbl[m]: d for m, d in MODE_DASH.items()}
    fig1 = px.line(df, x="booking_horizon_days", y=y_col, color="op_label",
                   line_dash="mode_label", line_dash_map=dash_map, color_discrete_map=color_map,
                   markers=True, title=f"{T['im_c1'].format(stat=stat)} — {route_lbl}",
                   labels={"booking_horizon_days": T["ov_days_adv"], y_col: T["im_price"],
                           "op_label": T["ov_op"], "mode_label": T["im_mode"]},
                   custom_data=["mode_label", "price_min", "price_avg", "price_median", "price_max", "n_offers"])
    fig1.update_traces(line_width=2, marker_size=6,
                       hovertemplate="<b>%{fullData.name}</b> (%{customdata[0]})<br>+%{x} " + T["days_unit"] +
                                     "<br>Min %{customdata[1]:.2f} € · Avg %{customdata[2]:.2f} €"
                                     "<br>Median %{customdata[3]:.2f} € · Max %{customdata[4]:.2f} €"
                                     "<br>%{customdata[5]} obs.<extra></extra>")
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
        fig2 = px.line(daily, x="col_date", y=y_col, color="mode_label",
                       color_discrete_map={mode_lbl[m]: c for m, c in MODE_COLORS.items()},
                       markers=True, title=f"{T['im_c2'].format(h=h, stat=stat)} — {route_lbl}",
                       labels={"col_date": T["ov_date"], y_col: T["im_price"], "mode_label": T["im_mode"]},
                       custom_data=["cheapest_label"])
        cheapest = " · %{customdata[0]}" if basis == "min" else ""
        fig2.update_traces(line_width=2, marker_size=6,
                           hovertemplate="<b>%{fullData.name}</b><br>%{x|%d.%m.%Y}<br>%{y:.2f} €" + cheapest)
        fig2.update_traces(selector=dict(name=mode_lbl["air"]), marker_size=11)
        fig2.update_yaxes(rangemode="tozero")
        fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(T["im_c2_note"].format(first=first_air.strftime("%d.%m.%Y")))


# ══════════════════════════════════════════════════════════════════
# SHARED CONTROLS (which is cheaper + door to door)
# ══════════════════════════════════════════════════════════════════
CHEAPER_COLOR = {"ground": "#1d4ed8", "air": "#c2410c"}


def _corridor_name(route_id, lang):
    """City names only (e.g. "Madrid – Barcelona"); unknown corridors fall back to the route_id cities."""
    if route_id in CORRIDOR_NAMES:
        return CORRIDOR_NAMES[route_id][lang]
    return " – ".join(part.replace("_", " ").title() for part in route_id.split("-", 1))


def _controls(T, lang, corridors, key):
    """Corridor + bag variant selection; returns (route_id, fare_class)."""
    c1, c2 = st.columns([3, 2])
    with c1:
        route_id = st.selectbox(T["im_corridor"], corridors["route_id"].tolist(),
                                format_func=lambda r: _corridor_name(r, lang), key=f"{key}_route")
    with c2:
        fare_class = st.radio(T["im_bags"], BAG_VARIANTS, horizontal=True, key=f"{key}_bags",
                              format_func=lambda fc: T[f"im_bag_{fc.split('_')[1]}"], help=T["im_bags_help"])
    return route_id, fare_class


def _summarise(m):
    """Share rail cheaper, mean diff (air − ground) and the horizon where air comes closest."""
    by_h = m.groupby("h")["diff"].apply(lambda s: (s > 0).mean() * 100)
    return {
        "share": (m["diff"] > 0).mean() * 100,
        "mean_diff": m["diff"].mean(),
        "worst_h": int(by_h.idxmin()),
        "worst_share": float(by_h.min()),
    }


# ══════════════════════════════════════════════════════════════════
# TAB: WER IST GÜNSTIGER?
# ══════════════════════════════════════════════════════════════════
def _render_cheaper(T, lang, corridors):
    if corridors.empty:
        st.info(T["im_no_data"])
        return
    st.caption(T["im_cmp_intro"])
    route_id, fare_class = _controls(T, lang, corridors, "imc")
    first_air = corridors["first_air_day"].min()
    period = st.radio(T["im_cmp_period"], [14, 0], horizontal=True, key="imc_period",
                      format_func=lambda d: T["im_cmp_last_days"].format(d=d) if d else T["im_cmp_since_start"])

    m_all = load_intermodal_matrix(tuple(corridors["route_id"]), fare_class, first_air)
    if m_all.empty:
        st.info(T["im_no_data"])
        return
    if period:
        m_all = m_all[m_all["col_date"] > m_all["col_date"].max() - pd.Timedelta(days=period)]
    m_all = m_all.assign(diff=(m_all["air_min"] - m_all["ground_min"]).round(2))
    m = m_all[m_all["route_id"] == route_id]
    if m.empty:
        st.info(T["im_no_data"])
        return
    s = _summarise(m)

    dist = load_distances()
    dist_row = dist[dist["route_id"] == route_id]
    dist_km = float(dist_row["distance_km"].iloc[0]) if not dist_row.empty else None
    dist_rail = not dist_row.empty and dist_row["distance_source"].iloc[0] == "rail"

    # ── KPIs ──
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi(T["im_cmp_kpi_share"], f"{s['share']:.0f} %", T["im_cmp_kpi_share_sub"]),
                unsafe_allow_html=True)
    k2.markdown(_kpi(T["im_cmp_kpi_diff"], f"{s['mean_diff']:+.0f} €", T["im_cmp_kpi_diff_sub"]),
                unsafe_allow_html=True)
    if s["worst_share"] >= 100:
        k3.markdown(_kpi(T["im_cmp_kpi_flip"], T["im_cmp_never"], T["im_cmp_never_sub"]), unsafe_allow_html=True)
    else:
        k3.markdown(_kpi(T["im_cmp_kpi_flip"], f"+{s['worst_h']} {T['days_unit']}",
                         T["im_cmp_flip_sub"].format(share=s["worst_share"])), unsafe_allow_html=True)
    if dist_km:
        sub = T["im_cmp_km_sub_rail" if dist_rail else "im_cmp_km_sub_hav"].format(km=dist_km)
        k4.markdown(_kpi(T["im_cmp_kpi_km"], f"{m['ground_min'].mean() / dist_km:.3f} € · "
                                             f"{m['air_min'].mean() / dist_km:.3f} €", sub),
                    unsafe_allow_html=True)

    corridor = _corridor_name(route_id, lang)
    horizons = sorted(m["h"].unique(), reverse=True)

    # ── Heatmap: Erhebungstag × Vorlauf ──
    piv = (m.pivot_table(index="col_date", columns="h", values="diff")
             .reindex(columns=horizons).sort_index(ascending=False))
    zmax = max(10.0, float(np.nanpercentile(np.abs(piv.values), 95)))
    # z and labels as plain lists, pre-formatted: Plotly 6 sends numpy arrays as binary
    # typed arrays, on which Streamlit's plotly.js ignores d3 number formats.
    z = [[None if pd.isna(v) else float(v) for v in r] for r in piv.values]
    labels = [["" if pd.isna(v) else f"{v:+.0f}" for v in r] for r in piv.values]
    fig1 = go.Figure(go.Heatmap(
        z=z, x=[str(h) for h in horizons], y=list(piv.index.strftime("%d.%m.")),
        zmin=-zmax, zmax=zmax, zmid=0,
        colorscale=[[0, CHEAPER_COLOR["air"]], [0.5, "#ffffff"], [1, CHEAPER_COLOR["ground"]]],
        text=labels, texttemplate="%{text}", textfont={"size": 10}, xgap=2, ygap=2,
        colorbar={"title": "€"},
        hovertemplate="%{y} · +%{x} " + T["days_unit"] + "<br>" + T["im_cmp_hover_diff"] + ": %{text} €<extra></extra>",
    ))
    fig1.update_xaxes(title=T["ov_days_adv"], type="category")
    fig1.update_yaxes(title=T["im_cmp_col_day"], type="category")
    fig1.update_layout(title=f"{T['im_cmp_c1']} — {corridor}", height=max(320, 26 * len(piv) + 160),
                       margin=dict(l=10, r=10, t=60, b=70),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)
    st.caption(T["im_cmp_c1_note"])

    # ── Anteil Bahn günstiger nach Vorlauf ──
    share_h = (m.groupby("h")["diff"].apply(lambda x: (x > 0).mean() * 100)
                 .reindex(horizons).reset_index(name="share"))
    share_h["h_lbl"] = share_h["h"].astype(str)
    share_h["winner"] = np.where(share_h["share"] >= 50, T["im_mode_rail"], T["im_mode_air"])
    share_h["share_lbl"] = share_h["share"].map(lambda v: f"{v:.0f} %")
    fig2 = px.bar(share_h, x="h_lbl", y="share", color="winner", text="share_lbl",
                  color_discrete_map={T["im_mode_rail"]: "#2563eb", T["im_mode_air"]: "#ea580c"},
                  title=f"{T['im_cmp_c2']} — {corridor}",
                  labels={"h_lbl": T["ov_days_adv"], "share": T["im_cmp_share_axis"], "winner": ""})
    fig2.update_traces(textposition="outside", cliponaxis=False)
    fig2.update_xaxes(type="category")
    fig2.update_yaxes(range=[0, 110])
    fig2.add_hline(y=50, line_dash="dot", line_color="rgba(128,128,128,0.6)")
    fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Alle Korridore ──
    st.markdown(f"#### {T['im_cmp_table']}")
    rows = []
    for rid, g in m_all.groupby("route_id"):
        gs = _summarise(g)
        rows.append({
            T["im_wip_col_corridor"]: _corridor_name(rid, lang),
            T["im_cmp_kpi_share"]:    gs["share"],
            T["im_cmp_kpi_diff"]:     f"{gs['mean_diff']:+.0f} €",
            T["im_cmp_kpi_flip"]:     (T["im_cmp_never"] if gs["worst_share"] >= 100
                                       else f"+{gs['worst_h']} {T['days_unit']} ({gs['worst_share']:.0f} %)"),
            T["im_cmp_col_days"]:     g["col_date"].nunique(),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, column_config={
        T["im_cmp_kpi_share"]: st.column_config.ProgressColumn(format="%.0f %%", min_value=0, max_value=100),
    })
    st.caption(T["im_cmp_method"])


# ══════════════════════════════════════════════════════════════════
# TAB: TÜR ZU TÜR
# ══════════════════════════════════════════════════════════════════
# Rough access/egress assumptions (minutes, € one way) between city centre and
# station/airport, as of 11/2026. Shown in the tab so users can judge them.
ACCESS = {
    "Milano Centrale":               (15, 2.20),
    "Roma Termini":                  (15, 1.50),
    "Madrid - Todas las estaciones": (15, 1.50),
    "Barcelona - Sants":             (15, 2.55),
    "Paris - Toutes les gares":      (20, 2.50),
    "Nice Ville":                    (15, 1.70),
    "LIN": (30, 2.20),
    "FCO": (45, 14.00),
    "MAD": (40, 5.00),
    "BCN": (40, 5.50),
    "ORY": (40, 13.00),
    "CDG": (50, 13.00),
    "NCE": (30, 1.70),
}
ACCESS_DEFAULT = (20, 2.00)
DEBOARD_MIN = 20

STEP_COLORS = {"access": "#9ca3af", "wait": "#e5e7eb", "ground": "#2563eb", "air": "#ea580c"}


def _hm(minutes):
    return f"{int(minutes // 60)}:{int(round(minutes % 60)):02d} h"


def _render_door(T, lang, corridors):
    if corridors.empty:
        st.info(T["im_no_data"])
        return
    st.caption(T["im_d2d_intro"])
    route_id, fare_class = _controls(T, lang, corridors, "imd")
    row = corridors[corridors["route_id"] == route_id].iloc[0]
    first_air = corridors["first_air_day"].min()

    c1, c2, c3 = st.columns(3)
    with c1:
        h = st.select_slider(T["im_horizon"], options=FLIGHT_HORIZONS,
                             value=14, key="imd_h")
    with c2:
        vot = st.slider(T["im_d2d_vot"], 0, 100, 20, step=1, key="imd_vot", help=T["im_d2d_vot_help"])
    with c3:
        buffer = st.slider(T["im_d2d_buffer"], 30, 150, 75, step=5, key="imd_buffer")

    df = load_intermodal_door(route_id, fare_class, h, first_air)
    ground = df[df["mode"] == "ground"]
    air = df[df["mode"] == "air"].sort_values("price")
    if ground.empty or air.empty:
        st.info(T["im_no_mode"].format(mode=T["im_mode_air" if air.empty else "im_mode_rail"], h=h))
        return
    pair = air["pair"].iloc[0]
    if len(air) > 1:
        pair = st.radio(T["im_airports"], air["pair"].tolist(), horizontal=True, key="imd_pair",
                        format_func=lambda p: p.replace("-", "–"))
    a = air[air["pair"] == pair].iloc[0]
    g = ground.iloc[0]
    orig_ap, dest_ap = pair.split("-")

    def acc(place):
        return ACCESS.get(place, ACCESS_DEFAULT)

    rail_name, air_name = T["im_mode_rail"], T["im_mode_air"]
    steps = [
        (rail_name, T["im_d2d_to_station"],   acc(row["origin_name"])[0],      "access", acc(row["origin_name"])[1]),
        (rail_name, T["im_d2d_ride"],         g["travel_h"] * 60,              "ground", g["price"]),
        (rail_name, T["im_d2d_from_station"], acc(row["destination_name"])[0], "access", acc(row["destination_name"])[1]),
        (air_name,  T["im_d2d_to_airport"],   acc(orig_ap)[0],                 "access", acc(orig_ap)[1]),
        (air_name,  T["im_d2d_checkin"],      buffer,                          "wait",   0),
        (air_name,  T["im_d2d_flight"],       a["travel_h"] * 60,              "air",    a["price"]),
        (air_name,  T["im_d2d_deboard"],      DEBOARD_MIN,                     "wait",   0),
        (air_name,  T["im_d2d_from_airport"], acc(dest_ap)[0],                 "access", acc(dest_ap)[1]),
    ]
    st_df = pd.DataFrame(steps, columns=["mode", "step", "minutes", "kind", "eur"])
    tot = st_df.groupby("mode").agg(minutes=("minutes", "sum"), eur=("eur", "sum"))
    r_min, r_eur = tot.loc[rail_name, "minutes"], tot.loc[rail_name, "eur"]
    a_min, a_eur = tot.loc[air_name, "minutes"], tot.loc[air_name, "eur"]
    r_gen, a_gen = r_eur + r_min / 60 * vot, a_eur + a_min / 60 * vot

    # break-even value of time: cheaper mode vs. faster mode
    d_eur, d_h = r_eur - a_eur, (a_min - r_min) / 60
    if (d_eur > 0) == (d_h > 0) and d_h != 0:
        breakeven = d_eur / d_h
        faster = rail_name if d_h > 0 else air_name
        be_text = T["im_d2d_be"].format(mode=faster, v=breakeven)
    else:
        breakeven = None
        be_text = T["im_d2d_be_always"].format(mode=rail_name if r_gen <= a_gen else air_name)

    # ── KPIs ──
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi(T["im_d2d_kpi_time"].format(mode=rail_name), _hm(r_min), T["im_d2d_kpi_time_sub"]),
                unsafe_allow_html=True)
    k2.markdown(_kpi(T["im_d2d_kpi_time"].format(mode=air_name), _hm(a_min),
                     T["im_d2d_kpi_buffer_sub"].format(b=buffer)), unsafe_allow_html=True)
    k3.markdown(_kpi(T["im_d2d_kpi_money"], f"{r_eur:.0f} € · {a_eur:.0f} €",
                     T["im_d2d_kpi_money_sub"].format(h=h)), unsafe_allow_html=True)
    k4.markdown(_kpi(T["im_d2d_kpi_verdict"].format(v=vot), rail_name if r_gen <= a_gen else air_name, be_text),
                unsafe_allow_html=True)

    corridor = _corridor_name(route_id, lang)

    # ── Reiseablauf ──
    fig1 = go.Figure()
    for _, s in st_df.iterrows():
        fig1.add_trace(go.Bar(
            y=[s["mode"]], x=[s["minutes"]], orientation="h", name=s["step"], showlegend=False,
            marker_color=STEP_COLORS[s["kind"]], marker_line_color="#9ca3af", marker_line_width=1,
            text=[f"{s['step']} {s['minutes']:.0f}'"], textposition="inside", insidetextanchor="middle",
            hovertemplate=f"<b>{s['step']}</b><br>{s['minutes']:.0f} min · {s['eur']:.2f} €<extra></extra>",
        ))
    fig1.update_layout(barmode="stack", height=240, title=f"{T['im_d2d_c1']} — {corridor}",
                       xaxis_title=T["im_d2d_minutes"], margin=dict(l=10, r=10, t=50, b=10),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig1.update_yaxes(categoryorder="array", categoryarray=[air_name, rail_name])
    st.plotly_chart(fig1, use_container_width=True)

    # ── Kosten inkl. Zeit ──
    v = np.arange(0, 101, 5)
    lines = pd.DataFrame({
        "vot": np.concatenate([v, v]),
        "cost": np.concatenate([r_eur + r_min / 60 * v, a_eur + a_min / 60 * v]),
        "mode": [rail_name] * len(v) + [air_name] * len(v),
    })
    fig2 = px.line(lines, x="vot", y="cost", color="mode", line_dash="mode",
                   color_discrete_map={rail_name: "#2563eb", air_name: "#ea580c"},
                   line_dash_map={rail_name: "solid", air_name: "dash"},
                   title=f"{T['im_d2d_c2']} — {corridor}",
                   labels={"vot": T["im_d2d_vot_axis"], "cost": T["im_d2d_cost_axis"], "mode": T["im_mode"]})
    fig2.add_vline(x=vot, line_dash="dot", line_color="rgba(128,128,128,0.7)")
    if breakeven is not None and 0 <= breakeven <= 100:
        fig2.add_scatter(x=[breakeven], y=[r_eur + r_min / 60 * breakeven], mode="markers+text",
                         marker=dict(size=11, color="#111827"), text=[f"{breakeven:.0f} €/h"],
                         textposition="top left", showlegend=False, hoverinfo="skip")
    fig2.update_yaxes(rangemode="tozero")
    fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Annahmen ──
    with st.expander(T["im_d2d_assumptions"], expanded=False):
        st.dataframe(st_df.assign(minutes=st_df["minutes"].round(0), eur=st_df["eur"].round(2)).rename(columns={
            "mode": T["im_mode"], "step": T["im_d2d_step"], "minutes": T["im_d2d_minutes"], "eur": "€",
        }).drop(columns="kind"), use_container_width=True, hide_index=True)
        st.caption(T["im_d2d_assumptions_note"].format(h=h, n=int(min(g["n_days"], a["n_days"]))))


def render_intermodal(T):
    lang = st.session_state.lang
    st.subheader(T["im_head"])
    corridors = load_intermodal_corridors()

    tab_cheaper, tab_door, tab_live, tab_wip = st.tabs(
        [T["im_tab_cheaper"], T["im_tab_door"], T["im_tab_live"], T["im_tab_wip"]])
    with tab_cheaper:
        _render_cheaper(T, lang, corridors)
    with tab_door:
        _render_door(T, lang, corridors)
    with tab_live:
        _render_live(T, lang, corridors)
    with tab_wip:
        _render_wip(T, lang, corridors)
