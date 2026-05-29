"""APScheduler-based cron runner for the data pipeline."""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from collectors.weather import collect as collect_weather
from collectors.crowdsource import auto_verify_reports, resolve_stale_outages
from processors.aggregator import refresh_cell_stats

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def job_weather():
    log.info("Running weather collection...")
    await collect_weather()


def job_crowdsource():
    log.info("Running crowdsource processing...")
    auto_verify_reports()
    resolve_stale_outages()


def job_aggregator():
    log.info("Refreshing cell stats...")
    refresh_cell_stats()


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_weather, "interval", hours=1, id="weather_collect")
    scheduler.add_job(job_crowdsource, "interval", minutes=30, id="crowdsource")
    scheduler.add_job(job_aggregator, "interval", hours=2, id="aggregator")
    scheduler.start()

    log.info("Data pipeline scheduler started.")
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
