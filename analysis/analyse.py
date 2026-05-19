import os
import sys

import pandas as pd

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export.csv")


def load() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        print(f"Datei nicht gefunden: {CSV_PATH}")
        sys.exit(1)
    df = pd.read_csv(CSV_PATH, low_memory=False,
                     parse_dates=["collected_at", "departure_at", "arrival_at"])
    df["price_eur"]            = pd.to_numeric(df["price_eur"], errors="coerce")
    df["booking_horizon_days"] = pd.to_numeric(df["booking_horizon_days"], errors="coerce")
    for col in ["collected_at", "departure_at", "arrival_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert(None)
    return df


def main():
    df = load()

    print(f"\n=== RailWatch — Datenübersicht ===")
    print(f"Records:      {len(df):,}")
    print(f"Operatoren:   {df['operator'].nunique()}")
    print(f"Strecken:     {df['route_id'].nunique()}")
    print(f"Zeitraum:     {df['collected_at'].min().date()} – {df['collected_at'].max().date()}")

    print(f"\n--- Records & Preise je Operator ---")
    grp = (df.groupby("operator")["price_eur"]
           .agg(records="count", avg="mean", min="min", max="max")
           .sort_values("records", ascending=False))
    for op, row in grp.iterrows():
        print(f"  {op:<15}  {int(row['records']):>7,} Records   "
              f"min {row['min']:>7.2f} €   avg {row['avg']:>7.2f} €   max {row['max']:>7.2f} €")

    print(f"\n--- Günstigste 10 Verbindungen (alle Strecken) ---")
    cols = ["operator", "origin_name", "destination_name", "price_eur", "departure_at", "booking_horizon_days"]
    for _, row in df.nsmallest(10, "price_eur")[cols].iterrows():
        dep = str(row["departure_at"])[:10]
        hz  = f"+{int(row['booking_horizon_days'])}T" if pd.notna(row["booking_horizon_days"]) else "   "
        print(f"  {row['operator']:<12}  {row['origin_name']} → {row['destination_name']:<35}  "
              f"{row['price_eur']:>6.2f} €  {dep}  {hz}")

    print(f"\n--- Ø Preis nach Buchungshorizont (alle Strecken) ---")
    hz_grp = (df.dropna(subset=["booking_horizon_days"])
              .groupby("booking_horizon_days")["price_eur"].agg(avg="mean", count="count")
              .sort_index())
    for h, row in hz_grp.iterrows():
        bar = "█" * int(row["avg"] / 5)
        print(f"  +{int(h):>2}T  {row['avg']:>7.2f} €  {bar}")

    print(f"\n--- Top-Strecken nach Datenmenge ---")
    route_grp = (df.groupby(["origin_name", "destination_name"])["price_eur"]
                 .agg(records="count", avg="mean", min="min")
                 .sort_values("records", ascending=False).head(10))
    for (orig, dest), row in route_grp.iterrows():
        print(f"  {orig} → {dest:<35}  {int(row['records']):>6,} Records   "
              f"min {row['min']:>6.2f} €   avg {row['avg']:>6.2f} €")


if __name__ == "__main__":
    main()
