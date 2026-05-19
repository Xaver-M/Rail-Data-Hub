"""
start_scheduler.py ; Automated daily crawler scheduler.
Runs all crawlers once immediately on start, then daily at 10:00 UTC which equals 12:00 CEST in the summer or 11:00 CET in the winter.

Run with: py scheduler/start_scheduler.py
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

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from scheduler.run_crawlers import run_all_crawlers


if __name__ == "__main__":
    logger.info("Scheduler starting — immediate run, then daily at 10:00 UTC -> 11:00 CET / 12:00 CEST")

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_all_crawlers,
        trigger=CronTrigger(hour=10, minute=0, timezone="UTC"),
        id="daily_crawl",
        name="Daily crawler run",
        misfire_grace_time=3600,
        coalesce=True,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
        scheduler.shutdown()