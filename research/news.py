"""
Deep research: fetch news from many sources (no single dependency).

- RSS: Insurance Journal, Dow Jones, CNBC, plus Google News search RSS per topic.
- NewsAPI: optional NEWS_API_KEY in .env for extra query-based results.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from research.resources import (
    ALL_RSS_FEEDS,
    GOOGLE_NEWS_QUERIES_AI,
    GOOGLE_NEWS_QUERIES_GUIDEWIRE,
    GOOGLE_NEWS_QUERIES_PC,
    GOOGLE_NEWS_RSS_BASE,
    GUIDEWIRE_NEWS_QUERIES,
    PC_AI_NEWS_QUERIES,
    PC_NEWS_QUERIES,
    RSS_FEEDS_FOR_GUIDEWIRE,
    RSS_FEEDS_FOR_PC_AI,
)

logger = logging.getLogger(__name__)

NEWS_API_BASE = "https://newsapi.org/v2/everything"


def _normalize_title(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()[:500]


def _google_news_rss_urls(queries: list[str]) -> list[str]:
    """Build Google News RSS URLs for given search queries (latest first)."""
    return [GOOGLE_NEWS_RSS_BASE.format(quote_plus(q)) for q in queries]


def fetch_rss_entries(
    feed_urls: list[str],
    max_entries_per_feed: int = 30,
    request_timeout: float = 15.0,
) -> list[dict]:
    """
    Fetch and parse RSS feeds. Returns list of normalized entry dicts.
    """
    entries = []
    seen_guids = set()

    for url in feed_urls:
        try:
            verify = os.environ.get("USE_INSECURE_SSL", "").lower() not in ("1", "true", "yes")
            resp = httpx.get(
                url,
                timeout=request_timeout,
                headers={"User-Agent": "PandC-Market-Research/1.0"},
                verify=verify,
                follow_redirects=True,
            )
            resp.raise_for_status()
            raw = feedparser.parse(resp.content)
        except Exception as e:
            logger.warning("RSS failed %s: %s", url, e)
            continue

        if getattr(raw, "bozo", False) and not getattr(raw, "entries", None):
            logger.warning("RSS parse error for %s", url)
            continue

        for e in getattr(raw, "entries", [])[:max_entries_per_feed]:
            guid = e.get("id") or e.get("link") or ""
            if guid in seen_guids:
                continue
            seen_guids.add(guid)
            title = _normalize_title(e.get("title") or "")
            link = e.get("link") or ""
            published = e.get("published") or e.get("updated") or ""
            summary = (e.get("summary") or "")[:1000] if e.get("summary") else ""
            feed_obj = getattr(raw, "feed", None) or raw.get("feed")
            source_name = getattr(feed_obj, "title", None) if feed_obj else None
            if not source_name and "news.google.com" in url:
                source_name = "Google News"
            if not source_name:
                source_name = url
            entries.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
                "source_feed": url,
                "source_name": source_name,
            })
    return entries


def fetch_newsapi(
    query: str,
    api_key: str,
    page_size: int = 20,
    sort_by: str = "publishedAt",
    request_timeout: float = 15.0,
) -> list[dict]:
    """
    Fetch news from NewsAPI (everything endpoint).
    Requires free API key from https://newsapi.org/
    """
    params = {
        "q": query,
        "apiKey": api_key,
        "pageSize": min(page_size, 100),
        "sortBy": sort_by,
        "language": "en",
    }
    verify = os.environ.get("USE_INSECURE_SSL", "").lower() not in ("1", "true", "yes")
    try:
        r = httpx.get(NEWS_API_BASE, params=params, timeout=request_timeout, verify=verify)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("NewsAPI request failed for query '%s': %s", query, e)
        return []

    if data.get("status") != "ok":
        return []
    articles = data.get("articles") or []
    out = []
    for a in articles:
        out.append({
            "title": _normalize_title(a.get("title") or ""),
            "link": a.get("url") or "",
            "published": a.get("publishedAt") or "",
            "summary": (a.get("description") or "")[:1000],
            "source_name": (a.get("source") or {}).get("name") or "NewsAPI",
            "query": query,
        })
    return out


def fetch_pc_news(
    use_newsapi: bool = True,
    newsapi_key: str | None = None,
    rss_urls: list[str] | None = None,
) -> list[dict]:
    """Deep research: P&C insurance news from many sources (RSS + Google News + optional NewsAPI)."""
    key = newsapi_key or os.environ.get("NEWS_API_KEY")
    rss_urls = rss_urls or (ALL_RSS_FEEDS + _google_news_rss_urls(GOOGLE_NEWS_QUERIES_PC))
    collected = fetch_rss_entries(rss_urls)
    if use_newsapi and key:
        for q in PC_NEWS_QUERIES:
            collected.extend(fetch_newsapi(q, key, page_size=15))
    return _dedupe_news(collected)


def fetch_guidewire_news(
    use_newsapi: bool = True,
    newsapi_key: str | None = None,
) -> list[dict]:
    """Deep research: Guidewire Software and competitors (topic-only feeds so dashboard section differs)."""
    key = newsapi_key or os.environ.get("NEWS_API_KEY")
    rss_urls = RSS_FEEDS_FOR_GUIDEWIRE + _google_news_rss_urls(GOOGLE_NEWS_QUERIES_GUIDEWIRE)
    collected = fetch_rss_entries(rss_urls)
    if use_newsapi and key:
        for q in GUIDEWIRE_NEWS_QUERIES:
            collected.extend(fetch_newsapi(q, key, page_size=15))
    return _dedupe_news(collected)


def fetch_pc_ai_news(
    use_newsapi: bool = True,
    newsapi_key: str | None = None,
) -> list[dict]:
    """Deep research: P&C insurers + AI (topic-only feeds so dashboard section differs)."""
    key = newsapi_key or os.environ.get("NEWS_API_KEY")
    rss_urls = RSS_FEEDS_FOR_PC_AI + _google_news_rss_urls(GOOGLE_NEWS_QUERIES_AI)
    collected = fetch_rss_entries(rss_urls)
    if use_newsapi and key:
        for q in PC_AI_NEWS_QUERIES:
            collected.extend(fetch_newsapi(q, key, page_size=15))
    return _dedupe_news(collected)


def _dedupe_news(entries: list[dict]) -> list[dict]:
    """Deduplicate by link, keep first occurrence."""
    seen = set()
    out = []
    for e in entries:
        link = (e.get("link") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        out.append(e)
    return sorted(out, key=lambda x: (x.get("published") or ""), reverse=True)


def run_news_and_save(output_dir: Path | str = "output") -> tuple[dict[str, list[dict]], str]:
    """
    Run all three news research tasks and save JSON + markdown per category.
    Returns (dict with pc_news, guidewire_news, pc_ai_news, timestamp_used).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    results = {}
    results["pc_news"] = fetch_pc_news()
    results["guidewire_news"] = fetch_guidewire_news()
    results["pc_ai_news"] = fetch_pc_ai_news()

    for name, items in results.items():
        path_json = output_dir / f"{name}_{ts}.json"
        with open(path_json, "w") as f:
            json.dump(items, f, indent=2)
        logger.info("Wrote %s (%d items)", path_json, len(items))
        path_md = output_dir / f"{name}_{ts}.md"
        path_md.write_text(_news_markdown(name, items), encoding="utf-8")
        logger.info("Wrote %s", path_md)

    return results, ts


def _news_markdown(title_key: str, items: list[dict]) -> str:
    title_map = {
        "pc_news": "P&C Insurance Companies – News",
        "guidewire_news": "Guidewire Software & Competitors – News",
        "pc_ai_news": "P&C Insurance & AI – News",
    }
    title = title_map.get(title_key, title_key)
    lines = [
        f"# {title}",
        "",
        f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]
    for i, e in enumerate(items[:100], 1):
        lines.append(f"## {i}. {e.get('title', '')}")
        lines.append("")
        if e.get("link"):
            lines.append(f"**Link:** {e['link']}")
        if e.get("published"):
            lines.append(f"**Published:** {e['published']}")
        if e.get("source_name"):
            lines.append(f"**Source:** {e['source_name']}")
        if e.get("summary"):
            lines.append("")
            lines.append(e["summary"][:800])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)
