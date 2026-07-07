# dashboard/views/overview.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import op_color, op_label, price_basis_toggle
from dashboard.database import (
    load_overview_kpis, load_timeline_data, load_price_range_by_operator,
    load_departure_hour_counts, load_fare_class_avg,
    load_available_departure_dates, load_trip_data,
    load_normalized_price_data, load_distances,
)


def _kpi_card(title, value, subtitle="", value_color=None, badge_color=None):
    color_style = f"color:{value_color};" if value_color else ""
    sub = ""
    if badge_color and subtitle:
        sub = f'<div class="kpi-badge" style="color:{badge_color};border-color:{badge_color};">{subtitle}</div>'
    elif subtitle:
        sub = f'<div class="kpi-subtitle">{subtitle}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value" style="{color_style}">{value}</div>
        {sub}
    </div>
    """


def render_overview(route, T):
    st.subheader(f"{route['origin_name']} → {route['destination_name']}")

    origin, destination = route["origin_name"], route["destination_name"]

    view_mode = st.radio(
        T["ov_mode"], options=["route", "trip"],
        format_func=lambda m: T["ov_mode_route"] if m == "route" else T["ov_mode_trip"],
        horizontal=True, key="ov_view_mode",
    )

    # ══════════════════════════════════════════════════════════════════
    # MODUS A: EINZELNE REISE
    # ══════════════════════════════════════════════════════════════════
    if view_mode == "trip":
        dates_df = load_available_departure_dates(origin, destination)
        if dates_df.empty:
            st.info(T["ov_no_data"])
            return

        avail_dates = sorted(dates_df["dep_date"].tolist())
        default_date = dates_df.loc[dates_df["n"].idxmax(), "dep_date"]

        sel_date = st.date_input(
            T["ov_dep_date"], value=default_date,
            min_value=avail_dates[0], max_value=avail_dates[-1],
            key="ov_dep_date_input",
        )

        df_trip = load_trip_data(origin, destination, sel_date)

        if df_trip.empty:
            st.info(T["ov_no_trip_data"])
            nearest = sorted(avail_dates, key=lambda d: abs((d - sel_date).days))[:5]
            st.caption(f'{T["ov_nearest"]} ' + ", ".join(d.strftime("%d.%m.%Y") for d in sorted(nearest)))
            return

        # ── Toggle ──
        basis = price_basis_toggle("ov_trip_basis", T)

        min_price = float(df_trip["price_eur"].min())
        max_price = float(df_trip["price_eur"].max())
        min_op    = df_trip.loc[df_trip["price_eur"].idxmin(), "operator"]
        max_op    = df_trip.loc[df_trip["price_eur"].idxmax(), "operator"]
        avg_price = float(df_trip["price_eur"].mean())
        recent    = df_trip["collected_at"] >= (df_trip["collected_at"].max() - pd.Timedelta(days=7))
        base      = df_trip[~recent]["price_eur"].mean()
        trend     = ((df_trip[recent]["price_eur"].mean() - base) / base * 100) if (pd.notna(base) and base) else 0
        trend_color = "#ef4444" if trend > 1 else "#22c55e" if trend < -1 else None
        trend_val   = f"▲ +{trend:.1f}%" if trend > 1 else f"▼ {trend:.1f}%" if trend < -1 else "± 0.0%"

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(_kpi_card(T["ov_lowest_price"], f"{min_price:.2f} €",
                                  op_label(min_op), value_color="#22c55e",
                                  badge_color=op_color(min_op)), unsafe_allow_html=True)
        with c2:
            st.markdown(_kpi_card(T["ov_avg_price"], f"{avg_price:.2f} €"), unsafe_allow_html=True)
        with c3:
            st.markdown(_kpi_card(T["ov_max_price"], f"{max_price:.2f} €",
                                  op_label(max_op), value_color="#f97316",
                                  badge_color=op_color(max_op)), unsafe_allow_html=True)
        with c4:
            st.markdown(_kpi_card(T["ov_trend_trip"], trend_val,
                                  T["ov_trend_sub"], value_color=trend_color), unsafe_allow_html=True)
        with c5:
            st.markdown(_kpi_card(T["ov_operators"], str(df_trip["operator"].nunique())), unsafe_allow_html=True)

        df_hz = (df_trip.dropna(subset=["booking_horizon_days"])
                 .groupby(["operator", "booking_horizon_days"])
                 .agg(price_avg=("price_eur", "mean"), price_min=("price_eur", "min"),
                      price_max=("price_eur", "max"), observations=("price_eur", "count"))
                 .reset_index())

        if df_hz.empty:
            st.info(T["ov_no_trip_data"])
            return

        y_col = {"min": "price_min", "avg": "price_avg", "max": "price_max"}[basis]
        y_lbl = {"min": T["price_min"], "avg": T["price_avg"], "max": T["price_max_label"]}[basis]

        df_hz["op_label"] = df_hz["operator"].map(op_label)
        df_hz["booking_horizon_days"] = df_hz["booking_horizon_days"].astype(int)
        df_hz = df_hz.sort_values("booking_horizon_days")
        color_map = {op_label(o): op_color(o) for o in df_hz["operator"].unique()}

        covered = int(df_hz["booking_horizon_days"].nunique())
        hmax    = int(df_hz["booking_horizon_days"].max())
        hmin    = int(df_hz["booking_horizon_days"].min())
        obs_tot = int(df_hz["observations"].sum())
        st.caption(T["ov_data_maturity"].format(hmax=hmax, hmin=hmin, covered=covered, obs=obs_tot))

        fig = px.line(df_hz, x="booking_horizon_days", y=y_col,
                      color="op_label", color_discrete_map=color_map, markers=True,
                      title=T["ov_trip_dev"].format(date=sel_date.strftime("%d.%m.%Y")),
                      labels={"booking_horizon_days": T["ov_days_adv"], y_col: y_lbl, "op_label": T["ov_op"]},
                      custom_data=["price_min", "price_avg", "price_max", "observations"])
        fig.update_traces(line_width=2, marker_size=6,
                          hovertemplate="<b>%{fullData.name}</b><br>+%{x} " + T["days_unit"] +
                                        "<br>Min %{customdata[0]:.2f} €"
                                        "<br>Avg %{customdata[1]:.2f} €"
                                        "<br>Max %{customdata[2]:.2f} €"
                                        "<br>%{customdata[3]} obs.")
        fig.update_xaxes(autorange="reversed")
        fig.update_yaxes(rangemode="tozero")
        fig.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        return

    # ══════════════════════════════════════════════════════════════════
    # MODUS B: STRECKE GESAMT
    # ══════════════════════════════════════════════════════════════════
    days = st.slider(T["ov_time_range"], 7, 90, 30, key="ov_days")

    # ── Toggle ──
    basis = price_basis_toggle("ov_route_basis", T)
    y_col = {"min": "min_price", "avg": "avg_price", "max": "max_price"}[basis]
    y_lbl = {"min": T["price_min"], "avg": T["price_avg"], "max": T["price_max_label"]}[basis]

    kpi_df = load_overview_kpis(origin, destination, days)
    if kpi_df.empty or pd.isna(kpi_df.iloc[0]["total_obs"]) or kpi_df.iloc[0]["total_obs"] == 0:
        st.info(T["ov_no_data"])
        return

    row = kpi_df.iloc[0]
    min_price = float(row["min_price"])
    avg_price = float(row["avg_price"])
    recent_avg = row.get("recent_avg")
    prior_avg  = row.get("prior_avg")
    trend = 0.0
    if pd.notna(recent_avg) and pd.notna(prior_avg) and prior_avg:
        trend = (float(recent_avg) - float(prior_avg)) / float(prior_avg) * 100

    timeline_df = load_timeline_data(origin, destination, days)
    if timeline_df.empty:
        st.info(T["ov_no_data"])
        return

    min_op_row  = timeline_df.loc[timeline_df["min_price"].idxmin()]
    max_op_row  = timeline_df.loc[timeline_df["max_price"].idxmax()]
    route_max   = float(max_op_row["max_price"])
    trend_color = "#ef4444" if trend > 1 else "#22c55e" if trend < -1 else None
    trend_val   = f"▲ +{trend:.1f}%" if trend > 1 else f"▼ {trend:.1f}%" if trend < -1 else "± 0.0%"

    # ── €/km und €/h ──
    dist_df = load_distances()
    route_id = route.get("route_id")
    haversine_km = None
    if route_id is not None and not dist_df.empty:
        match = dist_df[dist_df["route_id"] == route_id]
        if not match.empty:
            haversine_km = float(match.iloc[0]["haversine_km"])

    norm_df = load_normalized_price_data(origin, destination)
    avg_travel_h = float(norm_df["travel_h"].mean()) if not norm_df.empty and norm_df["travel_h"].notna().any() else None

    eur_km_val = f"{avg_price / haversine_km:.3f} €" if haversine_km else "—"
    eur_km_sub = T["ov_km_sub"].format(km=haversine_km) if haversine_km else T["ov_no_dist"]
    eur_h_val  = f"{avg_price / avg_travel_h:.2f} €" if avg_travel_h else "—"
    eur_h_sub  = T["ov_h_sub"].format(h=avg_travel_h) if avg_travel_h else T["ov_no_time"]

    # ── KPI-Zeile ──
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(_kpi_card(T["ov_lowest_price"], f"{min_price:.2f} €",
                              op_label(min_op_row["operator"]), value_color="#22c55e",
                              badge_color=op_color(min_op_row["operator"])), unsafe_allow_html=True)
    with c2:
        st.markdown(_kpi_card(T["ov_avg_price"], f"{avg_price:.2f} €"), unsafe_allow_html=True)
    with c3:
        st.markdown(_kpi_card(T["ov_max_price"], f"{route_max:.2f} €",
                              op_label(max_op_row["operator"]), value_color="#f97316",
                              badge_color=op_color(max_op_row["operator"])), unsafe_allow_html=True)
    with c4:
        st.markdown(_kpi_card(T["ov_trend"], trend_val,
                              T["ov_trend_sub"], value_color=trend_color), unsafe_allow_html=True)
    with c5:
        st.markdown(_kpi_card(T["ov_operators"], str(int(row["n_operators"]))), unsafe_allow_html=True)

    c6, c7, _ = st.columns([2, 2, 1])
    with c6:
        st.markdown(_kpi_card(T["ov_eur_km"], eur_km_val, eur_km_sub), unsafe_allow_html=True)
    with c7:
        st.markdown(_kpi_card(T["ov_eur_h"], eur_h_val, eur_h_sub), unsafe_allow_html=True)

    # ── Zeitverlauf mit Toggle ──
    timeline_df["op_label"] = timeline_df["operator"].map(op_label)
    color_map = {op_label(o): op_color(o) for o in timeline_df["operator"].unique()}

    fig = px.line(timeline_df, x="col_date", y=y_col, color="op_label",
                  color_discrete_map=color_map, markers=True,
                  title=f"{T['ov_c1'].format(days=days)} ({y_lbl})",
                  labels={"col_date": T["ov_date"], y_col: y_lbl, "op_label": T["ov_op"]},
                  custom_data=["min_price", "avg_price", "max_price"])
    fig.update_traces(line_width=2, marker_size=5,
                      hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>"
                                    "Min %{customdata[0]:.2f} €<br>"
                                    "Avg %{customdata[1]:.2f} €<br>"
                                    "Max %{customdata[2]:.2f} €")
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(T["ov_c1_note"])

    # ── Preisspanne Min/Avg/Max pro Operator ──
    range_df = load_price_range_by_operator(origin, destination)
    if not range_df.empty:
        fig2 = go.Figure()
        for _, r in range_df.iterrows():
            lbl, col = op_label(r["operator"]), op_color(r["operator"])
            fig2.add_trace(go.Scatter(x=[lbl, lbl], y=[float(r["price_min"]), float(r["price_max"])],
                                       mode="lines", line=dict(color=col, width=4), showlegend=False))
            fig2.add_trace(go.Scatter(x=[lbl], y=[float(r["price_avg"])], mode="markers",
                                       marker=dict(color="#fff", size=10, symbol="diamond",
                                                   line=dict(color=col, width=2)), name=lbl))
        fig2.update_yaxes(rangemode="tozero")
        fig2.update_layout(title=T["ov_c2"], yaxis_title=T["ov_price"],
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Abfahrtsstunden ──
    hour_df = load_departure_hour_counts(origin, destination)
    if not hour_df.empty:
        hour_df["dep_hour"] = pd.to_numeric(hour_df["dep_hour"]).astype(int)
        hour_df["op_label"] = hour_df["operator"].map(op_label)
        hour_df["hour_label"] = hour_df["dep_hour"].astype(str).str.zfill(2) + ":00"
        color_map2 = {op_label(o): op_color(o) for o in hour_df["operator"].unique()}
        fig3 = px.bar(hour_df, x="hour_label", y="connection_count", color="op_label",
                      color_discrete_map=color_map2, barmode="group", title=T["ov_c3"],
                      labels={"hour_label": T["ov_dep_hour"], "connection_count": T["ov_count"], "op_label": T["ov_op"]})
        fig3.update_yaxes(rangemode="tozero")
        fig3.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(T["ov_dep_hour_note"])

    # ── Tarifklassen ──
    route_ops = set(route.get("operators", []))
    fare_df = load_fare_class_avg(origin, destination) if route_ops & {"italo", "trenitalia"} else pd.DataFrame()
    if not fare_df.empty:
        st.subheader(T["ov_fare_classes"])
        fare_df["op_label"] = fare_df["operator"].map(op_label)
        color_map3 = {op_label(o): op_color(o) for o in fare_df["operator"].unique()}
        fig4 = px.bar(fare_df, x="fare_class", y="avg_price", color="op_label",
                      color_discrete_map=color_map3, barmode="group", title=T["ov_c5"],
                      labels={"fare_class": T["ov_class"], "avg_price": T["ov_avg"], "op_label": T["ov_op"]})
        fig4.update_yaxes(rangemode="tozero")
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)