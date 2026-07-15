# dashboard/views/operator_comp.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.config import op_color, op_label, station_name, SEATS_OPERATORS, DB_BAHNCARD_OPERATORS
from dashboard.database import (
    load_all_route_pairs, load_route_horizon_curve, load_route_summary,
    load_operator_comparison_at_horizon, load_seats_by_horizon, load_booking_horizon,
)


def _hex_to_rgba(hex_color: str, alpha: float = 0.18) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _translate_label(label, lang):
    parts = label.split(" → ")
    if len(parts) == 2:
        return f"{station_name(parts[0], lang)} → {station_name(parts[1], lang)}"
    return label


def render_operator_comparison(route, T):
    st.subheader(T["op_head"])

    lang = st.session_state.lang
    origin, destination = route["origin_name"], route["destination_name"]
    orig_lbl = station_name(origin, lang)
    dest_lbl = station_name(destination, lang)
    route_lbl = f"{orig_lbl} → {dest_lbl}"

    # ══════════════════════════════════════════════════════════════════
    # BLOCK 1: STRECKENVERGLEICH (Multi-Route)
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(T["op_route_head"])
        all_routes = load_all_route_pairs()
        all_labels = all_routes["label"].tolist()

        default_label = route["label"] if route["label"] in all_labels else (all_labels[0] if all_labels else None)
        sel_rts = st.multiselect(T["op_routes_lbl"], options=all_labels,
                                 default=[default_label] if default_label else [], key="route_compare",
                                 format_func=lambda l: _translate_label(l, lang))

        if len(sel_rts) >= 2:
            frames, ffreq, summary = [], [], []
            for rl in sel_rts:
                rr = all_routes[all_routes["label"] == rl].iloc[0]
                disp_label = _translate_label(rl, lang)
                curve = load_route_horizon_curve(rr["origin_name"], rr["destination_name"])
                if curve.empty:
                    continue
                curve = curve.copy()
                curve["booking_horizon_days"] = pd.to_numeric(curve["booking_horizon_days"]).astype(int)
                curve["price_avg"] = pd.to_numeric(curve["price_avg"])
                curve["price_min"] = pd.to_numeric(curve["price_min"])
                curve["observations"] = pd.to_numeric(curve["observations"])
                curve["route"] = disp_label
                frames.append(curve[["route", "booking_horizon_days", "price_avg", "price_min"]])
                ffreq.append(curve[["route", "booking_horizon_days", "observations"]])

                summ = load_route_summary(rr["origin_name"], rr["destination_name"])
                if not summ.empty:
                    r0 = summ.iloc[0]
                    summary.append({
                        "route": disp_label,
                        "low": float(r0["price_min"]) if pd.notna(r0["price_min"]) else 0.0,
                        "avg": float(r0["price_avg"]) if pd.notna(r0["price_avg"]) else 0.0,
                        "ops": int(r0["n_operators"]) if pd.notna(r0["n_operators"]) else 0,
                        "pts": int(r0["observations"]) if pd.notna(r0["observations"]) else 0,
                        "cheapest_op": r0["cheapest_operator"] if pd.notna(r0["cheapest_operator"]) else None,
                    })

            if summary:
                cheapest_rt = min(summary, key=lambda x: x["low"])
                for s in summary:
                    best = s["route"] == cheapest_rt["route"]
                    border = "2px solid #a8e44a" if best else "1px solid #333"
                    badge = T["op_badge"] if best else ""
                    op_name = op_label(s["cheapest_op"]) if s["cheapest_op"] else "—"
                    st.markdown(
                        f'<div style="border:{border};border-radius:8px;padding:10px 12px;background:#111;margin-bottom:8px;">'
                        f'<div style="font-size:11px;color:#888;margin-bottom:2px;">{s["route"]}{badge}</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#fff;">{s["low"]:.2f} € <span style="font-size:12px;font-weight:500;color:{op_color(s["cheapest_op"])};">{op_name}</span></div>'
                        f'<div style="font-size:11px;color:#aaa;">{T["op_avg"]} {s["avg"]:.2f} € · {s["ops"]} op. · {s["pts"]:,} {T["op_pts"]}</div>'
                        f'</div>', unsafe_allow_html=True)

            if frames:
                df_rhz = pd.concat(frames, ignore_index=True)
                route_palette = px.colors.qualitative.Plotly
                route_color_map = {r: route_palette[i % len(route_palette)]
                                   for i, r in enumerate(df_rhz["route"].unique())}

                bt1, bt2, bt3 = st.columns(3)
                show_normal = bt1.toggle(T["bh_bc_normal"], value=True, key="op_route_fare_normal")
                show_bc50 = bt2.toggle(T["bh_bc50"], value=False, key="op_route_fare_bc50")
                show_bc25 = bt3.toggle(T["bh_bc25"], value=False, key="op_route_fare_bc25")
                if show_bc50 or show_bc25:
                    st.caption(T["bh_bc_note"])

                plot_frames = []
                if show_normal:
                    base = df_rhz.copy()
                    base["route_grp"] = base["route"]
                    base["fare_type"] = T["bh_bc_normal"]
                    base["series"] = base["route"]
                    plot_frames.append(base[["route_grp", "fare_type", "series", "booking_horizon_days", "price_avg"]])

                if show_bc50 or show_bc25:
                    for rl in sel_rts:
                        rr = all_routes[all_routes["label"] == rl].iloc[0]
                        disp_label = _translate_label(rl, lang)
                        bh_op = load_booking_horizon(rr["origin_name"], rr["destination_name"])
                        if bh_op.empty:
                            continue
                        bh_db = bh_op[bh_op["operator"].isin(DB_BAHNCARD_OPERATORS)].copy()
                        if bh_db.empty:
                            continue
                        bh_db["booking_horizon_days"] = pd.to_numeric(bh_db["booking_horizon_days"]).astype(int)
                        bh_db["price_avg"] = pd.to_numeric(bh_db["price_avg"])
                        for op_id in bh_db["operator"].unique():
                            op_df = bh_db[bh_db["operator"] == op_id]
                            if show_bc50:
                                bc50 = op_df.copy()
                                bc50["price_avg"] = bc50["price_avg"] * 0.5
                                bc50["route_grp"] = disp_label
                                bc50["fare_type"] = T["bh_bc50"]
                                bc50["series"] = f"{disp_label} · {op_label(op_id)} {T['bh_bc50']}"
                                plot_frames.append(bc50[["route_grp", "fare_type", "series", "booking_horizon_days", "price_avg"]])
                            if show_bc25:
                                bc25 = op_df.copy()
                                bc25["price_avg"] = bc25["price_avg"] * 0.75
                                bc25["route_grp"] = disp_label
                                bc25["fare_type"] = T["bh_bc25"]
                                bc25["series"] = f"{disp_label} · {op_label(op_id)} {T['bh_bc25']}"
                                plot_frames.append(bc25[["route_grp", "fare_type", "series", "booking_horizon_days", "price_avg"]])

                if not plot_frames:
                    st.info(T["bh_bc_none"])
                else:
                    df_plot = pd.concat(plot_frames, ignore_index=True)
                    fare_dash_map = {T["bh_bc_normal"]: "solid", T["bh_bc50"]: "dot", T["bh_bc25"]: "dashdot"}
                    multi_fare = (show_bc50 or show_bc25)
                    fig = px.line(df_plot, x="booking_horizon_days", y="price_avg", color="route_grp",
                                  line_dash="fare_type" if multi_fare else None,
                                  line_dash_map=fare_dash_map if multi_fare else None,
                                  line_group="series", color_discrete_map=route_color_map,
                                  markers=True, hover_name="series",
                                  title=T["op_hz_t"],
                                  labels={"booking_horizon_days": T["ov_days_adv"], "price_avg": T["bh_avg"], "route_grp": T["op_routes_lbl"]})
                    fig.update_traces(line_width=2, marker_size=5)
                    fig.update_xaxes(autorange="reversed")
                    fig.update_yaxes(rangemode="tozero")
                    fig.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)

                df_rmin = df_rhz.groupby("route").agg(low=("price_min", "min")).reset_index().sort_values("low")
                fig2 = px.bar(df_rmin, x="route", y="low", color="route", color_discrete_map=route_color_map,
                              title=T["op_low_rt"], labels={"low": T["op_low"]}, text="low")
                fig2.update_traces(texttemplate="%{text:.2f} €", textposition="outside")
                fig2.update_yaxes(rangemode="tozero")
                fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

            if ffreq:
                df_frc = pd.concat(ffreq, ignore_index=True)
                fig3 = px.bar(df_frc, x="booking_horizon_days", y="observations", color="route", barmode="group",
                              color_discrete_map=route_color_map,
                              title=T["op_conn"], labels={"booking_horizon_days": T["ov_days_adv"], "observations": T["ov_count"]})
                fig3.update_xaxes(autorange="reversed")
                fig3.update_yaxes(rangemode="tozero")
                fig3.update_layout(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info(T["op_sel2"] if sel_rts else T["op_no_rt"])

    st.divider()

    # ══════════════════════════════════════════════════════════════════
    # BLOCK 2: ANBIETERVERGLEICH bei wählbarem Horizont
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(T["op_comp"].format(orig=orig_lbl, dest=dest_lbl))
        hz_val = st.select_slider(T["op_hz"], options=[1, 2, 3, 4, 5, 6, 7, 10, 14, 21, 30, 45, 60, 90],
                                  value=14, key="cp_h")
        df_cp = load_operator_comparison_at_horizon(origin, destination, hz_val)

        if df_cp.empty:
            st.info(T["op_no_hz"].format(days=hz_val))
        else:
            df_cp = df_cp.copy()
            if st.session_state.get("active_operators"):
                df_cp = df_cp[df_cp["operator"].isin(st.session_state.active_operators)]
            if df_cp.empty:
                st.info(T["op_no_hz"].format(days=hz_val))

            for col in ["price_min", "price_avg", "price_max", "seats_avg"]:
                df_cp[col] = pd.to_numeric(df_cp[col], errors="coerce")
            df_cp["observations"] = pd.to_numeric(df_cp["observations"])
            df_cp = df_cp.sort_values("price_min").reset_index(drop=True)
            df_cp["op_label"] = df_cp["operator"].map(op_label)

            min_p = float(df_cp["price_min"].min())
            max_p = float(df_cp["price_min"].max())
            savings = (max_p - min_p) / max_p * 100 if max_p > 0 else 0
            cheap, most_e = df_cp.iloc[0], df_cp.iloc[-1]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(T["op_cheap"], op_label(cheap["operator"]), f"{float(cheap['price_min']):.2f} €")
            c2.metric(T["op_exp"], op_label(most_e["operator"]), f"{float(most_e['price_min']):.2f} €")
            c3.metric(T["op_sav"], f"{savings:.0f}%", help=T["op_sav_help"])
            c4.metric(T["op_hz_m"], f"+{hz_val}d")

            op_color_map = {o: op_color(o) for o in df_cp["operator"].unique()}

            cl, cr = st.columns(2)
            with cl:
                fig = go.Figure()
                for _, r in df_cp.iterrows():
                    c = op_color_map[r["operator"]]
                    fig.add_trace(go.Bar(name=r["op_label"], x=["Min", "Avg", "Max"],
                                         y=[float(r["price_min"]), float(r["price_avg"]), float(r["price_max"])],
                                         marker_color=_hex_to_rgba(c, 0.8),
                                         marker_line_color=c, marker_line_width=1))
                fig.update_yaxes(rangemode="tozero")
                fig.update_layout(barmode="group", yaxis_title=T["ov_price"],
                                  title=f"{T['op_mam'].format(days=hz_val)} — {route_lbl}",
                                  margin=dict(t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
            with cr:
                df_cp["diff_pct"] = ((df_cp["price_min"] - min_p) / min_p * 100).round(4)
                label_color_map = {r["op_label"]: op_color_map[r["operator"]] for _, r in df_cp.iterrows()}
                fig2 = px.bar(df_cp, x="op_label", y="diff_pct", color="op_label",
                              color_discrete_map=label_color_map,
                              title=f"{T['op_extra'].format(op=op_label(cheap['operator']))} — {route_lbl}",
                              labels={"op_label": T["ov_op"], "diff_pct": T["op_pct"]}, text="diff_pct")
                fig2.update_traces(texttemplate="+%{text:.1f}%", textposition="outside")
                fig2.update_yaxes(rangemode="tozero")
                fig2.update_layout(showlegend=False, margin=dict(t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

            if len(df_cp) >= 2:
                st.markdown(T["op_prof"])
                rows = []
                min_price_overall = float(df_cp["price_min"].min())
                for _, r in df_cp.iterrows():
                    spread = float(r["price_max"]) - float(r["price_min"])
                    price_flag = " ✓" if float(r["price_min"]) == min_price_overall else ""
                    rows.append({
                        T["ov_op"]:           r["op_label"],
                        T["op_tbl_min"]:      f"{float(r['price_min']):.2f} €{price_flag}",
                        T["op_tbl_avg"]:      f"{float(r['price_avg']):.2f} €",
                        T["op_tbl_max"]:      f"{float(r['price_max']):.2f} €",
                        T["op_tbl_spread"]:   f"{spread:.2f} €",
                        T["op_tbl_seats"]:    f"{float(r['seats_avg']):.0f}" if pd.notna(r["seats_avg"]) else "–",
                        T["op_tbl_obs"]:      f"{int(r['observations']):,}",
                    })
                st.dataframe(
                    pd.DataFrame(rows).set_index(T["ov_op"]),
                    use_container_width=True,
                )

            df_sc = df_cp[df_cp["seats_avg"].notna() & df_cp["operator"].isin(SEATS_OPERATORS)]
            if not df_sc.empty:
                color_map = {op_label(o): op_color(o) for o in df_cp["operator"].unique()}
                fig3 = px.scatter(df_sc, x="price_min", y="seats_avg", color="op_label", color_discrete_map=color_map,
                                  size=[20] * len(df_sc), text="op_label",
                                  title=f"{T['op_scatter']} — {route_lbl}",
                                  labels={"price_min": T["op_low"], "seats_avg": T["op_seats"], "op_label": T["ov_op"]},
                                  custom_data=["observations"])
                fig3.update_traces(textposition="top center",
                                   hovertemplate="<b>%{text}</b><br>%{x:.2f} €<br>%{y:.0f} seats<br>%{customdata[0]} obs.")
                fig3.update_xaxes(rangemode="tozero")
                fig3.update_yaxes(rangemode="tozero")
                fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig3, use_container_width=True)

            df_sh2 = load_seats_by_horizon(origin, destination)
            df_sh2 = df_sh2[df_sh2["operator"].isin(SEATS_OPERATORS)] if not df_sh2.empty else df_sh2
            if st.session_state.get("active_operators") and not df_sh2.empty:
                df_sh2 = df_sh2[df_sh2["operator"].isin(st.session_state.active_operators)]
            if not df_sh2.empty:
                df_sh2 = df_sh2.copy()
                df_sh2["booking_horizon_days"] = pd.to_numeric(df_sh2["booking_horizon_days"]).astype(int)
                df_sh2["seats_avg"] = pd.to_numeric(df_sh2["seats_avg"])
                df_sh2 = df_sh2.sort_values(["operator", "booking_horizon_days"], ascending=[True, False])
                df_sh2["op_label"] = df_sh2["operator"].map(op_label)
                color_map2 = {op_label(o): op_color(o) for o in df_sh2["operator"].unique()}
                fig4 = px.line(df_sh2, x="booking_horizon_days", y="seats_avg", color="op_label",
                               color_discrete_map=color_map2, markers=True,
                               title=f"{T['op_seats_hz']} — {route_lbl}",
                               labels={"booking_horizon_days": T["ov_days_adv"], "seats_avg": T["op_seats"], "op_label": T["ov_op"]})
                fig4.update_xaxes(autorange="reversed")
                fig4.update_yaxes(rangemode="tozero")
                fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig4, use_container_width=True)