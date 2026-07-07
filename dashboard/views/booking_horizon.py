# dashboard/views/booking_horizon.py
import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.config import op_color, op_label, price_basis_toggle
from dashboard.database import load_booking_horizon


def render_booking_horizon(route, T):
    st.subheader(T["bh_head"].format(orig=route["origin_name"], dest=route["destination_name"]))

    origin, destination = route["origin_name"], route["destination_name"]

    df_bh = load_booking_horizon(origin, destination)
    if df_bh.empty:
        st.info(T["bh_no"])
        return

    df_bh["booking_horizon_days"] = pd.to_numeric(df_bh["booking_horizon_days"]).astype(int)
    df_bh["price_avg"] = pd.to_numeric(df_bh["price_avg"])
    df_bh["price_min"] = pd.to_numeric(df_bh["price_min"])
    df_bh["price_max"] = pd.to_numeric(df_bh["price_max"])
    df_bh["observations"] = pd.to_numeric(df_bh["observations"])
    df_bh["op_label"] = df_bh["operator"].map(op_label)
    color_map = {op_label(o): op_color(o) for o in df_bh["operator"].unique()}

    # ── Toggle ──
    basis = price_basis_toggle("bh_basis", T)
    y_col = {"min": "price_min", "avg": "price_avg", "max": "price_max"}[basis]
    y_lbl = {"min": T["price_min"], "avg": T["price_avg"], "max": T["price_max_label"]}[basis]

    # ── Optimaler Buchungszeitpunkt (KPI-Karten) ──
    st.write(f"#### 💡 {T['bh_opt']}")
    ops = sorted(df_bh["operator"].unique())
    opt_cols = st.columns(max(1, len(ops)))
    for idx, op in enumerate(ops):
        df_op = df_bh[df_bh["operator"] == op]
        if df_op.empty:
            continue
        cheapest_row = df_op.loc[df_op[y_col].idxmin()]
        max_price = df_op[y_col].max()
        savings_pct = ((max_price - cheapest_row[y_col]) / max_price * 100) if max_price > 0 else 0
        with opt_cols[idx]:
            st.markdown(f"""
            <div class="kpi-card" style="border-top: 4px solid {op_color(op)};">
                <div class="kpi-title">{op_label(op)}</div>
                <div class="kpi-value">+{int(cheapest_row['booking_horizon_days'])} {T['days_unit']}</div>
                <div class="kpi-subtitle">{T['bh_cheap']} {cheapest_row[y_col]:.2f} €</div>
                <div class="kpi-subtitle" style="color:#a8e44a; font-weight:bold;">{T['bh_saves'].format(pct=savings_pct)}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Charts ──
    c1, c2 = st.columns(2)

    with c1:
        st.write(f"#### 📊 {T['bh_c1']} ({y_lbl})")
        fig1 = px.line(df_bh, x="booking_horizon_days", y=y_col, color="op_label",
                      color_discrete_map=color_map, markers=True,
                      labels={"booking_horizon_days": T["ov_days_adv"], y_col: y_lbl, "op_label": T["ov_op"]},
                      custom_data=["observations", "price_min", "price_avg", "price_max"])
        fig1.update_traces(line_width=2, marker_size=7,
                          hovertemplate="<b>%{fullData.name}</b><br>+%{x} days<br>"
                                        f"{y_lbl}: " + "%{y:.2f} €"
                                        "<br>Min %{customdata[1]:.2f} €"
                                        "<br>Avg %{customdata[2]:.2f} €"
                                        "<br>Max %{customdata[3]:.2f} €"
                                        "<br>%{customdata[0]} obs.")
        fig1.update_xaxes(autorange="reversed")
        fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.write(f"#### 📈 {T['bh_c2']}")
        fig2 = px.bar(df_bh, x="booking_horizon_days", y="observations", color="op_label",
                      color_discrete_map=color_map, barmode="group",
                      labels={"booking_horizon_days": T["ov_days_adv"], "observations": T["bh_conn"], "op_label": T["ov_op"]})
        fig2.update_xaxes(autorange="reversed")
        fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Detailtabelle ──
    st.write(f"#### 📋 {T['bh_table']} ({y_lbl})")
    pivot = df_bh.pivot_table(index="operator", columns="booking_horizon_days", values=y_col).round(4)
    pivot.index = pivot.index.map(op_label)
    pivot.columns = [f"+{int(c)}d" for c in pivot.columns]
    pivot = pivot[sorted(pivot.columns, key=lambda c: int(c.strip("+d")))]
    st.dataframe(pivot.style.format("{:.2f} €", na_rep="—"), use_container_width=True)