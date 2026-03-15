"""
Fetch daily Twitter (X.com) posts regarding P&C insurance.
Since X blocks guest search, we try Playwright, and fallback gracefully.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def fetch_x_posts(query: str = "P&C insurance") -> list[str]:
    """
    Attempt to scrape X.com using Playwright.
    Returns a list of tweet texts.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            logger.info("Starting headless Chromium to fetch X posts for query: %s", query)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            url = f"https://x.com/search?q={query.replace(' ', '+')}&src=typed_query"
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)
            tweets = page.locator('[data-testid="tweetText"]').all_inner_texts()
            browser.close()
            logger.info("Fetched %d tweets from X.", len(tweets))
            return tweets
    except ImportError:
        logger.warning("Playwright not installed. Skipping X fetch.")
        return []
    except Exception as e:
        logger.warning("Failed to fetch X posts: %s", e)
        return []

def run_and_save(output_dir: Path | str = "output") -> list[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tweets = fetch_x_posts("P&C insurance")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    
    path_json = output_dir / f"twitter_posts_{ts}.json"
    with open(path_json, "w") as f:
        json.dump(tweets, f, indent=2)
    logger.info("Wrote %s (%d items)", path_json, len(tweets))
    return tweets
