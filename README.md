# Rail Data Hub

> Automated collection and analysis of long-distance train ticket prices across European rail operators — empirical foundation for studying yield management and dynamic pricing strategies in passenger rail.

**KIT · Institut für Volkswirtschaftslehre · Teamprojekt SS 2026**

---

## Overview

Rail Data Hub systematically crawls ticket prices from 10 European rail operators across 144 routes, storing all observations in a TimescaleDB time-series database. A Streamlit dashboard enables interactive analysis of pricing dynamics, booking horizon effects, and cross-operator comparisons.

The project covers operators in Germany, Italy, France, Spain, Czech Republic, Austria, Slovakia and Hungary, collecting prices at 14 discrete booking horizons (1–90 days before departure) every day at 10:00 UTC.

---

## Operators

| Operator | Country | Type | Source |
|---|---|---|---|
| Deutsche Bahn | 🇩🇪 Germany | Long-distance rail | db-vendo-client microservice |
| DB (ParseBot) | 🇩🇪 Germany | Long-distance rail (backup) | Parse.bot scraper |
| Flixtrain | 🇩🇪 Europe | Low-cost rail | Direct API |
| Flixbus | 🇪🇺 Europe | Long-distance bus | Direct API |
| Trenitalia | 🇮🇹 Italy | Long-distance rail | lefrecce.it BFF |
| Italo | 🇮🇹 Italy | High-speed rail | Playwright (local only) |
| OUIGO España | 🇪🇸 Spain | Low-cost rail | Direct API |
| OUIGO France | 🇫🇷 France | Low-cost rail | Direct API |
| RegioJet | 🇨🇿 Czech Republic | Long-distance rail | Public REST API |
| České dráhy | 🇨🇿 Czech Republic | Long-distance rail | Public REST API |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   bwCloud VM (Ubuntu 24)             │
│                                                     │
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │  APScheduler    │───▶│  run_crawlers.py       │  │
│  │  start_crawlers │    │  (all crawlers except  │  │
│  │  daily 10:00UTC │    │   Italo, db_parsebot)  │  │
│  └─────────────────┘    └──────────┬─────────────┘  │
│                                    │                 │
│  ┌─────────────────┐               │                 │
│  │  Node.js        │◀──────────────┤                 │
│  │  db-vendo-client│  DBCrawler    │                 │
│  │  :3123          │               │                 │
│  └─────────────────┘               │                 │
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

┌─────────────────────────────┐
│   Local Machine (Windows)   │
│                             │
│  Italo crawler (Playwright) │
│  db_parsebot crawler        │
│  → manual CSV sync to VM    │
└─────────────────────────────┘
```

---

## Data Schema

All price observations are stored in the `price_observations` hypertable (TimescaleDB):

| Column | Type | Description |
|---|---|---|
| `id` | BIGSERIAL | Primary key |
| `operator` | TEXT | Operator identifier (e.g. `db`, `trenitalia`) |
| `origin_id` | TEXT | Origin station ID |
| `origin_name` | TEXT | Origin station name |
| `destination_id` | TEXT | Destination station ID |
| `destination_name` | TEXT | Destination station name |
| `route_id` | TEXT | Route identifier |
| `departure_at` | TIMESTAMPTZ | Scheduled departure time |
| `arrival_at` | TIMESTAMPTZ | Scheduled arrival time |
| `price_eur` | NUMERIC | Cheapest available fare in EUR |
| `fare_class` | TEXT | Fare class (operator-specific, not comparable across operators) |
| `booking_horizon_days` | INTEGER | Days before departure at time of collection |
| `train_number` | TEXT | Train/service identifier |
| `seats_available` | INTEGER | Available seats (where provided) |
| `is_direct` | BOOLEAN | Direct connection (no transfer) |
| `collected_at` | TIMESTAMPTZ | Timestamp of data collection (UTC) |

**Unique constraint:** `(operator, origin_id, destination_id, departure_at, fare_class, collected_at)` — duplicate crawl attempts are silently ignored via `ON CONFLICT DO NOTHING`.

### Booking Horizons

Prices are collected at 14 fixed points before departure:

```
90 · 60 · 45 · 30 · 21 · 14 · 10 · 7 · 6 · 5 · 4 · 3 · 2 · 1 days
```

### Price Basis

All analyses use `MIN(price_eur)` per route, horizon and collection day — i.e. the cheapest available fare for 1 adult, 2nd class / economy, single journey, no railcards or extras.

`fare_class` is operator-specific and not directly comparable across operators. Cross-operator analyses always use `price_eur` directly.

---

## Repository Structure

```
Rail-Data-Hub/
├── config/
│   ├── routes.py              # Route definitions, booking horizons
│   └── route_distances.csv    # Haversine distances per route
├── crawlers/
│   ├── base/
│   │   └── base_crawler.py    # BaseCrawler class (save, dedup, logging)
│   ├── db/
│   │   ├── db_crawler.py      # Deutsche Bahn crawler
│   │   └── microservice/      # Node.js db-vendo-client wrapper
│   │       └── server.mjs
│   ├── db_parsebot/           # DB backup via Parse.bot API
│   ├── trenitalia/            # Trenitalia crawler
│   ├── italo/                 # Italo crawler (Playwright, local only)
│   ├── flixtrain/             # Flixtrain crawler
│   ├── flixbus/               # Flixbus crawler
│   ├── ouigo_es/              # OUIGO España crawler
│   ├── ouigo_fr/              # OUIGO France crawler
│   ├── regiojet/              # RegioJet crawler
│   └── ceske_drahy/           # České dráhy crawler
├── scheduler/
│   ├── start_crawlers.py      # APScheduler — runs daily at 10:00 UTC
│   └── run_crawlers.py        # Manual one-off crawler run
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
│       ├── normalized_prices.py # €/km and €/h comparison
│       ├── operator_comp.py   # Cross-operator comparison
│       └── crawler_status.py  # System health view
├── data/
│   └── snapshot.csv           # Local CSV snapshot for offline mode
├── logs/                      # Crawler and scheduler logs (30-day rotation)
├── analysis/                  # Jupyter notebooks, geocoding scripts
└── docs/                      # Project documentation
```

---

## Dashboard

The dashboard runs at `http://193.196.37.50:8501` (VM) or `http://localhost:8501` (local).

### Analysis Modules

| Tab | Description |
|---|---|
| **Overview** | Price timeline for a route — MIN/AVG/MAX per operator, selectable time range |
| **Individual Train** | Price history of a specific train from 90 days out to departure |
| **Booking Horizon** | How does price change with lead time? Curves for all 14 horizons |
| **Time of Day** | Are early or late departures systematically cheaper? Heatmap by hour and weekday |
| **Operator Comparison** | Direct price comparison across operators at a selectable horizon |
| **€/km & €/h** | Normalised prices for route-neutral cross-operator comparison |
| **Crawler Status** | System health: last crawl times, record counts, 7-day availability |

### Offline Mode

If no database connection is available, the dashboard automatically falls back to `data/snapshot.csv`. A warning banner is shown in the sidebar. All analysis modules work in offline mode via Pandas equivalents of the DB queries.

---

## Known Limitations

### Deutsche Bahn API Block
The DB `dbnav`/vendo API (`app.services-bahn.de`) categorically blocks datacenter IPs with HTTP 403/500 at edge level (~40ms response time). This is documented in [db-vendo-client Issue #78](https://github.com/public-transport/db-vendo-client/issues/78), effective since ~18.05.2026. The bwCloud VM IP has been intermittently blocked since 06.07.2026 (`OPS_BLOCKED` error code). DB prices are collected as backup via `db_parsebot` (Parse.bot scraper).

### DB Morning Window
Both `db` and `db_parsebot` only cover a morning departure window (fixed `departure=10:00` parameter, resulting in connections roughly 08:00–13:15 departure time). This is a known limitation — the time series was not modified after collection started to avoid breaking continuity.

### Italo WAF Block
Italo's website is protected by Akamai WAF, which blocks headless Playwright browsers originating from datacenter IPs (`ERR_HTTP2_PROTOCOL_ERROR`). Italo crawls run locally only and are synced to the VM manually via CSV export/import.

### db_parsebot Instability
Parse.bot's API has an elevated error rate (~50% HTTP 503 responses). Records per run vary significantly (100–5000+ depending on API availability). Documented as a known data quality limitation.

### fare_class Heterogeneity
The `fare_class` column is populated differently across operators (Italo: productClass codes, Trenitalia: offer names, RegioJet: vehicleStandardKey, others: fixed strings or NULL). It is not used for cross-operator analysis — `price_eur` (cheapest available fare) is the reliable field.

### Flixtrain Thin Timetable
Flixtrain operates only 3 daily departures on most routes, resulting in lower absolute record counts compared to other operators. This reflects the actual timetable, not a crawler limitation.

---

## Team

| Member | Role |
|---|---|
| Xaver | Infrastructure, VM, crawlers, dashboard |
| Nico | Dashboard development |
| Fabian | Crawler development (České dráhy) |
| 2 × Econometrics | Analysis, regression, hypothesis testing |

---

## Links

- **Dashboard:** http://193.196.37.50:8501
- **Institution:** [KIT Institut für Volkswirtschaftslehre](https://www.wiwi.kit.edu)
- **DB API Issue:** [db-vendo-client #78](https://github.com/public-transport/db-vendo-client/issues/78)