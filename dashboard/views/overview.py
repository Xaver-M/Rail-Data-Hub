# dashboard/views/overview.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import op_color, op_label
from dashboard.database import (
    load_overview_kpis, load_timeline_data, load_price_range_by_operator,
    load_departure_hour_counts, load_fare_class_avg,
    load_available_departure_dates, load_trip_data,
)


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

        trains = sorted(t for t in df_trip["train_number"].dropna().unique() if t != "")
        train_opts = ["__all__"] + trains
        sel_train = st.selectbox(
            T["ov_train_filter"], train_opts,
            format_func=lambda t: T["ov_all_trains"] if t == "__all__" else str(t),
            key="ov_train_filter_select",
        )
        if sel_train != "__all__":
            df_trip = df_trip[df_trip["train_number"] == sel_train].copy()

        if df_trip.empty:
            st.info(T["ov_no_trip_data"])
            return

        min_price = float(df_trip["price_eur"].min())
        min_op    = df_trip.loc[df_trip["price_eur"].idxmin(), "operator"]
        avg_price = float(df_trip["price_eur"].mean())
        recent    = df_trip["collected_at"] >= (df_trip["collected_at"].max() - pd.Timedelta(days=7))
        base      = df_trip[~recent]["price_eur"].mean()
        trend     = ((df_trip[recent]["price_eur"].mean() - base) / base * 100) if (pd.notna(base) and base) else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(T["ov_lowest_price"], f"{min_price:.2f} €", op_label(min_op))
        c2.metric(T["ov_avg_price"], f"{avg_price:.2f} €")
        c3.metric(T["ov_trend_trip"], f"{trend:+.1f}%", delta=f"{trend:+.1f}%",
                  delta_color="inverse", help=T["ov_trend_trip_help"])
        c4.metric(T["ov_operators"], df_trip["operator"].nunique())

        df_hz = (df_trip.dropna(subset=["booking_horizon_days"])
                 .groupby(["operator", "booking_horizon_days"])
                 .agg(price_avg=("price_eur", "mean"), price_min=("price_eur", "min"),
                      observations=("price_eur", "count"))
                 .reset_index())

        if df_hz.empty:
            st.info(T["ov_no_trip_data"])
            return

        df_hz["op_label"] = df_hz["operator"].map(op_label)
        df_hz["booking_horizon_days"] = df_hz["booking_horizon_days"].astype(int)
        df_hz = df_hz.sort_values("booking_horizon_days")
        color_map = {op_label(o): op_color(o) for o in df_hz["operator"].unique()}

        covered = int(df_hz["booking_horizon_days"].nunique())
        hmax    = int(df_hz["booking_horizon_days"].max())
        hmin    = int(df_hz["booking_horizon_days"].min())
        obs_tot = int(df_hz["observations"].sum())
        st.caption(T["ov_data_maturity"].format(hmax=hmax, hmin=hmin, covered=covered, obs=obs_tot))

        fig = px.line(df_hz, x="booking_horizon_days", y="price_avg",
                      color="op_label", color_discrete_map=color_map, markers=True,
                      title=T["ov_trip_dev"].format(date=sel_date.strftime("%d.%m.%Y")),
                      labels={"booking_horizon_days": T["ov_days_adv"], "price_avg": T["ov_avg"], "op_label": T["ov_op"]},
                      custom_data=["price_min", "observations"])
        fig.update_traces(line_width=2, marker_size=6,
                          hovertemplate="<b>%{fullData.name}</b><br>+%{x} " + T["days_unit"] +
                                        "<br>Avg. %{y:.2f} €<br>Min %{customdata[0]:.2f} €<br>%{customdata[1]} obs.")
        fig.update_xaxes(autorange="reversed")
        fig.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        return

    # ══════════════════════════════════════════════════════════════════
    # MODUS B: STRECKE GESAMT
    # ══════════════════════════════════════════════════════════════════
    days = st.slider(T["ov_time_range"], 7, 90, 30, key="ov_days")

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

    min_op_row = timeline_df.loc[timeline_df["min_price"].idxmin()]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T["ov_lowest_price"], f"{min_price:.2f} €", op_label(min_op_row["operator"]))
    c2.metric(T["ov_avg_price"], f"{avg_price:.2f} €")
    c3.metric(T["ov_trend"], f"{trend:+.1f}%", delta=f"{trend:+.1f}%", delta_color="inverse")
    c4.metric(T["ov_operators"], int(row["n_operators"]))

    timeline_df["op_label"] = timeline_df["operator"].map(op_label)
    color_map = {op_label(o): op_color(o) for o in timeline_df["operator"].unique()}

    fig = px.line(timeline_df, x="col_date", y="min_price", color="op_label", color_discrete_map=color_map,
                  markers=True, title=T["ov_c1"].format(days=days),
                  labels={"col_date": T["ov_date"], "min_price": T["ov_low_lbl"], "op_label": T["ov_op"]})
    fig.update_traces(line_width=2)
    fig.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # ── Preisspanne Min/Avg/Max pro Operator ──
    range_df = load_price_range_by_operator(origin, destination)
    if not range_df.empty:
        fig2 = go.Figure()
        for _, r in range_df.iterrows():
            lbl, col = op_label(r["operator"]), op_color(r["operator"])
            fig2.add_trace(go.Scatter(x=[lbl, lbl], y=[float(r["price_min"]), float(r["price_max"])],
                                       mode="lines", line=dict(color=col, width=4), showlegend=False))
            fig2.add_trace(go.Scatter(x=[lbl], y=[float(r["price_avg"])], mode="markers",
                                       marker=dict(color="#fff", size=10, symbol="diamond", line=dict(color=col, width=2)),
                                       name=lbl))
        fig2.update_layout(title=T["ov_c2"], yaxis_title=T["ov_price"],
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Abfahrtsstunden-Verteilung ──
    hour_df = load_departure_hour_counts(origin, destination)
    if not hour_df.empty:
        hour_df["dep_hour"] = pd.to_numeric(hour_df["dep_hour"]).astype(int)
        hour_df["op_label"] = hour_df["operator"].map(op_label)
        hour_df["hour_label"] = hour_df["dep_hour"].astype(str).str.zfill(2) + ":00"
        color_map2 = {op_label(o): op_color(o) for o in hour_df["operator"].unique()}
        fig3 = px.bar(hour_df, x="hour_label", y="connection_count", color="op_label", color_discrete_map=color_map2,
                      barmode="group", title=T["ov_c3"],
                      labels={"hour_label": T["ov_dep_hour"], "connection_count": T["ov_count"], "op_label": T["ov_op"]})
        fig3.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(T["ov_dep_hour_note"])

    # ── Tarifklassen ──
    fare_df = load_fare_class_avg(origin, destination)
    if not fare_df.empty:
        st.subheader(T["ov_fare_classes"])
        fare_df["op_label"] = fare_df["operator"].map(op_label)
        color_map3 = {op_label(o): op_color(o) for o in fare_df["operator"].unique()}
        fig4 = px.bar(fare_df, x="fare_class", y="avg_price", color="op_label", color_discrete_map=color_map3,
                      barmode="group", title=T["ov_c5"],
                      labels={"fare_class": T["ov_class"], "avg_price": T["ov_avg"], "op_label": T["ov_op"]})
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(T["ov_fare_note"])