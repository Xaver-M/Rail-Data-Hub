"""
run_crawlers.py – Manual crawler run.
Executes all active crawlers once.

Run with: py scheduler/run_crawlers.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add("logs/scheduler.log", rotation="1 day", retention="30 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from config.routes import ROUTES, BOOKING_HORIZONS
from crawlers.flixtrain.flixtrain_crawler import FlixtrainCrawler
from crawlers.trenitalia.trenitalia_crawler import TrenitaliaCrawler
from crawlers.ouigo_es.ougio_es_crawler import OuigoEsCrawler
from crawlers.db.db_crawler import DBCrawler
from crawlers.regiojet.regiojet_crawler import RegioJetCrawler
from crawlers.ouigo_fr.ouigo_fr_crawler import OuigoFrCrawler
from crawlers.italo.italo_crawler import ItaloCrawler


def run_all_crawlers():
    logger.info(f"=== Crawler run started: {datetime.now()} ===")

    crawlers = [
        FlixtrainCrawler(),
        TrenitaliaCrawler(),
        OuigoEsCrawler(),
        DBCrawler(),
        RegioJetCrawler(),
        OuigoFrCrawler(),
        ItaloCrawler(),
    ]

    for crawler in crawlers:
        try:
            crawler.run(ROUTES, BOOKING_HORIZONS)
        except Exception as e:
            logger.error(f"Crawler {crawler.OPERATOR_NAME} failed: {e}")
        finally:
            if hasattr(crawler, "close"):
                crawler.close()

    logger.info("=== Crawler run completed ===")


if __name__ == "__main__":
    run_all_crawlers()