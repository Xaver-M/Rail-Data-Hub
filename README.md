# Rail Data Hub

Automated tool for collecting and analysing price and capacity data in European long-distance rail.

## Project Overview

Rail Data Hub collects daily ticket prices and occupancy data from major European long-distance rail operators and makes them systematically comparable. The goal is a data driven analysis.



## Team

KIT – Karlsruhe Institute of Technology - part of the "Teamprojekt SS26 - Rail-Data-Hub" - Department for Economics and Management - Institute of Economics

## Project Structure

```
rail-data-hub/
├── crawlers/
│   ├── base/               # BaseCrawler (abstract class)
│   ├── db/                 # Deutsche Bahn (production - no capacity data)
│   ├── flixtrain/          # Flixtrain (production)
│   ├── trenitalia          # Trenitalia (production)
|   |── italo/              # Italo (WIP) 
│   ├── ouigo_es/           # OUIGO Spain (production)
│   ├── oebb/               # OBB (deprioritised)
│   └── sncf/               # SNCF (open data planned)
├── database/
│   ├── timescaledb/        # Schema & migrations
│   └── duckdb/             # Analytical queries
├── scheduler/              # APScheduler – daily crawler runs
├── dashboard/              # UI & visualisation (planned)
├── analysis/               # Competitive analysis modules (planned)
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
| Containerisation   | Docker Compose           | Local TimescaleDB instance           |
| Version control    | GitHub                   | Branch protection, collaboration     |

## Data Sources

| Operator        | Endpoint                      | Type                 | Status                      |
|-----------------|-------------------------------|----------------------|-----------------------------|
| Flixtrain       | global.api.flixbus.com        | Unofficial API       | Production                  |
| Trenitalia      | lefrecce.it BFF               | Unofficial API       | Production                  |
| OUIGO           | mdw02.api-es.ouigo.com        | Unofficial API       | Production                  |
| Italo           | Pending                       | Pending              | WIP                         |
| Deutsche Bahn   | -                             | Unofficial API         | Production                |
| SNCF            | data.sncf.com (static)        | Open Data (ODbL)     | Ingestion planned           |
| OBB             | HAFAS mgate                   | Semi-public          | Deprioritised               |

## Booking Horizons

Each route is queried daily at 15 booking horizons. This produces a price curve showing how fares develop as a function of the departure date — the core data for yield management analysis.

| Group                  | Horizons                             |
|------------------------|--------------------------------------|
| Daily, next week       | +1d +2d +3d +4d +5d +6d +7d          |
| Weekly up to 30 days   | +10d +14d +21d +30d                  |
| Monthly up to 90 days  | +45d +60d +90d                       |

## Database Schema

Three tables:

- **`price_observations`** — Hypertable (TimescaleDB). One row per price snapshot. Key field: `booking_horizon_days`, the core variable for yield management analysis.
- **`routes`** — Reference table. 13 competition routes with an operator-agnostic `route_id` (e.g. `hamburg-berlin`) for cross-operator comparisons.
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
| `scheduler/run_crawlers.py`           | Entry point for automated daily runs               |
