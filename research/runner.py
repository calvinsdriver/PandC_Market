"""
Daily research runner: stock prices + all news categories + LLM deep summaries.

Invoked by the scheduler at 8am Pacific or manually.
"""

from __future__ import annotations

import logging
from pathlib import Path

from research.stock_prices import run_and_save as run_stock_prices
from research.news import run_news_and_save
from research.twitter import run_and_save as run_twitter_save
from research.summarize import run_summaries, summarize_twitter_with_llm

logger = logging.getLogger(__name__)


def run_all(output_dir: str | Path = "output") -> dict:
    """
    Run full deep research:
    1. P&C insurance companies stock prices
    2. P&C insurance related news
    3. Guidewire Software and competitors related news
    4. P&C insurance companies + AI news
    5. LLM deep summary per news category (if XAI_API_KEY set)

    Saves JSON, Markdown, and summary Markdown under output_dir. Returns summary dict.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {"stock_prices": None, "pc_news": 0, "guidewire_news": 0, "pc_ai_news": 0, "twitter_posts": 0}

    try:
        rows = run_stock_prices(output_dir=output_dir)
        summary["stock_prices"] = len(rows)
    except Exception as e:
        logger.exception("Stock prices run failed: %s", e)

    try:
        news, ts = run_news_and_save(output_dir=output_dir)
        summary["pc_news"] = len(news.get("pc_news", []))
        summary["guidewire_news"] = len(news.get("guidewire_news", []))
        summary["pc_ai_news"] = len(news.get("pc_ai_news", []))
        run_summaries(
            pc_news=news.get("pc_news", []),
            guidewire_news=news.get("guidewire_news", []),
            ai_news=news.get("pc_ai_news", []),
            output_dir=output_dir,
            ts=ts,
        )
    except Exception as e:
        logger.exception("News run failed: %s", e)

    try:
        tweets = run_twitter_save(output_dir=output_dir)
        summary["twitter_posts"] = len(tweets)
        # We reuse the timestamp from news run if available, or generate a fresh one
        # but the news ts is handy. Actually let's just use the current one or news ts. 
        # But 'ts' is only reliably defined if news succeeds. So we just let summarize_twitter do it or pass ts. 
        # Wait, if ts is defined, use it, else make a new one.
        from datetime import datetime, timezone
        tw_ts = ts if 'ts' in locals() else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        summarize_twitter_with_llm(tweets, ts=tw_ts, output_dir=output_dir)
    except Exception as e:
        logger.exception("Twitter run failed: %s", e)

    logger.info("Research run complete: %s", summary)
    return summary
