"""
run_crawlers.py – Runs all enabled crawlers once.

Used by the systemd timer (rdh-crawlers.timer) on the VM and for manual runs.

Which crawlers run:
  1. --only CLI argument          (manual tests)
  2. RDH_CRAWLERS in .env         (per machine, e.g. VM vs. local PC)
  3. DEFAULT_VM_CRAWLERS below    (fallback)

Examples:
  python scheduler/run_crawlers.py
  python scheduler/run_crawlers.py --only trenitalia,ouigo_fr
  python scheduler/run_crawlers.py --list

Exit code: 0 if all crawlers ran, 1 if at least one crawler failed completely
(-> systemd marks the run as failed, visible via `systemctl --failed`).
"""

import argparse
import importlib
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from config.routes import ROUTES, BOOKING_HORIZONS, DB_PARSEBOT_HORIZONS


# ─────────────────────────────────────────────────────────────
# CRAWLER REGISTRY
# ─────────────────────────────────────────────────────────────
# name -> (module, class, horizons)
# horizons = None means: crawler brings its own routes/horizons (call .run() without args)

CRAWLER_REGISTRY = {
    "flixtrain":      ("crawlers.flixtrain.flixtrain_crawler",           "FlixtrainCrawler",     BOOKING_HORIZONS),
    "flixbus":        ("crawlers.flixbus.flixbus_crawler",               "FlixbusCrawler",       BOOKING_HORIZONS),
    "trenitalia":     ("crawlers.trenitalia.trenitalia_crawler",         "TrenitaliaCrawler",    BOOKING_HORIZONS),
    "ouigo_es":       ("crawlers.ouigo_es.ougio_es_crawler",             "OuigoEsCrawler",       BOOKING_HORIZONS),
    "ouigo_fr":       ("crawlers.ouigo_fr.ouigo_fr_crawler",             "OuigoFrCrawler",       BOOKING_HORIZONS),
    "regiojet":       ("crawlers.regiojet.regiojet_crawler",             "RegioJetCrawler",      BOOKING_HORIZONS),
    "ceske_drahy":    ("crawlers.ceske_drahy.ceske_drahy_crawler",       "CeskeDrahyCrawler",    BOOKING_HORIZONS),
    "db":             ("crawlers.db.db_crawler",                         "DBCrawler",            BOOKING_HORIZONS),
    # trimmed horizons to stay within Parse.bot credit budget
    "db_parsebot":    ("crawlers.db_parsebot.db_parsebot_crawler",       "DBParseBotCrawler",    DB_PARSEBOT_HORIZONS),
    # headed Playwright browser -> service runs under xvfb-run (deploy/install_systemd.sh)
    "italo":          ("crawlers.italo.italo_crawler",                   "ItaloCrawler",         BOOKING_HORIZONS),
    # own routes/horizons from config/flight_routes.py
    "google_flights": ("crawlers.google_flights.google_flights_crawler", "GoogleFlightsCrawler", None),
}

# Fallback if RDH_CRAWLERS is not set.                                  
# db: datacenter IP blocked (db-vendo-client #78) -> db_parsebot instead
DEFAULT_VM_CRAWLERS = [
    "flixtrain",
    "flixbus",
    "trenitalia",
    "ouigo_es",
    "ouigo_fr",
    "regiojet",
    "ceske_drahy",
    "db_parsebot",
    "italo",
    "google_flights",
]


# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────

def setup_scheduler_logging():
    # BaseCrawler calls logger.remove() on init -> re-attach scheduler handlers
    # after every crawler so the summary always lands in scheduler.log
    logger.remove()
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")
    os.makedirs("logs", exist_ok=True)
    logger.add("logs/scheduler.log", rotation="1 day", retention="30 days",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def resolve_enabled(only: str | None) -> list[str]:
    if only:
        names = [n.strip() for n in only.split(",") if n.strip()]
    elif os.getenv("RDH_CRAWLERS"):
        names = [n.strip() for n in os.getenv("RDH_CRAWLERS").split(",") if n.strip()]
    else:
        names = DEFAULT_VM_CRAWLERS

    unknown = [n for n in names if n not in CRAWLER_REGISTRY]
    if unknown:
        raise SystemExit(f"Unknown crawler(s): {unknown}. Valid: {sorted(CRAWLER_REGISTRY)}")
    return names


def run_one(name: str) -> bool:
    """Import, instantiate and run one crawler. Never raises."""
    module_name, class_name, horizons = CRAWLER_REGISTRY[name]
    start = time.monotonic()
    crawler = None
    try:
        module = importlib.import_module(module_name)
        crawler = getattr(module, class_name)()
        if horizons is None:
            crawler.run()
        else:
            crawler.run(ROUTES, horizons)
        ok = True
    except Exception as e:
        setup_scheduler_logging()
        logger.error(f"Crawler {name} failed: {type(e).__name__}: {e}")
        ok = False
    finally:
        if crawler is not None and hasattr(crawler, "close"):
            try:
                crawler.close()
            except Exception as e:
                logger.warning(f"Crawler {name} close() failed: {e}")

    setup_scheduler_logging()
    logger.info(f"Crawler {name} {'finished' if ok else 'FAILED'} after {time.monotonic() - start:.0f}s")
    return ok


def log_summary(run_start: datetime):
    """Records written per operator during this run (sanity check in the log)."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "rail_data"),
            user=os.getenv("DB_USER", "rail_user"),
            password=os.getenv("DB_PASSWORD"),
        )
        with conn, conn.cursor() as cur:
            cur.execute("""
                SELECT operator, COUNT(*)
                FROM price_observations
                WHERE collected_at >= %s
                GROUP BY operator
                ORDER BY operator
            """, (run_start,))
            rows = cur.fetchall()
        conn.close()

        if not rows:
            logger.warning("Summary: 0 records written in this run")
        for operator, n in rows:
            logger.info(f"Summary: {operator:<16} {n:>7} records")
    except Exception as e:
        logger.warning(f"Summary query failed: {e}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def run_all_crawlers(only: str | None = None) -> int:
    setup_scheduler_logging()
    enabled = resolve_enabled(only)
    run_start = datetime.now(timezone.utc)

    logger.info(f"=== Crawler run started: {run_start:%Y-%m-%d %H:%M:%S} UTC ===")
    logger.info(f"Enabled crawlers: {', '.join(enabled)}")

    failed = [name for name in enabled if not run_one(name)]

    log_summary(run_start)
    if failed:
        logger.error(f"=== Crawler run completed with failures: {', '.join(failed)} ===")
        return 1
    logger.info("=== Crawler run completed successfully ===")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Rail Data Hub crawlers once.")
    parser.add_argument("--only", help="Comma-separated crawler names, overrides RDH_CRAWLERS")
    parser.add_argument("--list", action="store_true", help="List crawlers and which are enabled")
    args = parser.parse_args()

    if args.list:
        enabled = resolve_enabled(args.only)
        for name in CRAWLER_REGISTRY:
            print(f"{'[x]' if name in enabled else '[ ]'} {name}")
        sys.exit(0)

    sys.exit(run_all_crawlers(args.only))