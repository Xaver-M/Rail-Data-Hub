# dashboard/views/crawler_status.py
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timezone

from dashboard.config import op_color, op_label, time_since
from dashboard.database import (
    load_crawler_overview, load_crawler_stats_by_operator,
    load_crawler_daily_counts, load_crawler_health,
)


def render_crawler_status(T):
    st.subheader(T["cr_head"])

    # ══════════════════════════════════════════════════════════════════
    # DATENÜBERSICHT – KPIs
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(T["cr_data"])

        overview = load_crawler_overview()
        if not overview.empty:
            row = overview.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(T["cr_total"], f"{int(row['total_records']):,}".replace(",", "."))
            c2.metric(T["cr_ops"], int(row["n_operators"]))
            c3.metric(T["cr_routes"], int(row["n_routes"]))
            c4.metric(T["cr_last"], time_since(row["last_collected"], T))

        df_by_op = load_crawler_stats_by_operator()
        if not df_by_op.empty:
            df_by_op["op_label"] = df_by_op["operator"].map(op_label)
            color_map = {op_label(o): op_color(o) for o in df_by_op["operator"].unique()}

            # Balkendiagramm: Records pro Operator
            fig = px.bar(
                df_by_op.sort_values("records"),
                x="records", y="op_label", orientation="h",
                color="op_label", color_discrete_map=color_map,
                title=T["cr_c1"],
                labels={"records": T["cr_rec"], "op_label": T["cr_cr"]}
            )
            fig.update_xaxes(rangemode="tozero")
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            # Gestapeltes Balkendiagramm: tägliche Records pro Operator
            df_daily = load_crawler_daily_counts(days_back=45)
            if not df_daily.empty:
                df_daily["op_label"] = df_daily["operator"].map(op_label)
                fig2 = px.bar(
                    df_daily, x="col_date", y="records",
                    color="op_label", color_discrete_map=color_map,
                    title=T["cr_c2"],
                    labels={"col_date": T["cr_date"], "records": T["cr_rec"], "op_label": T["cr_cr"]}
                )
                fig2.update_yaxes(rangemode="tozero")
                fig2.update_layout(barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════
    # 7-TAGE-GESUNDHEITS-AMPEL
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(T["cr_health"])
        st.caption(T["cr_health_cap"])

        health_df = load_crawler_health(days_back=7)
        if not health_df.empty:
            summary = (
                health_df.groupby("operator")
                .agg(days_with_data=("col_date", "nunique"), avg_per_day=("records", "mean"))
                .reset_index()
                .sort_values("days_with_data", ascending=False)
            )

            for _, r in summary.iterrows():
                days_ok = int(r["days_with_data"])
                if days_ok >= 6:
                    icon = T["cr_health_ok"]
                elif days_ok >= 3:
                    icon = T["cr_health_warn"]
                else:
                    icon = T["cr_health_bad"]

                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(
                    f'{icon} <span style="color:{op_color(r["operator"])}">●</span> '
                    f'**{op_label(r["operator"])}**',
                    unsafe_allow_html=True
                )
                c2.caption(f"{days_ok} / 7 {T['days_unit']}")
                c3.caption(f"{T['cr_avg_day']}: {r['avg_per_day']:.0f}")
        else:
            st.info(T["no_data"])

    # ══════════════════════════════════════════════════════════════════
    # STATUS PRO CRAWLER (DB-basiert)
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(T["cr_status"])
        st.caption(T["cr_stat_cap"])

        df_by_op = load_crawler_stats_by_operator()
        if df_by_op.empty:
            st.info(T["no_data"])
        else:
            # Header
            h1, h2, h3, h4, h5 = st.columns([2, 2, 1, 1, 2])
            h1.caption("**Anbieter**")
            h2.caption("**Letzter Lauf**")
            h3.caption("**Records**")
            h4.caption("**Routen**")
            h5.caption("**Ø Preis**")

            st.divider()

            for _, r in df_by_op.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 2])
                with c1:
                    st.markdown(
                        f'<span style="color:{op_color(r["operator"])}">●</span> '
                        f'**{op_label(r["operator"])}**',
                        unsafe_allow_html=True
                    )
                c2.metric("", time_since(r["last_collected"], T), label_visibility="collapsed")
                c3.metric("", f"{int(r['records']):,}".replace(",", "."), label_visibility="collapsed")
                c4.metric("", int(r["routes"]), label_visibility="collapsed")
                c5.metric("", f"{float(r['avg_price']):.2f} €", label_visibility="collapsed")