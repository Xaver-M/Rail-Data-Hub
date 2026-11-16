# Rail Data Hub

> Automated collection and analysis of long-distance train ticket prices across European rail operators — empirical foundation for studying yield management and dynamic pricing strategies in passenger rail.

**KIT · Institut für Volkswirtschaftslehre · Teamprojekt SS 2026**

---

## Overview

Rail Data Hub systematically crawls ticket prices from 10 European rail and bus sources across 179 routes, storing all observations in a TimescaleDB time-series database. Since October 2026, flight prices on four corridors are collected as well (Google Flights) for a rail-vs-air comparison. A Streamlit dashboard enables interactive analysis of pricing dynamics, booking horizon effects, cross-operator and cross-mode comparisons, plus a data export.

The routes cover Germany, Italy, France, Spain, Austria, Switzerland, the Netherlands, Belgium, the Czech Republic, Slovakia, Hungary and Poland. Prices are collected at 14 discrete booking horizons (1–90 days before departure) every day at 10:00 UTC.

---

## Operators

| Operator | Country | Type | Source |
|---|---|---|---|
| DB (ParseBot) | 🇩🇪 Germany | Long-distance rail | Parse.bot scraper (replaces `db` on the VM, see limitations) |
| Deutsche Bahn | 🇩🇪 Germany | Long-distance rail | db-vendo-client microservice (blocked on datacenter IPs) |
| Flixtrain | 🇩🇪 Europe | Low-cost rail | Direct API |
| Flixbus | 🇪🇺 Europe | Long-distance bus | Direct API |
| Trenitalia | 🇮🇹 Italy | Long-distance rail | lefrecce.it BFF |
| Italo | 🇮🇹 Italy | High-speed rail | Playwright (headed, under xvfb on the VM) |
| OUIGO España | 🇪🇸 Spain | Low-cost rail | Direct API |
| OUIGO France | 🇫🇷 France | Low-cost rail | Direct API |
| RegioJet | 🇨🇿 Czech Republic | Long-distance rail | Public REST API |
| České dráhy | 🇨🇿 Czech Republic | Long-distance rail | Public REST API |
| Google Flights | ✈️ IT · ES · FR | Flights (intermodal comparison) | Google Flights, 4 corridors |

### Flight corridors

Flights are collected only where they compete with rail on the same route. Their `route_id` matches the rail route, so both can be compared directly.

| Corridor (`route_id`) | Airports (nonstop) |
|---|---|
| `milan-rome` | LIN–FCO |
| `madrid-barcelona` | MAD–BCN |
| `barcelona-madrid` | BCN–MAD |
| `paris-nice` | ORY–NCE, CDG–NCE |

Each flight is stored in two baggage variants via `fare_class` (`economy_nobag`, `economy_cabinbag`). Flights are hidden in all dashboard views except **Rail vs. Air** and the export.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  bwCloud VM (Ubuntu 24)              │
│                                                     │
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │ systemd timer   │───▶│  run_crawlers.py       │  │
│  │ rdh-crawlers    │    │  (crawler registry,    │  │
│  │ daily 10:00 UTC │    │   runs under xvfb-run) │  │
│  └─────────────────┘    └──────────┬─────────────┘  │
│                                    │                 │
│                                    ▼                 │
│  ┌─────────────────────────────────────────────────┐ │
│  │         Docker: TimescaleDB / PostgreSQL         │ │
│  │         rail_data · price_observations           │ │
│  └─────────────────────────────────────────────────┘ │
│                                    │                 │
│  ┌─────────────────┐               │                 │
│  │  Streamlit      │◀──────────────┘                 │
│  │  Dashboard      │  port 8501                      │
│  └─────────────────┘                                 │
└─────────────────────────────────────────────────────┘
```

Which crawlers run is set per machine via `RDH_CRAWLERS` in `.env`; without it, `DEFAULT_VM_CRAWLERS` in `scheduler/run_crawlers.py` applies. Setup of the timer: `deploy/install_systemd.sh`.

```bash
python scheduler/run_crawlers.py                      # all enabled crawlers
python scheduler/run_crawlers.py --only trenitalia    # single crawler
python scheduler/run_crawlers.py --list               # show registry
```

---

## Data Schema

All price observations are stored in the `price_observations` hypertable (TimescaleDB):

| Column | Type | Description |
|---|---|---|
| `id` | BIGSERIAL | Primary key |
| `operator` | TEXT | Operator identifier (e.g. `db`, `trenitalia`, `ita_airways`) |
| `origin_id` | TEXT | Origin station ID (IATA code for flights) |
| `origin_name` | TEXT | Origin station name |
| `destination_id` | TEXT | Destination station ID (IATA code for flights) |
| `destination_name` | TEXT | Destination station name |
| `route_id` | TEXT | Route identifier |
| `departure_at` | TIMESTAMPTZ | Scheduled departure time |
| `arrival_at` | TIMESTAMPTZ | Scheduled arrival time |
| `price_eur` | NUMERIC | Cheapest available fare in EUR |
| `fare_class` | TEXT | Fare class (operator-specific, not comparable across operators; baggage variant for flights) |
| `booking_horizon_days` | INTEGER | Days before departure at time of collection |
| `train_number` | TEXT | Train/service/flight identifier |
| `seats_available` | INTEGER | Available seats (where provided) |
| `is_direct` | BOOLEAN | Direct connection (no transfer) |
| `collected_at` | TIMESTAMPTZ | Timestamp of data collection (UTC) |

**Unique constraint:** `(operator, origin_id, destination_id, departure_at, fare_class, collected_at)` — duplicate crawl attempts are silently ignored via `ON CONFLICT DO NOTHING`.

### Booking Horizons

Prices are collected at 14 fixed points before departure:

```
90 · 60 · 45 · 30 · 21 · 14 · 10 · 7 · 6 · 5 · 4 · 3 · 2 · 1 days
```

`db_parsebot` uses a reduced set (1, 2, 3, 7, 14, 21) to stay within the Parse.bot credit budget.

### Price Basis

All analyses use `MIN(price_eur)` per route, horizon and collection day — i.e. the cheapest available fare for 1 adult, 2nd class / economy, single journey, no railcards or extras.

`fare_class` is operator-specific and not directly comparable across operators. Cross-operator analyses always use `price_eur` directly.

### Distances

`config/route_distances.csv` holds one distance per route for the €/km figures:

| Column | Description |
|---|---|
| `haversine_km` | Straight-line distance between the stations (from `config/geocode_stations.py`) |
| `rail_km` | Rail network distance between the two cities (141 of 179 routes) |
| `distance_source` | `rail` or `haversine` — which distance the dashboard uses |

Rail distances are missing for all routes to/from Prague, Munich–Budapest, Berlin–Binz, Paris–Hendaye and Paris–Bourg-Saint-Maurice; there the dashboard falls back to the straight line and flags it. Re-running `geocode_stations.py` keeps `rail_km`.

---

## Repository Structure

```
Rail-Data-Hub/
├── config/
│   ├── routes.py              # Stations, routes, booking horizons
│   ├── flight_routes.py       # Flight corridors for the rail-vs-air comparison
│   ├── route_distances.csv    # Rail + straight-line distances per route
│   ├── geocode_stations.py    # Geocodes stations, writes straight-line distances
│   └── station_coordinates.py # Generated station coordinates
├── crawlers/
│   ├── base/
│   │   └── base_crawler.py    # BaseCrawler class (save, dedup, logging)
│   ├── db/
│   │   ├── db_crawler.py      # Deutsche Bahn crawler
│   │   └── microservice/      # Node.js db-vendo-client wrapper
│   ├── db_parsebot/           # DB via Parse.bot API
│   ├── trenitalia/            # Trenitalia crawler
│   ├── italo/                 # Italo crawler (Playwright)
│   ├── flixtrain/             # Flixtrain crawler
│   ├── flixbus/               # Flixbus crawler
│   ├── ouigo_es/              # OUIGO España crawler
│   ├── ouigo_fr/              # OUIGO France crawler
│   ├── regiojet/              # RegioJet crawler
│   ├── ceske_drahy/           # České dráhy crawler
│   └── google_flights/        # Google Flights crawler
├── scheduler/
│   ├── run_crawlers.py        # Crawler registry, run by the systemd timer
│   └── start_crawlers.py      # APScheduler variant (Docker scheduler service)
├── deploy/
│   └── install_systemd.sh     # Installs rdh-crawlers.service + .timer on the VM
├── database/
│   ├── timescaledb/           # Initial schema
│   └── migrations/            # Schema migrations
├── dashboard/
│   ├── app.py                 # Streamlit entry point
│   ├── config.py              # Translations (EN/DE), color maps, helpers
│   ├── database.py            # All DB queries + offline CSV fallback
│   └── views/
│       ├── landing.py         # Landing page
│       ├── overview.py        # Price timeline view
│       ├── individual_train.py# Single train price history
│       ├── booking_horizon.py # Horizon effect analysis
│       ├── time_of_day.py     # Departure time analysis
│       ├── operator_comp.py   # Cross-operator comparison
│       ├── normalized_prices.py # €/km and €/h comparison
│       ├── intermodal.py      # Rail vs. air
│       ├── export.py          # Data export (password protected)
│       └── crawler_status.py  # System health view
├── logs/                      # Crawler and scheduler logs (30-day rotation)
├── analysis/                  # Analysis scripts
└── docs/                      # Dashboard manual, specification
```

---

## Dashboard

The dashboard runs on the project VM on port 8501 (address on request) or at `http://localhost:8501` (local). A user manual is in [`docs/handbook/dashboard_manual.md`](docs/handbook/dashboard_manual.md).

### Analysis Modules

| Tab | Description |
|---|---|
| **Overview** | Price timeline for a route — MIN/AVG/MAX per operator, selectable time range |
| **Individual Train** | Price history of a specific train from 90 days out to departure |
| **Booking Horizon** | How does price change with lead time? Curves for all 14 horizons |
| **Time of Day** | Are early or late departures systematically cheaper? Heatmap by hour and weekday |
| **Operator Comparison** | Direct price comparison across operators at a selectable horizon |
| **€/km & €/h** | Normalised prices based on rail distance (straight line as flagged fallback) |
| **Rail vs. Air** | Rail/bus vs. flight on four corridors: which is cheaper (by day and horizon), door-to-door time and cost incl. value of time, price development, data basis |
| **Data Export** | Filtered download as CSV or Excel, protected by a shared password |
| **Crawler Status** | System health: last crawl times, record counts, 7-day availability |

### Local Development

Locally, the dashboard reads the database connection from `.streamlit/secrets.toml` (`[connections.postgresql]`), usually via an SSH tunnel to the VM (`ssh -L 5432:localhost:5432 <vm> -N`). The export password is set there as `export_password`.

### Offline Mode

If no database connection is available, the dashboard falls back to `data/snapshot.csv` (not part of the repository — place a `price_observations` export there). A warning banner is shown in the sidebar. The analysis modules work in offline mode via Pandas equivalents of the DB queries; Rail vs. Air and the export need the database.

---

## Known Limitations

### Deutsche Bahn API Block
The DB `dbnav`/vendo API (`app.services-bahn.de`) categorically blocks datacenter IPs with HTTP 403/500 at edge level (~40ms response time). This is documented in [db-vendo-client Issue #78](https://github.com/public-transport/db-vendo-client/issues/78), effective since ~18.05.2026. The bwCloud VM IP has been intermittently blocked since 06.07.2026 (`OPS_BLOCKED` error code). The `db` crawler is therefore disabled on the VM; DB prices are collected via `db_parsebot` (Parse.bot scraper).

### DB Morning Window
Both `db` and `db_parsebot` only cover a morning departure window (fixed `departure=10:00` parameter, resulting in connections roughly 08:00–13:15 departure time). This is a known limitation — the time series was not modified after collection started to avoid breaking continuity.

### Italo WAF Block
Italo's website is protected by Akamai WAF, which blocks headless Playwright browsers (`ERR_HTTP2_PROTOCOL_ERROR`). The crawler therefore runs a headed browser; on the VM it runs under `xvfb-run` as part of the daily systemd run.

### db_parsebot Instability
Parse.bot's API has an elevated error rate (~50% HTTP 503 responses). Records per run vary significantly (100–5000+ depending on API availability). Documented as a known data quality limitation.

### fare_class Heterogeneity
The `fare_class` column is populated differently across operators (Italo: productClass codes, Trenitalia: offer names, RegioJet: vehicleStandardKey, flights: baggage variant, others: fixed strings or NULL). It is not used for cross-operator analysis — `price_eur` (cheapest available fare) is the reliable field.

### Flixtrain Thin Timetable
Flixtrain operates only 3 daily departures on most routes, resulting in lower absolute record counts compared to other operators. This reflects the actual timetable, not a crawler limitation.

### Distances
Rail distances are city-to-city, not station-to-station (e.g. Paris Est and "Paris toutes gares" share one value). 38 routes still use the straight-line distance, which understates the rail distance by ~26% on average.

## Links

- **Institution:** [KIT Institut für Volkswirtschaftslehre](https://www.wiwi.kit.edu)
- **DB API Issue:** [db-vendo-client #78](https://github.com/public-transport/db-vendo-client/issues/78)
