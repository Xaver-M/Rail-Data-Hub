"""
APScheduler – Täglicher automatischer Crawler-Run
Startet alle aktiven Crawler einmal täglich um 06:00 Uhr.

Starten: py scheduler/run_crawlers.py
"""

from loguru import logger
import sys

# Eigener Logger für den Scheduler ohne operator-Binding
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add("logs/scheduler.log", rotation="1 day", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from datetime import datetime

from config.routes import ROUTES, BOOKING_HORIZONS
from crawlers.flixtrain.flixtrain_crawler import FlixtrainCrawler
from crawlers.trenitalia.trenitalia_crawler import TrenitaliaCrawler  
from crawlers.ouigo_es.ougio_es_crawler import OuigoEsCrawler


def run_all_crawlers():
    logger.info(f"=== Täglicher Crawler-Run gestartet: {datetime.now()} ===")

    crawlers = [
        FlixtrainCrawler(),
        TrenitaliaCrawler(), 
        OuigoEsCrawler(),
        # DBCrawler(),          ← später hinzufügen
    ]

    for crawler in crawlers:
        try:
            crawler.run(ROUTES, BOOKING_HORIZONS)
        except Exception as e:
            logger.error(f"Crawler {crawler.OPERATOR_NAME} fehlgeschlagen: {e}")
            continue

    logger.info("=== Täglicher Crawler-Run abgeschlossen ===")


if __name__ == "__main__":
    # Einmal sofort ausführen beim Start
    logger.info("Scheduler gestartet — erster Run sofort, dann täglich 06:00 Uhr")
    run_all_crawlers()

    # Dann täglich um 06:00 Uhr
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_all_crawlers,
        trigger=CronTrigger(hour=10, minute=0),
        id="daily_crawl",
        name="Täglicher Crawler-Run",
        misfire_grace_time=3600  # 1 Stunde Toleranz falls PC kurz aus war
    )

    logger.info("Nächster Run: morgen 10:00 Uhr")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler manuell gestoppt")
        scheduler.shutdown()
