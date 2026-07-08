# dashboard/views/normalized_prices.py
import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.config import op_color, op_label, station_name
from dashboard.database import load_normalized_price_data, load_distances


def render_normalized_prices(route, T):
    lang = st.session_state.lang
    st.subheader(T["nm_head"].format(orig=station_name(route["origin_name"], lang),
                                      dest=station_name(route["destination_name"], lang)))

    origin, destination = route["origin_name"], route["destination_name"]

    dist_df = load_distances()
    route_dist_row = dist_df[dist_df["route_id"] == route["route_id"]]
    if route_dist_row.empty:
        st.info(T["nm_no_dist"])
        return
    dist_km = float(route_dist_row["haversine_km"].iloc[0])
    st.caption(f"{T['nm_dist']}: **{dist_km:.1f} {T['nm_km']}** —  {T['nm_note']}")

    with st.spinner("..."):
        df_norm_raw = load_normalized_price_data(origin, destination)

    if df_norm_raw.empty:
        st.info(T["nm_no_time"])
        return

    # ── Steuerelemente: Preisbasis + Verbindungstyp ──
    cbasis, cdirect = st.columns(2)
    with cbasis:
        basis = st.radio(T["price_basis"], options=["min", "avg", "max"],
                         format_func=lambda m: {"min": T["price_min"], "avg": T["price_avg"], "max": "Max"}[m],
                         horizontal=True, key="nm_basis", help=T["price_basis_help"])
    with cdirect:
        direct_choice = st.radio(T["direct_filter"], options=["all", "direct", "transfer"],
                                 format_func=lambda m: {"all": T["direct_all"], "direct": T["direct_only"],
                                                        "transfer": T["direct_transfer"]}[m],
                                 horizontal=True, key="nm_direct")

    df_t = df_norm_raw.copy()
    if direct_choice == "direct":
        df_t = df_t[df_t["is_direct"] == True]
    elif direct_choice == "transfer":
        df_t = df_t[df_t["is_direct"] == False]

    if df_t.empty:
        st.info(T["nm_no_time"])
        return

    df_t["eur_per_km"] = df_t["price_eur"] / dist_km
    df_t["eur_per_h"]  = df_t["price_eur"] / df_t["travel_h"]

    df_agg = (df_t.groupby(["operator", "booking_horizon_days"])
              .agg(eur_km_min=("eur_per_km", "min"), eur_km_avg=("eur_per_km", "mean"), eur_km_max=("eur_per_km", "max"),
                   eur_h_min=("eur_per_h", "min"),   eur_h_avg=("eur_per_h", "mean"), eur_h_max=("eur_per_h", "max"),
                   travel_h_avg=("travel_h", "mean"), observations=("price_eur", "count"))
              .reset_index())
    df_agg["op_label"] = df_agg["operator"].map(op_label)
    df_agg = df_agg.sort_values(["operator", "booking_horizon_days"])
    color_map = {op_label(o): op_color(o) for o in df_agg["operator"].unique()}

    # Auswahl der Spalten basierend auf Basis
    if basis == "min":
        ykm, yh, basis_lbl = "eur_km_min", "eur_h_min", T["price_min"]
    elif basis == "avg":
        ykm, yh, basis_lbl = "eur_km_avg", "eur_h_avg", T["price_avg"]
    else:
        ykm, yh, basis_lbl = "eur_km_max", "eur_h_max", T["price_max_label"]

    st.caption(T["nm_basis_note"])

    # ── Summary ──
    overall_km = float(df_t["eur_per_km"].mean())
    overall_h  = float(df_t["eur_per_h"].mean())
    default_hz = 14 if 14 in df_agg["booking_horizon_days"].values else int(df_agg["booking_horizon_days"].median())
    st.markdown(T["nm_summary"].format(eurkm=overall_km, eurh=overall_h, basis=basis_lbl, days=default_hz))

    st.markdown("---")

    # ── Chart 1: €/km nach Horizont ──
    fig1 = px.line(df_agg, x="booking_horizon_days", y=ykm, color="op_label", color_discrete_map=color_map,
                  markers=True, title=T["nm_c1"] + f"  ({basis_lbl})",
                  labels={"booking_horizon_days": T["nm_hz"], ykm: T["nm_eur_km"], "op_label": T["nm_op"]},
                  custom_data=["eur_km_avg", "observations"])
    fig1.update_traces(line_width=2, marker_size=6,
                       hovertemplate="<b>%{fullData.name}</b><br>+%{x} days<br>%{y:.3f} €/km<br>%{customdata[1]} obs.")
    fig1.update_xaxes(autorange="reversed")
    fig1.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: €/h nach Horizont ──
    fig2 = px.line(df_agg, x="booking_horizon_days", y=yh, color="op_label", color_discrete_map=color_map,
                  markers=True, title=T["nm_c2"] + f"  ({basis_lbl})",
                  labels={"booking_horizon_days": T["nm_hz"], yh: T["nm_eur_h"], "op_label": T["nm_op"]},
                  custom_data=["travel_h_avg", "observations"])
    fig2.update_traces(line_width=2, marker_size=6,
                       hovertemplate="<b>%{fullData.name}</b><br>+%{x} days<br>%{y:.2f} €/h<br>"
                                     "Avg travel %{customdata[0]:.2f} h<br>%{customdata[1]} obs.")
    fig2.update_xaxes(autorange="reversed")
    fig2.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Chart 3: Scatter €/km vs €/h bei wählbarem Horizont ──
    avail_hz = sorted(df_agg["booking_horizon_days"].unique().tolist())
    hz_scatter = st.select_slider(T["nm_hz_sel"], options=avail_hz,
                                  value=14 if 14 in avail_hz else avail_hz[len(avail_hz) // 2], key="nm_hz_scatter")
    df_sc = df_agg[df_agg["booking_horizon_days"] == hz_scatter]
    if not df_sc.empty:
        fig3 = px.scatter(df_sc, x="eur_km_avg", y="eur_h_avg", color="op_label", color_discrete_map=color_map,
                          size="observations", text="op_label", title=T["nm_c3"].format(days=hz_scatter),
                          labels={"eur_km_avg": T["nm_eur_km"], "eur_h_avg": T["nm_eur_h"], "op_label": T["nm_op"]},
                          custom_data=["travel_h_avg", "observations"])
        fig3.update_traces(textposition="top center",
                           hovertemplate="<b>%{text}</b><br>%{x:.3f} €/km<br>%{y:.2f} €/h<br>"
                                         "Avg travel %{customdata[0]:.2f} h<br>%{customdata[1]} obs.")
        fig3.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Chart 4: Boxplot €/km über alle Horizonte ──
    df_t["op_label"] = df_t["operator"].map(op_label)
    fig4 = px.box(df_t, x="op_label", y="eur_per_km", color="op_label", color_discrete_map=color_map,
                 points="outliers", title=T["nm_c4"],
                 labels={"op_label": T["nm_op"], "eur_per_km": T["nm_eur_km"]})
    fig4.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig4, use_container_width=True)
