# Rail Data Hub

Automated tool for collecting and analysing price and capacity data in European long-distance rail.

## Project Overview

Rail Data Hub collects daily ticket prices and occupancy data from major European long-distance rail operators and makes them systematically comparable across a 90-day booking horizon. The goal is a data-driven analysis of yield management and competitive pricing dynamics.

## Team

KIT – Karlsruhe Institute of Technology — part of "Teamprojekt SS26 – Rail-Data-Hub", Department for Economics and Management, Institute of Economics.

## Project Structure

```
rail-data-hub/
├── crawlers/
│   ├── base/               # BaseCrawler (abstract class)
│   ├── db_parsebot/        # Deutsche Bahn via parse-bot scraping (production)
│   ├── flixtrain/          # Flixtrain (production)
│   ├── flixbus/            # Flixbus (production)
│   ├── trenitalia/         # Trenitalia (production)
│   ├── italo/              # Italo (production, local only — see notes)
│   ├── ouigo_es/           # OUIGO Spain (production)
│   ├── ouigo_fr/           # OUIGO France (production)
│   ├── regiojet/           # RegioJet (production)
│   ├── ceske_drahy/        # České dráhy (production)
│   ├── db/                 # Legacy DB API crawler (deprecated, see notes)
│   ├── ns/                 # Nederlandse Spoorwegen (planned)
│   ├── oebb/               # ÖBB (deprioritised)
│   └── sncf/               # SNCF open data (planned)
├── database/
│   ├── timescaledb/        # Schema & migrations
│   └── duckdb/             # Analytical queries (planned)
├── scheduler/              # APScheduler – daily crawler runs
├── analysis/               # Dashboard & analysis modules
├── docs/                   # Handbook & requirements
├── tests/
└── config/                 # Route configuration & scheduling
```

## Tech Stack

| Component          | Technology               | Purpose                              |
|--------------------|--------------------------|--------------------------------------|
| Crawlers           | Python 3.13, requests    | Data retrieval from operator APIs    |
| Scheduling         | APScheduler              | Daily automated runs                 |
| Database (write)   | TimescaleDB (PostgreSQL) | Time-series storage                  |
| Database (read)    | DuckDB                   | Analytical queries                   |
| Dashboard          | Streamlit, Plotly        | Interactive visualisation            |
| Containerisation   | Docker Compose           | Local TimescaleDB instance           |
| Version control    | GitHub                   | Branch protection, collaboration     |

## Data Sources

| Operator        | Endpoint                      | Type             | Status                          |
|-----------------|-------------------------------|------------------|---------------------------------|
| Flixtrain       | global.api.flixbus.com        | Unofficial API   | Production                      |
| Flixbus         | global.api.flixbus.com        | Unofficial API   | Production                      |
| Trenitalia      | lefrecce.it BFF               | Unofficial API   | Production                      |
| Italo           | api-biglietti.italotreno.com  | Unofficial API   | Production (local only)         |
| OUIGO Spain     | mdw02.api-es.ouigo.com        | Unofficial API   | Production                      |
| OUIGO France    | —                             | Unofficial API   | Production                      |
| RegioJet        | —                             | Unofficial API   | Production                      |
| České dráhy     | —                             | Unofficial API   | Production                      |
| Deutsche Bahn   | parse-bot scraping            | Scraping         | Production (via db_parsebot)    |
| Deutsche Bahn   | app.services-bahn.de          | Unofficial API   | Deprecated (WAF block, May '26) |
| SNCF            | data.sncf.com (static)        | Open Data (ODbL) | Ingestion planned               |
| ÖBB / NS        | —                             | —                | Not implemented                 |

### Notes on crawler status

- **Deutsche Bahn:** The original API crawler (`crawlers/db/`) stopped working after the infrastructure change in May 2026 — the `app.services-bahn.de` endpoint now returns HTTP 500 (WAF block). It has been replaced by **`db_parsebot`**, which scrapes via a parse bot and runs in production. The legacy module is kept for reference but is no longer scheduled.
- **Italo:** Runs in production, but is **blocked by an Akamai WAF** on the VM's datacenter IP. It is therefore executed from a local machine rather than the scheduled VM run.
- **db_parsebot** uses a trimmed horizon list (`DB_PARSEBOT_HORIZONS`) to stay within its API credit budget (~126 requests/day).

## Booking Horizons

Each route is queried daily at 15 booking horizons. This produces a price curve showing how fares develop as the departure date approaches — the core data for yield management analysis.

| Group                  | Horizons                             |
|------------------------|--------------------------------------|
| Daily, next week       | +1d +2d +3d +4d +5d +6d +7d          |
| Weekly up to 30 days   | +10d +14d +21d +30d                  |
| Monthly up to 90 days  | +45d +60d +90d                       |

Deutsche Bahn (`db_parsebot`) uses a reduced subset (`DB_PARSEBOT_HORIZONS`) due to API credit limits.

## Database Schema

Two tables:

- **`price_observations`** — Hypertable (TimescaleDB). One row per price snapshot. Key field: `booking_horizon_days`, the core variable for yield management analysis. A unique index on `(operator, origin_id, destination_id, departure_at, fare_class, collected_at)` enables idempotent `ON CONFLICT DO NOTHING` writes.
- **`crawler_logs`** — One row per crawler run. Status and error tracking.

## Setup (local)

### Prerequisites

- [Python 3.13+](https://python.org/downloads) – enable "Add to PATH" during installation
- [Docker Desktop](https://docker.com/products/docker-desktop) – for the local database
- [Git](https://git-scm.com)
- [VSCode](https://code.visualstudio.com) – recommended editor

### 1. Clone the repository

```cmd
git clone https://github.com/Xaver-M/Rail-Data-Hub.git
cd Rail-Data-Hub
```

### 2. Install Python dependencies

```cmd
py -m pip install -r requirements.txt
```

### 3. Set up environment variables

```cmd
copy .env.example .env
```

Open `.env` and fill in the values – ask Xaver for the database password.

### 4. Start the database

```cmd
docker-compose up -d
```

TimescaleDB is now running locally on port 5432. The schema is applied automatically on first start.

### 5. Test the connection

```cmd
py -c "import psycopg2; conn = psycopg2.connect(host='localhost', dbname='rail_data', user='rail_user', password='YOUR_PASSWORD'); print('Database connection successful!')"
```

### Stop the database

```cmd
docker-compose down
```

## Running the crawlers

```cmd
:: One-off manual run of all active crawlers
py scheduler/run_crawlers.py

:: Start the scheduler (immediate run, then daily at 10:00 UTC = 11:00 CET / 12:00 CEST)
py scheduler/start_crawlers.py
```

## Running the dashboard

```cmd
set PYTHONPATH=.
py -m streamlit run analysis/dashboard.py
```

The dashboard reads from TimescaleDB and offers route/trip-level price views, booking-horizon yield curves, operator comparison, time-of-day analysis, and crawler status.

## Git Workflow

We never commit directly to `main`. The workflow is always:

```
1. Create a new branch:   git checkout -b feature/my-feature
2. Make changes & commit
3. Push the branch:       git push origin feature/my-feature
4. Open a Pull Request on GitHub
5. Review by at least 1 team member
6. Merge into main
```

Active development happens on `dev`. Run `git fetch --all` before merges to avoid merging stale local branches.

### Commit Conventions

```
feat:     New feature
fix:      Bug fix
docs:     Documentation
refactor: Code restructuring without new functionality
test:     Adding tests
```

## Key Files

| File                                  | Purpose                                            |
|---------------------------------------|----------------------------------------------------|
| `.env`                                | Local configuration – never commit this            |
| `.env.example`                        | Template for `.env`                                |
| `docker-compose.yml`                  | Starts local TimescaleDB                           |
| `requirements.txt`                    | Python dependencies                                |
| `config/routes.py`                    | Route definitions with operator-specific IDs       |
| `database/timescaledb/01_schema.sql`  | Database schema                                    |
| `scheduler/run_crawlers.py`           | Manual one-off run of all crawlers                 |
| `scheduler/start_crawlers.py`         | Scheduled daily automated runs                     |
| `analysis/dashboard.py`               | Streamlit dashboard                                |