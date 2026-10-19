# dashboard/views/export.py
import io
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from dashboard.config import op_label, route_label
from dashboard.database import (
    load_route_list, load_export_date_range, count_export, load_export,
    ExportFilter, EXPORT_RAW_COLUMNS, COLLECTION_TZ,
)

# Download files are built in memory -> hard caps
RAW_ROW_LIMIT  = 500_000
XLSX_ROW_LIMIT = 200_000
PREVIEW_ROWS   = 100

HORIZONS = [1, 2, 3, 4, 5, 6, 7, 10, 14, 21, 30, 45, 60, 90]
DEFAULT_RAW_COLUMNS = [
    "collected_at", "collection_day", "operator", "route_id", "origin_name", "destination_name",
    "departure_at", "arrival_at", "booking_horizon_days", "train_number", "fare_class",
    "price_eur", "seats_available", "is_direct",
]


def _short(items, fallback="all", max_items=3):
    if not items:
        return fallback
    if len(items) > max_items:
        return f"{len(items)}x"
    return "-".join(str(i) for i in items)


def _file_name(f: ExportFilter, level: str, ext: str) -> str:
    return (f"rdh_{level}_{_short(f.operators)}_{_short(f.route_ids)}"
            f"_{f.col_from:%Y-%m-%d}_{f.col_to:%Y-%m-%d}.{ext}")


def _filter_summary(f: ExportFilter, level: str, n_rows: int, T) -> pd.DataFrame:
    rows = [
        (T["ex_meta_exported"], datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        (T["ex_level"], T[f"ex_level_{level}"]),
        (T["ex_operators"], ", ".join(f.operators) or T["ex_all"]),
        (T["ex_routes"], ", ".join(f.route_ids) or T["ex_all"]),
        (T["ex_col_range"], f"{f.col_from} – {f.col_to} ({COLLECTION_TZ})"),
        (T["ex_horizons"], ", ".join(str(h) for h in f.horizons) or T["ex_all"]),
        (T["ex_direct_only"], str(f.direct_only)),
        (T["ex_dep_range"], f"{f.dep_from} – {f.dep_to}" if f.dep_from else T["ex_all"]),
        (T["ex_meta_rows"], str(n_rows)),
        (T["ex_meta_note_lbl"], T["ex_meta_note"]),
    ]
    return pd.DataFrame(rows, columns=[T["ex_meta_key"], T["ex_meta_value"]])


def _to_csv(df: pd.DataFrame, sep: str) -> bytes:
    # utf-8-sig: Excel opens umlauts / accents correctly
    decimal = "," if sep == ";" else "."
    return df.to_csv(index=False, sep=sep, decimal=decimal).encode("utf-8-sig")


def _to_xlsx(df: pd.DataFrame, meta: pd.DataFrame) -> bytes:
    df = df.copy()
    for col in df.columns:
        # Excel cannot store tz-aware timestamps -> naive UTC (documented in the Info sheet)
        if isinstance(df[col].dtype, pd.DatetimeTZDtype):
            df[col] = df[col].dt.tz_convert("UTC").dt.tz_localize(None)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="data", index=False)
        meta.to_excel(writer, sheet_name="info", index=False)
    return buf.getvalue()


def render_export(T):
    lang = st.session_state.lang
    st.subheader(T["ex_head"])
    st.caption(T["ex_intro"])

    routes_df = load_route_list()
    first_day, last_day = load_export_date_range()
    if routes_df.empty or first_day is None:
        st.info(T["no_data"])
        return

    # route_id -> display label (first origin/destination pair per route_id)
    route_rows = routes_df.dropna(subset=["route_id"]).drop_duplicates("route_id")
    route_labels = {r["route_id"]: route_label(r["origin_name"], r["destination_name"], lang)
                    for _, r in route_rows.iterrows()}
    all_operators = sorted({op for ops in routes_df["operators"] for op in ops})

    # ══════════════════════════════════════════════════════════════════
    # 1. FILTER
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(f"#### 1 · {T['ex_step_filter']}")

        c1, c2 = st.columns(2)
        with c1:
            sel_ops = st.multiselect(T["ex_operators"], all_operators, format_func=op_label,
                                     placeholder=T["ex_all"], key="ex_ops")
        with c2:
            if sel_ops:
                ops_routes = routes_df[routes_df["operators"].apply(lambda o: any(x in sel_ops for x in o))]
                route_options = sorted(set(ops_routes["route_id"].dropna()), key=lambda r: route_labels.get(r, r))
            else:
                route_options = sorted(route_labels, key=lambda r: route_labels[r])
            sel_routes = st.multiselect(T["ex_routes"], route_options,
                                        format_func=lambda r: route_labels.get(r, r),
                                        placeholder=T["ex_all"], key="ex_routes")
            sel_routes = [r for r in sel_routes if r in route_options]

        c3, c4 = st.columns(2)
        with c3:
            col_range = st.date_input(T["ex_col_range"], value=(first_day, last_day),
                                      min_value=first_day, max_value=last_day,
                                      format="DD.MM.YYYY", key="ex_col_range")
        with c4:
            sel_hz = st.multiselect(T["ex_horizons"], HORIZONS, placeholder=T["ex_all"],
                                    format_func=lambda h: f"+{h}", key="ex_hz")

        c5, c6 = st.columns(2)
        with c5:
            direct_only = st.checkbox(T["ex_direct_only"], key="ex_direct")
        with c6:
            use_dep = st.checkbox(T["ex_dep_limit"], key="ex_use_dep")
        dep_range = None
        if use_dep:
            dep_range = st.date_input(T["ex_dep_range"], value=(first_day, last_day),
                                      format="DD.MM.YYYY", key="ex_dep_range")

    # date_input returns a 1-tuple while the user is still picking the end date
    if not isinstance(col_range, (list, tuple)) or len(col_range) != 2:
        st.info(T["ex_pick_range"])
        return
    if use_dep and (not isinstance(dep_range, (list, tuple)) or len(dep_range) != 2):
        st.info(T["ex_pick_range"])
        return

    f = ExportFilter(
        operators=tuple(sel_ops),
        route_ids=tuple(sel_routes),
        col_from=col_range[0], col_to=col_range[1],
        horizons=tuple(sorted(sel_hz)),
        direct_only=direct_only,
        dep_from=dep_range[0] if use_dep else None,
        dep_to=dep_range[1] if use_dep else None,
    )

    # ══════════════════════════════════════════════════════════════════
    # 2. DETAILGRAD & SPALTEN
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(f"#### 2 · {T['ex_step_level']}")
        level = st.radio(T["ex_level"], options=["daily", "raw"], horizontal=True,
                         format_func=lambda l: T[f"ex_level_{l}"], key="ex_level")
        st.caption(T[f"ex_level_{level}_help"])

        columns = ()
        if level == "raw":
            columns = tuple(st.multiselect(T["ex_columns"], list(EXPORT_RAW_COLUMNS),
                                           default=DEFAULT_RAW_COLUMNS, key="ex_cols"))
            if not columns:
                st.info(T["ex_no_columns"])
                return

    # ══════════════════════════════════════════════════════════════════
    # 3. VORSCHAU & DOWNLOAD
    # ══════════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown(f"#### 3 · {T['ex_step_download']}")

        with st.spinner("..."):
            n_rows = count_export(f, level)

        fmt = st.radio(T["ex_format"], options=["csv_comma", "csv_semicolon", "xlsx"], horizontal=True,
                       format_func=lambda x: T[f"ex_fmt_{x}"], key="ex_fmt")

        m1, m2 = st.columns(2)
        m1.metric(T["ex_rows"], f"{n_rows:,}".replace(",", "."))
        m2.metric(T["ex_level"], T[f"ex_level_{level}"])

        if n_rows == 0:
            st.info(T["ex_empty"])
            return
        if level == "raw" and n_rows > RAW_ROW_LIMIT:
            st.warning(T["ex_too_many_raw"].format(limit=f"{RAW_ROW_LIMIT:,}".replace(",", ".")))
            return
        if fmt == "xlsx" and n_rows > XLSX_ROW_LIMIT:
            st.warning(T["ex_too_many_xlsx"].format(limit=f"{XLSX_ROW_LIMIT:,}".replace(",", ".")))
            return

        st.caption(T["ex_preview"].format(n=min(PREVIEW_ROWS, n_rows)))
        st.dataframe(load_export(f, level, columns, limit=PREVIEW_ROWS),
                     use_container_width=True, hide_index=True, height=260)

        # Build the file only on click (keeps reruns cheap); invalidate when the selection changes
        selection_key = (f, level, columns, fmt)
        if st.session_state.get("ex_file", {}).get("key") != selection_key:
            st.session_state.pop("ex_file", None)

        if st.button(T["ex_build"], type="primary", key="ex_build_btn"):
            with st.spinner(T["ex_building"]):
                df = load_export(f, level, columns)
                if fmt == "xlsx":
                    data = _to_xlsx(df, _filter_summary(f, level, len(df), T))
                    mime, ext = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
                else:
                    data = _to_csv(df, ";" if fmt == "csv_semicolon" else ",")
                    mime, ext = "text/csv", "csv"
            st.session_state["ex_file"] = {
                "key": selection_key, "data": data, "mime": mime,
                "name": _file_name(f, level, ext),
            }

        ex_file = st.session_state.get("ex_file")
        if ex_file:
            size_mb = len(ex_file["data"]) / 1_048_576
            st.download_button(f"⬇ {ex_file['name']} ({size_mb:.1f} MB)", data=ex_file["data"],
                               file_name=ex_file["name"], mime=ex_file["mime"], key="ex_download")
