# dashboard/views/time_of_day.py
import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.config import op_color, op_label
from dashboard.database import load_time_of_day


def render_time_of_day(route, T):
    st.subheader(T["dt_head"].format(orig=route["origin_name"], dest=route["destination_name"]))

    origin, destination = route["origin_name"], route["destination_name"]
    operators = route["operators"]

    sel_op = st.selectbox(T["dt_op"], operators, format_func=op_label, key="dt_op")

    df_dt = load_time_of_day(origin, destination, sel_op)
    if df_dt.empty:
        st.info(T["dt_no"])
        return

    df_dt = df_dt.dropna(subset=["dep_hour"]).copy()
    df_dt["dep_hour"] = df_dt["dep_hour"].astype(int)

    n_hours = df_dt["dep_hour"].nunique()
    if n_hours < 8:
        st.warning(T["dt_coverage_warn"].format(n=n_hours, op=op_label(sel_op)))

    DOW = T["dow"]

    # ── Avg. Preis nach Stunde ──
    df_hour = (df_dt.groupby("dep_hour")["price_eur"].mean().reset_index()
               .rename(columns={"price_eur": "price_avg"}))
    df_hour["hour_label"] = df_hour["dep_hour"].astype(str).str.zfill(2) + ":00"
    fig = px.bar(df_hour, x="hour_label", y="price_avg", color="price_avg",
                 color_continuous_scale=["#a8e44a", "#ffb547", "#ff5f5f"],
                 title=T["dt_c1"].format(op=op_label(sel_op)),
                 labels={"hour_label": T["ov_dep_hour"], "price_avg": T["ov_avg"]})
    fig.update_coloraxes(showscale=False)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # ── Heatmap: Wochentag × Stunde ──
    df_dt["dow_label"] = df_dt["dep_dow"].map(lambda d: DOW.get(int(d)) if pd.notna(d) else None)
    df_dt["hour_label"] = df_dt["dep_hour"].astype(str).str.zfill(2) + ":00"
    ph = df_dt.pivot_table(index="dow_label", columns="hour_label", values="price_eur", aggfunc="mean").round(4)
    ph = ph.reindex([d for d in DOW.values() if d in ph.index])
    if not ph.empty:
        fig2 = px.imshow(ph, color_continuous_scale=["#1a3a1a", "#a8e44a", "#ffb547", "#ff5f5f"],
                         labels={"x": T["ov_dep_hour"], "y": T["dt_wd"], "color": T["ov_avg"]},
                         title=T["dt_c2"].format(op=op_label(sel_op)), aspect="auto")
        fig2.update_xaxes(tickangle=45)
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Sitzplatz nach Stunde ──
    df_seats = df_dt.dropna(subset=["seats_available"])
    if not df_seats.empty:
        df_sh = (df_seats.groupby("dep_hour")["seats_available"].mean().reset_index()
                 .rename(columns={"seats_available": "seats_avg"}))
        df_sh["hour_label"] = df_sh["dep_hour"].astype(str).str.zfill(2) + ":00"
        fig3 = px.line(df_sh, x="hour_label", y="seats_avg", markers=True,
                       title=T["dt_c3"].format(op=op_label(sel_op)),
                       labels={"hour_label": T["ov_dep_hour"], "seats_avg": T["dt_seats"]},
                       color_discrete_sequence=[op_color(sel_op)])
        fig3.update_traces(line_width=2)
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.caption(T["dt_seats_none"])

    # ── KPI-Karten: günstigste/teuerste Stunde & Tag ──
    if not df_hour.empty:
        minh = df_hour.loc[df_hour["price_avg"].idxmin()]
        maxh = df_hour.loc[df_hour["price_avg"].idxmax()]
        df_dow = df_dt.dropna(subset=["dow_label"]).groupby("dow_label")["price_eur"].mean()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(T["dt_ch_h"], minh["hour_label"], f"Avg. {float(minh['price_avg']):.2f} €")
        c2.metric(T["dt_ex_h"], maxh["hour_label"], f"Avg. {float(maxh['price_avg']):.2f} €")
        if not df_dow.empty:
            c3.metric(T["dt_ch_d"], df_dow.idxmin(), f"Avg. {float(df_dow.min()):.2f} €")
            c4.metric(T["dt_ex_d"], df_dow.idxmax(), f"Avg. {float(df_dow.max()):.2f} €")