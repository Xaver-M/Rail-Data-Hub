# dashboard/views/individual_train.py
import streamlit as st
import plotly.express as px
import pandas as pd

from dashboard.config import op_color, op_label, price_basis_toggle, station_name
from dashboard.database import load_train_numbers, load_single_train_data


def render_individual_train(route, T):
    lang = st.session_state.lang
    st.subheader(T["tr_head"].format(orig=station_name(route["origin_name"], lang),
                                      dest=station_name(route["destination_name"], lang)))

    origin, destination = route["origin_name"], route["destination_name"]
    operators = route["operators"]

    sel_op = st.selectbox(T["tr_op"], operators, format_func=op_label, key="train_op")

    trains_df = load_train_numbers(origin, destination, sel_op)
    if trains_df.empty:
        st.info(T["tr_no_data"])
        return

    # ── Verbindungstyp-Filter für Dropdown ──
    col_basis, col_direct = st.columns(2)
    with col_direct:
        direct_choice = st.radio(
            T["direct_filter"], options=["all", "direct", "transfer"],
            format_func=lambda m: {"all": T["direct_all"], "direct": T["direct_only"],
                                   "transfer": T["direct_transfer"]}[m],
            horizontal=True, key="tr_direct"
        )

    all_trains = trains_df["train_number"].tolist()
    if direct_choice == "direct":
        train_list = [t for t in all_trains if "+" not in str(t)]
    elif direct_choice == "transfer":
        train_list = [t for t in all_trains if "+" in str(t)]
    else:
        train_list = all_trains

    if not train_list:
        st.info(T["ov_no_data"])
        return

    if len(all_trains) > 60:
        st.caption(T["tr_heterogen"].format(n=len(all_trains), op=op_label(sel_op)))

    with col_basis:
        sel_train = st.selectbox(T["tr_sel"], train_list, key="train_name")
    if not sel_train:
        return

    df_single = load_single_train_data(origin, destination, sel_op, sel_train)
    if df_single.empty:
        st.info(T["tr_no_data"])
        return

    # ── Preisbasis-Toggle ──
    basis = price_basis_toggle("tr_basis", T)
    y_lbl = {"min": T["price_min"], "avg": T["price_avg"], "max": T["price_max_label"]}[basis]

    # ── Aktuelle Werte ──
    latest     = df_single.iloc[0]
    dep_str    = pd.to_datetime(latest["departure_at"]).strftime("%H:%M")
    price_now  = float(latest["price_eur"])
    price_min  = float(df_single["price_eur"].min())
    price_max  = float(df_single["price_eur"].max())

    cut7       = df_single["collected_at"].max() - pd.Timedelta(days=8)
    older      = df_single[df_single["collected_at"] <= cut7]
    price_7d_ago = float(older.iloc[0]["price_eur"]) if not older.empty else None
    change_7d  = ((price_now - price_7d_ago) / price_7d_ago * 100) if price_7d_ago else None

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(T["tr_cur"], f"{price_now:.2f} €",
              help=T["tr_fare"].format(fare=latest.get("fare_class") or "—"))
    m2.metric(T["tr_lohi"], f"{price_min:.2f} € / {price_max:.2f} €")
    m3.metric(T["tr_7d"], f"{change_7d:+.1f}%" if change_7d is not None else "—",
              delta=f"{change_7d:+.1f}%" if change_7d is not None else None, delta_color="inverse")
    seats = latest.get("seats_available")
    m4.metric(T["tr_seats"], str(int(seats)) if pd.notna(seats) else "—")
    st.divider()

    # ── Preisverlauf über Zeit ──
    df_single["col_date"] = df_single["collected_at"].dt.date
    df_hist = (df_single.groupby("col_date")
               .agg(price_min=("price_eur", "min"),
                    price_avg=("price_eur", "mean"),
                    price_max=("price_eur", "max"))
               .reset_index().sort_values("col_date"))

    if not df_hist.empty:
        y_col_hist = {"min": "price_min", "avg": "price_avg", "max": "price_max"}[basis]
        avg_l = float(df_hist["price_avg"].mean())
        fig = px.line(df_hist, x="col_date", y=y_col_hist,
                      title=f"{T['tr_dev'].format(train=sel_train, dep=dep_str)} ({y_lbl})",
                      labels={"col_date": T["ov_date"], y_col_hist: y_lbl},
                      color_discrete_sequence=[op_color(sel_op)],
                      custom_data=["price_min", "price_avg", "price_max"])
        fig.update_traces(line_width=2, fill="tozeroy",
                          hovertemplate="%{x}<br>"
                                        "Min %{customdata[0]:.2f} €<br>"
                                        "Avg %{customdata[1]:.2f} €<br>"
                                        "Max %{customdata[2]:.2f} €")
        fig.add_hline(y=avg_l, line_dash="dot", line_color="#888",
                      annotation_text=f"Avg. {avg_l:.2f} €")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(T["tr_no_hist"])

    # ── Preis nach Buchungshorizont ──
    df_hz = (df_single.dropna(subset=["booking_horizon_days"])
             .groupby("booking_horizon_days")
             .agg(price_avg=("price_eur", "mean"),
                  price_min=("price_eur", "min"),
                  price_max=("price_eur", "max"),
                  observations=("price_eur", "count"))
             .reset_index().sort_values("booking_horizon_days"))

    if not df_hz.empty:
        y_col_hz = {"min": "price_min", "avg": "price_avg", "max": "price_max"}[basis]
        tp = float(df_hz[y_col_hz].min())
        th = int(df_hz.loc[df_hz[y_col_hz].idxmin(), "booking_horizon_days"])
        df_hz["surcharge_pct"] = ((df_hz[y_col_hz].astype(float) - tp) / tp * 100).round(1)
        df_hz["label"] = "+" + df_hz["booking_horizon_days"].astype(int).astype(str) + "d"

        fig2 = px.bar(df_hz, x="label", y="surcharge_pct", color="surcharge_pct",
                      color_continuous_scale=["#a8e44a", "#ffb547", "#ff5f5f"],
                      range_color=[0, df_hz["surcharge_pct"].max() if df_hz["surcharge_pct"].max() > 0 else 1],
                      title=T["tr_sur_title"].format(train=sel_train, price=tp, horizon=th),
                      labels={"label": T["tr_hz_lbl"], "surcharge_pct": T["tr_sur_lbl"]},
                      custom_data=["observations", "price_min", "price_avg", "price_max"])
        fig2.update_traces(hovertemplate="<b>%{x}</b><br>+%{y:.1f}%<br>"
                                         "Min %{customdata[1]:.2f} €"
                                         "<br>Avg %{customdata[2]:.2f} €"
                                         "<br>Max %{customdata[3]:.2f} €"
                                         "<br>%{customdata[0]} obs.")
        fig2.update_coloraxes(showscale=False)
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.line(df_hz, x="label", y=y_col_hz, markers=True,
                       title=f"{T['tr_abs'].format(train=sel_train)} ({y_lbl})",
                       labels={"label": T["tr_hz_lbl"], y_col_hz: y_lbl},
                       color_discrete_sequence=[op_color(sel_op)],
                       custom_data=["surcharge_pct", "observations", "price_min", "price_avg", "price_max"])
        fig3.update_traces(line_width=2, marker_size=7, fill="tozeroy",
                           hovertemplate="<b>%{x}</b><br>"
                                         f"{y_lbl}: " + "%{y:.2f} €<br>"
                                         "+%{customdata[0]:.1f}%<br>"
                                         "Min %{customdata[2]:.2f} €<br>"
                                         "Avg %{customdata[3]:.2f} €<br>"
                                         "Max %{customdata[4]:.2f} €<br>"
                                         "%{customdata[1]} obs.")
        fig3.add_hline(y=tp, line_dash="dot", line_color="#3B6D11",
                       annotation_text=T["tr_low_line"].format(price=tp))
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)

        best  = df_hz.loc[df_hz[y_col_hz].idxmin()]
        worst = df_hz.loc[df_hz[y_col_hz].idxmax()]
        st.success(T["tr_rec"].format(
            days=int(best["booking_horizon_days"]), price=float(best[y_col_hz]),
            obs=int(best["observations"]), worst=int(worst["booking_horizon_days"]),
            pct=float(worst["surcharge_pct"])))
    else:
        st.info(T["tr_no_hz"])

    # ── Sitzplatz vs Preis ──
    df_seats = df_single[df_single["seats_available"].notna()]
    if not df_seats.empty:
        st.divider()
        fig4 = px.scatter(df_seats, x="seats_available", y="price_eur",
                          labels={"seats_available": T["tr_seats"], "price_eur": T["ov_price"]},
                          color_discrete_sequence=[op_color(sel_op)])
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)