#!/usr/bin/env python3
"""
P&C Market Research Service.

Runs every day at 8:00 AM Pacific time:
- P&C insurance companies stock prices (yfinance)
- P&C insurance related news (RSS + optional NewsAPI)
- Guidewire Software and competitors news
- P&C insurers + AI news

Usage:
  python service.py              # run scheduler (8am Pacific daily)
  python service.py --once       # run once and exit
  RUN_ONCE=1 python service.py  # same as --once
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from research.runner import run_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PACIFIC = pytz.timezone("US/Pacific")
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def job(output_dir: Path | None = None):
    """Scheduled job: run full research and write to output/."""
    out = output_dir if output_dir is not None else OUTPUT_DIR
    logger.info("Starting scheduled research run (8am Pacific).")
    try:
        run_all(output_dir=out)
    except Exception as e:
        logger.exception("Scheduled run failed: %s", e)
    logger.info("Scheduled research run finished.")


def main():
    parser = argparse.ArgumentParser(description="P&C Market Research Service")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run research once and exit (no scheduler).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for JSON and Markdown reports.",
    )
    args = parser.parse_args()

    run_once = args.once or os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes")
    output_dir = args.output_dir

    if run_once:
        logger.info("Running research once (--once / RUN_ONCE).")
        job(output_dir=output_dir)
        return

    # Every day at 8:00 AM US/Pacific
    scheduler = BlockingScheduler(timezone=PACIFIC)
    scheduler.add_job(lambda: job(output_dir=output_dir), CronTrigger(hour=8, minute=0))
    logger.info("Scheduler started. Next run: 08:00 US/Pacific (daily).")
    scheduler.start()


if __name__ == "__main__":
    main()
