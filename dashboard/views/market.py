# dashboard/views/market.py
# Market overview across all routes: route ranking (€/km), pricing strategies
# (booking paths per operator) and day of travel (weekday, holidays).
# All heavy lifting happens in SQL (dashboard/database.py, load_market_*),
# results are cached for hours. DB only — no offline mode.
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.config import op_color, op_label, route_label
from dashboard.database import (
    BUS_OPERATORS, is_offline_mode, load_distances, load_market_ranking, load_market_day_prices,
    load_market_yield_curve, load_market_yield_moves, load_market_price_points, load_market_example_paths,
)
from dashboard.views.overview import _kpi_card

HORIZONS = [90, 60, 45, 30, 21, 14, 10, 7, 6, 5, 4, 3, 2, 1]
MIN_DAYS = 7          # ranking: ignore route × operator with fewer collection days
MIN_DEPS = 200        # pricing strategies: ignore operators with fewer observed departures
UP, DOWN = "#ea580c", "#2563eb"

# Home market per operator (holiday effects are pooled over the operators of a country)
OPERATOR_MARKET = {
    "trenitalia": "IT", "italo": "IT", "ouigo_es": "ES", "ouigo_fr": "FR",
    "regiojet": "CZ", "ceske-drahy": "CZ", "db": "DE", "db_parsebot": "DE", "flixtrain": "DE",
}

# Public holidays in the collected departure range (Jun 2026 – Feb 2027), by country.
HOLIDAYS = [
    ("2026-06-02", "Festa della Repubblica", ("IT",)),
    ("2026-07-06", "Jan Hus", ("CZ",)),
    ("2026-07-14", "Fête nationale", ("FR",)),
    ("2026-08-15", "Ferragosto / Assomption / Asunción", ("IT", "FR", "ES")),
    ("2026-09-28", "Den české státnosti", ("CZ",)),
    ("2026-10-03", "Tag der Deutschen Einheit", ("DE",)),
    ("2026-10-12", "Fiesta Nacional", ("ES",)),
    ("2026-10-28", "Vznik Československa", ("CZ",)),
    ("2026-11-01", "Ognissanti / Toussaint / Todos los Santos", ("IT", "FR", "ES")),
    ("2026-11-11", "Armistice", ("FR",)),
    ("2026-11-17", "Den boje za svobodu", ("CZ",)),
    ("2026-12-08", "Immacolata / Inmaculada", ("IT", "ES")),
    ("2026-12-24", "Heiligabend / Štědrý den", ("DE", "CZ")),
    ("2026-12-25", "Weihnachten / Natale / Noël / Navidad", ("IT", "FR", "ES", "DE", "CZ")),
    ("2026-12-26", "Santo Stefano / 2. Weihnachtstag", ("IT", "DE", "CZ")),
    ("2027-01-01", "Neujahr / Capodanno / Jour de l'an / Año Nuevo", ("IT", "FR", "ES", "DE", "CZ")),
    ("2027-01-06", "Epifania / Reyes", ("IT", "ES")),
]


def _layout(fig, **kw):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", **kw)
    return fig


def _fmt_eur(v, d=2):
    return f"{v:.{d}f} €".replace(".", ",")


# ══════════════════════════════════════════════════════════════════
# TAB: STRECKEN-RANKING
# ══════════════════════════════════════════════════════════════════
def _render_ranking(T, lang):
    st.caption(T["mk_rk_intro"])
    c1, c2, c3 = st.columns([1, 3, 2])
    with c1:
        h = st.selectbox(T["mk_horizon"], [1, 7, 14, 30, 60], index=2, key="mk_rk_h",
                         format_func=lambda x: f"{x} {T['days_unit']}")
    raw = load_market_ranking(h)
    if raw.empty:
        st.info(T["mk_no_data"])
        return
    dist = load_distances()
    df = raw.merge(dist, on="route_id", how="inner")
    df = df[df["n_days"] >= MIN_DAYS].copy()
    with c2:
        ops = sorted(df["operator"].unique(), key=op_label)
        sel_ops = st.multiselect(T["mk_operators"], ops, default=ops, format_func=op_label, key="mk_rk_ops")
    with c3:
        st.write("")
        with_hav = st.checkbox(T["mk_rk_with_hav"], value=False, key="mk_rk_hav")
    df = df[df["operator"].isin(sel_ops)]
    if not with_hav:
        df = df[df["distance_source"] == "rail"]
    if df.empty:
        st.info(T["mk_no_data"])
        return

    df["eur_km"] = (df["price"] / df["distance_km"]).round(4)
    df["route"] = [route_label(o, d, lang) for o, d in zip(df["origin"], df["destination"])]
    df["op_label"] = df["operator"].map(op_label)
    df["mode"] = np.where(df["operator"].isin(BUS_OPERATORS), T["im_mode_bus"], T["im_mode_rail"])
    df["hover"] = [
        f"<b>{r}</b><br>{o} · {km:.0f} km<br>{_fmt_eur(p)} · {ek:.3f} €/km<br>{n} {T['mk_days']}"
        + ("<br>⚠️ " + T["mk_hav_short"] if s != "rail" else "")
        for r, o, km, p, ek, n, s in zip(df["route"], df["op_label"], df["distance_km"], df["price"],
                                         df["eur_km"], df["n_days"], df["distance_source"])
    ]
    color_map = {op_label(o): op_color(o) for o in df["operator"].unique()}

    # ── KPIs ──
    lo, hi = df.loc[df["eur_km"].idxmin()], df.loc[df["eur_km"].idxmax()]
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(_kpi_card(T["mk_rk_cheapest"], f"{lo['eur_km']:.3f} €/km", f"{lo['route']} · {lo['op_label']}",
                          value_color="#2563eb"), unsafe_allow_html=True)
    k2.markdown(_kpi_card(T["mk_rk_priciest"], f"{hi['eur_km']:.3f} €/km", f"{hi['route']} · {hi['op_label']}",
                          value_color="#ea580c"), unsafe_allow_html=True)
    k3.markdown(_kpi_card(T["mk_rk_median"], f"{df['eur_km'].median():.3f} €/km",
                          T["mk_rk_factor"].format(f=hi["eur_km"] / lo["eur_km"])), unsafe_allow_html=True)
    k4.markdown(_kpi_card(T["mk_rk_count"], str(df["route_id"].nunique()),
                          T["mk_rk_count_sub"].format(n=len(df), ops=df["operator"].nunique())), unsafe_allow_html=True)

    # ── Preis vs. Distanz ──
    fig = px.scatter(df, x="distance_km", y="price", color="op_label", symbol="mode",
                     color_discrete_map=color_map, custom_data=["hover"],
                     labels={"distance_km": T["mk_rk_km"], "price": T["mk_rk_price"].format(h=h),
                             "op_label": T["ov_op"], "mode": ""},
                     title=T["mk_rk_c1"])
    fig.update_traces(marker=dict(size=10, line=dict(width=1, color="white")),
                      hovertemplate="%{customdata[0]}<extra></extra>")
    if len(df) >= 3:
        slope, icpt = np.polyfit(df["distance_km"], df["price"], 1)
        xs = np.array([0, df["distance_km"].max() * 1.05])
        fig.add_trace(go.Scatter(x=xs.tolist(), y=(icpt + slope * xs).round(2).tolist(), mode="lines",
                                 line=dict(dash="dash", color="rgba(128,128,128,0.8)"),
                                 name=T["mk_rk_trend"], hoverinfo="skip"))
    fig.update_xaxes(rangemode="tozero")
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(_layout(fig, height=480), use_container_width=True)
    st.caption(T["mk_rk_c1_note"])

    # ── Günstigste / teuerste 10 ──
    def bars(sub, title):
        sub = sub.assign(lbl=sub["eur_km"].map(lambda v: f"{v:.3f}"),
                         name=sub["route"] + " · " + sub["op_label"])
        f = px.bar(sub, x="eur_km", y="name", orientation="h", color="op_label", text="lbl",
                   color_discrete_map=color_map, custom_data=["hover"], title=title,
                   labels={"eur_km": "€ / km", "name": "", "op_label": T["ov_op"]})
        f.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{customdata[0]}<extra></extra>")
        f.update_yaxes(categoryorder="array", categoryarray=sub["name"].tolist()[::-1])
        f.update_layout(showlegend=False)
        return _layout(f, height=420, margin=dict(l=10, r=40, t=50, b=10))

    b1, b2 = st.columns(2)
    with b1:
        st.plotly_chart(bars(df.nsmallest(10, "eur_km"), T["mk_rk_c2_low"]), use_container_width=True)
    with b2:
        st.plotly_chart(bars(df.nlargest(10, "eur_km"), T["mk_rk_c2_high"]), use_container_width=True)

    # ── Anbieter im Vergleich ──
    order = df.groupby("op_label")["eur_km"].median().sort_values().index.tolist()
    fig3 = px.box(df, x="op_label", y="eur_km", color="op_label", color_discrete_map=color_map, points="all",
                  custom_data=["hover"], category_orders={"op_label": order}, title=T["mk_rk_c3"],
                  labels={"op_label": "", "eur_km": "€ / km"})
    fig3.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig3.update_yaxes(rangemode="tozero")
    st.plotly_chart(_layout(fig3, showlegend=False, height=380), use_container_width=True)

    # ── Tabelle ──
    with st.expander(T["mk_rk_table"], expanded=False):
        tab = df.sort_values("eur_km")[["route", "op_label", "distance_km", "price", "eur_km", "n_days", "distance_source"]]
        st.dataframe(tab.rename(columns={
            "route": T["mk_route"], "op_label": T["ov_op"], "distance_km": "km", "price": T["mk_rk_price_col"],
            "eur_km": "€ / km", "n_days": T["mk_days"], "distance_source": T["mk_rk_source"],
        }), use_container_width=True, hide_index=True, column_config={
            "km": st.column_config.NumberColumn(format="%.0f"),
            T["mk_rk_price_col"]: st.column_config.NumberColumn(format="%.2f €"),
            "€ / km": st.column_config.NumberColumn(format="%.3f"),
        })
    st.caption(T["mk_rk_method"].format(h=h, n=MIN_DAYS))


# ══════════════════════════════════════════════════════════════════
# TAB: PREISSTRATEGIEN
# ══════════════════════════════════════════════════════════════════
def _render_yield(T, lang):
    st.caption(T["mk_ys_intro"])
    with st.spinner(T["mk_loading"]):
        curve = load_market_yield_curve()
        moves = load_market_yield_moves()
    if curve.empty or moves.empty:
        st.info(T["mk_no_data"])
        return
    moves = moves[moves["n_deps"] >= MIN_DEPS].copy()
    ops = sorted(moves["operator"], key=op_label)
    curve = curve[curve["operator"].isin(ops)]
    color_map = {op_label(o): op_color(o) for o in ops}

    # ── Anbieter im Vergleich: eine Zeile je Anbieter (Fingerabdruck) ──
    rise = curve[curve["h"] == 1].set_index("operator")["q50"] - 100
    spark = {op: curve[curve["operator"] == op].set_index("h")["q50"].reindex(HORIZONS).round(1).tolist()
             for op in ops}
    total = (moves["up"] + moves["same"] + moves["down"]).replace(0, np.nan)
    fp = pd.DataFrame({
        T["ov_op"]:              moves["operator"].map(op_label),
        T["mk_ys_col_curve"]:    moves["operator"].map(spark),
        T["mk_ys_col_rise"]:     moves["operator"].map(rise).round(0),
        T["mk_ys_col_changes"]:  moves["changes_per_dep"].round(1),
        T["mk_ys_up"]:           (moves["up"] / total * 100).round(0),
        T["mk_ys_same"]:         (moves["same"] / total * 100).round(0),
        T["mk_ys_down"]:         (moves["down"] / total * 100).round(0),
        T["mk_ys_col_deps"]:     moves["n_deps"].astype(int),
    }).sort_values(T["mk_ys_col_rise"], ascending=False)
    lo = float(np.nanmin(curve["q50"]))
    hi = float(np.nanmax(curve["q50"]))
    pct = lambda: st.column_config.ProgressColumn(format="%.0f %%", min_value=0, max_value=100)
    st.markdown(f"#### {T['mk_ys_table']}")
    st.dataframe(fp, use_container_width=True, hide_index=True, column_config={
        T["mk_ys_col_curve"]:   st.column_config.LineChartColumn(y_min=lo, y_max=hi, help=T["mk_ys_col_curve_help"]),
        T["mk_ys_col_rise"]:    st.column_config.NumberColumn(format="%+.0f %%", help=T["mk_ys_col_rise_help"]),
        T["mk_ys_col_changes"]: st.column_config.NumberColumn(format="%.1f", help=T["mk_ys_col_changes_help"]),
        T["mk_ys_up"]: pct(), T["mk_ys_same"]: pct(), T["mk_ys_down"]: pct(),
    })
    st.caption(T["mk_ys_table_note"])

    # ── Anbieter auswählen ──
    by_rise = sorted(ops, key=lambda o: -rise.get(o, -np.inf))
    sel = st.pills(T["mk_ys_pick"], by_rise, format_func=op_label, default=by_rise[0], key="mk_ys_op") or by_rise[0]

    # ── Indexkurven ──
    curve = curve.assign(op_label=curve["operator"].map(op_label), h_lbl=curve["h"].astype(str),
                         q50r=curve["q50"].round(1))
    curve["hover"] = [f"<b>{o}</b><br>+{h} {T['days_unit']}<br>Index {q:.0f} ({a:.0f}–{b:.0f})<br>{n} obs."
                      for o, h, q, a, b, n in zip(curve["op_label"], curve["h"], curve["q50"], curve["q25"],
                                                  curve["q75"], curve["n"])]
    fig = go.Figure()
    s = curve[curve["operator"] == sel].sort_values("h", ascending=False)
    fig.add_trace(go.Scatter(x=s["h_lbl"].tolist() + s["h_lbl"].tolist()[::-1],
                             y=s["q75"].round(1).tolist() + s["q25"].round(1).tolist()[::-1],
                             fill="toself", fillcolor=op_color(sel), opacity=0.15, line=dict(width=0),
                             hoverinfo="skip", showlegend=False))
    for op in ops:
        c = curve[curve["operator"] == op].sort_values("h", ascending=False)
        fig.add_trace(go.Scatter(x=c["h_lbl"].tolist(), y=c["q50r"].tolist(), mode="lines+markers",
                                 name=op_label(op), line=dict(color=op_color(op), width=4 if op == sel else 1.5),
                                 opacity=1 if op == sel else 0.45, customdata=c[["hover"]].values.tolist(),
                                 hovertemplate="%{customdata[0]}<extra></extra>"))
    fig.add_hline(y=100, line_dash="dot", line_color="rgba(128,128,128,0.6)")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=[str(h) for h in HORIZONS],
                     title=T["ov_days_adv"])
    fig.update_yaxes(title=T["mk_ys_index"])
    st.plotly_chart(_layout(fig, title=T["mk_ys_c1"].format(op=op_label(sel)), height=460,
                            legend=dict(orientation="h", y=-0.2)), use_container_width=True)

    # ── Details für den gewählten Anbieter: eine Strecke ──
    st.divider()
    st.markdown(f"#### {T['mk_ys_details'].format(op=op_label(sel))}")
    routes = load_market_ranking(14)
    routes = routes[routes["operator"] == sel].sort_values("n_days", ascending=False)
    dist = load_distances().set_index("route_id")
    if routes.empty:
        return
    labels = {r: (route_label(dist.loc[r, "origin"], dist.loc[r, "destination"], lang) if r in dist.index else r)
              for r in routes["route_id"]}
    rid = st.selectbox(T["mk_route"], list(labels), format_func=labels.get, key=f"mk_ys_route_{sel}")

    p1, p2 = st.columns(2)
    with p1:
        pts = load_market_price_points(sel, rid)
        if not pts.empty:
            pts = pts.sort_values("n", ascending=False)
            cum = pts["n"].cumsum() / pts["n"].sum()
            n80 = int((cum < 0.8).sum() + 1)
            pts = pts.sort_values("price").assign(lbl=lambda d: d["price"].map(lambda v: f"{v:.2f}"))
            fig3 = px.bar(pts, x="lbl", y="n", title=T["mk_ys_c3"],
                          labels={"lbl": T["mk_rk_price_col"], "n": T["mk_ys_obs"]},
                          color_discrete_sequence=[op_color(sel)])
            fig3.update_xaxes(type="category")
            st.plotly_chart(_layout(fig3, height=360), use_container_width=True)
            st.caption(T["mk_ys_c3_note"].format(n=len(pts), n80=n80))
    with p2:
        paths = load_market_example_paths(sel, rid)
        if not paths.empty:
            paths = paths.assign(h_lbl=paths["h"].astype(str),
                                 dep_lbl=paths["dep"].dt.tz_convert("Europe/Berlin").dt.strftime("%d.%m. %H:%M"))
            fig4 = px.line(paths, x="h_lbl", y="price", color="dep_lbl", line_shape="hv", markers=True,
                           title=T["mk_ys_c4"],
                           labels={"h_lbl": T["ov_days_adv"], "price": T["mk_rk_price_col"], "dep_lbl": T["mk_ys_dep"]})
            fig4.update_xaxes(type="category", categoryorder="array", categoryarray=[str(h) for h in HORIZONS])
            fig4.update_yaxes(rangemode="tozero")
            st.plotly_chart(_layout(fig4, height=360), use_container_width=True)
    st.caption(T["mk_ys_method"].format(n=MIN_DEPS))


# ══════════════════════════════════════════════════════════════════
# TAB: REISETAG
# ══════════════════════════════════════════════════════════════════
def _render_dayofweek(T, lang):
    st.caption(T["mk_dt_intro"])
    c1, c2 = st.columns([1, 3])
    with c1:
        h = st.selectbox(T["mk_horizon"], [1, 7, 14, 30], index=2, key="mk_dt_h",
                         format_func=lambda x: f"{x} {T['days_unit']}")
    dp = load_market_day_prices(h)
    if dp.empty:
        st.info(T["mk_no_data"])
        return
    dp = dp.copy()
    dp["idx"] = dp["price"] / dp.groupby(["operator", "route_id"])["price"].transform("mean") * 100
    dp["dow"] = dp["dep_date"].dt.dayofweek
    ops = sorted(dp["operator"].unique(), key=op_label)
    with c2:
        sel = st.selectbox(T["ov_op"], ops, format_func=op_label, key="mk_dt_op",
                           index=ops.index("italo") if "italo" in ops else 0)
    dow_names = [T["dow"][i] for i in range(7)]

    # ── Wochentag je Anbieter ──
    wk = (dp.groupby(["operator", "dow"])["idx"].mean() - 100).round(1).reset_index(name="dev")
    s = wk[wk["operator"] == sel].sort_values("dow")
    hol = _holiday_table(dp, T)

    k1, k2, k3, k4 = st.columns(4)
    mx, mn = s.loc[s["dev"].idxmax()], s.loc[s["dev"].idxmin()]
    k1.markdown(_kpi_card(T["mk_dt_max"], f"{dow_names[int(mx['dow'])]} {mx['dev']:+.0f} %", op_label(sel),
                          value_color="#ea580c"), unsafe_allow_html=True)
    k2.markdown(_kpi_card(T["mk_dt_min"], f"{dow_names[int(mn['dow'])]} {mn['dev']:+.0f} %", op_label(sel),
                          value_color="#2563eb"), unsafe_allow_html=True)
    if not hol.empty:
        k3.markdown(_kpi_card(T["mk_dt_hol"], f"{hol['eve_dev'].mean():+.0f} %", T["mk_dt_hol_sub"]),
                    unsafe_allow_html=True)
    k4.markdown(_kpi_card(T["mk_dt_days"], str(dp["dep_date"].nunique()),
                          f"{dp['dep_date'].min():%d.%m.%Y} – {dp['dep_date'].max():%d.%m.%Y}"),
                unsafe_allow_html=True)

    s = s.assign(day=s["dow"].map(lambda d: dow_names[int(d)]), lbl=s["dev"].map(lambda v: f"{v:+.0f} %"),
                 sign=np.where(s["dev"] >= 0, "+", "−"))
    fig = px.bar(s, x="day", y="dev", text="lbl", color="sign", color_discrete_map={"+": UP, "−": DOWN},
                 title=f"{T['mk_dt_c1']} — {op_label(sel)}", labels={"day": "", "dev": T["mk_dt_dev"]})
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{text}<extra></extra>")
    fig.update_xaxes(categoryorder="array", categoryarray=dow_names)
    st.plotly_chart(_layout(fig, showlegend=False, height=360), use_container_width=True)

    # ── Alle Anbieter: Wochentag-Heatmap ──
    pv = wk.pivot(index="operator", columns="dow", values="dev").reindex(columns=range(7))
    pv = pv.loc[sorted(pv.index, key=op_label)]
    z = [[None if pd.isna(v) else float(v) for v in r] for r in pv.values]
    txt = [["" if pd.isna(v) else f"{v:+.0f}" for v in r] for r in pv.values]
    zmax = max(5.0, float(np.nanmax(np.abs(pv.values))))
    fig2 = go.Figure(go.Heatmap(z=z, x=dow_names, y=[op_label(o) for o in pv.index], text=txt,
                                texttemplate="%{text}", zmin=-zmax, zmax=zmax, zmid=0, xgap=2, ygap=2,
                                colorscale=[[0, DOWN], [0.5, "#ffffff"], [1, UP]], colorbar={"title": "%"},
                                hovertemplate="%{y} · %{x}: %{text} %<extra></extra>"))
    st.plotly_chart(_layout(fig2, title=T["mk_dt_c2"], height=80 + 36 * len(pv)), use_container_width=True)

    # ── Kalender für eine Strecke ──
    dist = load_distances().set_index("route_id")
    rids = dp[dp["operator"] == sel].groupby("route_id").size().sort_values(ascending=False).index.tolist()
    labels = {r: (route_label(dist.loc[r, "origin"], dist.loc[r, "destination"], lang) if r in dist.index else r)
              for r in rids}
    rid = st.selectbox(T["mk_route"], rids, format_func=labels.get, key="mk_dt_route")
    _calendar(dp[(dp["operator"] == sel) & (dp["route_id"] == rid)], T, dow_names,
              f"{T['mk_dt_c3']} — {labels[rid]} · {op_label(sel)}")

    # ── Feiertage ──
    st.markdown(f"#### {T['mk_dt_hol_table']}")
    if hol.empty:
        st.info(T["mk_no_data"])
    else:
        st.dataframe(hol.rename(columns={
            "date": T["mk_dt_col_date"], "name": T["mk_dt_col_name"], "countries": T["mk_dt_col_countries"],
            "day_dev": T["mk_dt_col_day"], "eve_dev": T["mk_dt_col_eve"], "n": T["mk_dt_col_n"],
        }), use_container_width=True, hide_index=True, column_config={
            T["mk_dt_col_day"]: st.column_config.NumberColumn(format="%+.0f %%"),
            T["mk_dt_col_eve"]: st.column_config.NumberColumn(format="%+.0f %%"),
        })
    st.caption(T["mk_dt_method"].format(h=h))


def _holiday_table(dp, T):
    """Index on the holiday and on the day before, pooled over the operators of the holiday's countries."""
    rows = []
    for d, name, countries in HOLIDAYS:
        ops = [o for o, c in OPERATOR_MARKET.items() if c in countries]
        day = pd.Timestamp(d)
        sub = dp[dp["operator"].isin(ops)]
        on, eve = sub[sub["dep_date"] == day], sub[sub["dep_date"] == day - pd.Timedelta(days=1)]
        if len(on) < 3 and len(eve) < 3:
            continue
        rows.append({
            "date": f"{T['dow'][day.dayofweek]} {day:%d.%m.%Y}", "name": name, "countries": ", ".join(countries),
            "day_dev": round(on["idx"].mean() - 100, 1) if len(on) else None,
            "eve_dev": round(eve["idx"].mean() - 100, 1) if len(eve) else None,
            "n": len(on) + len(eve),
        })
    return pd.DataFrame(rows)


def _calendar(sub, T, dow_names, title):
    if sub.empty:
        return
    start = sub["dep_date"].min() - pd.Timedelta(days=int(sub["dep_date"].min().dayofweek))
    sub = sub.assign(week=((sub["dep_date"] - start).dt.days // 7).astype(int))
    weeks = range(int(sub["week"].max()) + 1)
    pv = sub.pivot_table(index="dow", columns="week", values="idx").reindex(index=range(7), columns=weeks)
    hol = {pd.Timestamp(d): n for d, n, _ in HOLIDAYS}
    z, txt = [], []
    for dow in range(7):
        zr, tr = [], []
        for w in weeks:
            v = pv.loc[dow, w]
            day = start + pd.Timedelta(days=w * 7 + dow)
            zr.append(None if pd.isna(v) else round(float(v), 1))
            tr.append("" if pd.isna(v) else f"{day:%d.%m.%Y} · Index {v:.0f}" + (f" · {hol[day]}" if day in hol else ""))
        z.append(zr)
        txt.append(tr)
    x = [(start + pd.Timedelta(days=w * 7)).strftime("%d.%m.") for w in weeks]
    fig = go.Figure(go.Heatmap(z=z, x=x, y=dow_names, text=txt, zmid=100, xgap=2, ygap=2,
                               colorscale=[[0, DOWN], [0.5, "#f3f4f6"], [1, UP]], colorbar={"title": "Index"},
                               hovertemplate="%{text}<extra></extra>"))
    # mark holidays
    hx, hy = [], []
    for day in hol:
        w = (day - start).days // 7
        if 0 <= w < len(x):
            hx.append(x[w])
            hy.append(dow_names[day.dayofweek])
    if hx:
        fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers", marker=dict(symbol="circle-open", size=14,
                                 color="#111827", line=dict(width=2)), hoverinfo="skip", showlegend=False))
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=dow_names)
    fig.update_xaxes(type="category")
    st.plotly_chart(_layout(fig, title=title, height=330), use_container_width=True)
    st.caption(T["mk_dt_c3_note"])


def render_market(T):
    lang = st.session_state.lang
    st.subheader(T["mk_head"])
    if is_offline_mode():
        st.info(T["mk_offline"])
        return
    st.caption(T["mk_intro"])
    t1, t2, t3 = st.tabs([T["mk_tab_ranking"], T["mk_tab_yield"], T["mk_tab_day"]])
    with t1:
        _render_ranking(T, lang)
    with t2:
        _render_yield(T, lang)
    with t3:
        _render_dayofweek(T, lang)
