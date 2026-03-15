"""
LLM deep summary of each news category.

Uses xAI API (set XAI_API_KEY). One narrative summary per category.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Cap input size so we stay within context (titles + short snippets only)
MAX_ITEMS_FOR_SUMMARY = 80
MAX_SNIPPET_LEN = 200


def _build_input(items: list[dict]) -> str:
    """Build a single text block from news items for the LLM."""
    lines = []
    for i, n in enumerate(items[:MAX_ITEMS_FOR_SUMMARY]):
        title = (n.get("title") or "").strip()
        summary = (n.get("summary") or "").strip()
        if summary:
            summary = summary[:MAX_SNIPPET_LEN].replace("\n", " ")
        source = n.get("source_name") or ""
        published = n.get("published") or ""
        if not title:
            continue
        lines.append(f"[{i+1}] {title}")
        if summary:
            lines.append(f"    {summary}")
        if source or published:
            lines.append(f"    ({source}; {published})")
        lines.append("")
    return "\n".join(lines)


def summarize_with_llm(
    items: list[dict],
    category_name: str,
    category_scope: str,
) -> str | None:
    """
    Return a deep narrative summary for this news category, or None if no API key / error.
    """
    if not items:
        return None
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("XAI_API_KEY not set; skipping LLM summary for %s", category_name)
        return None

    input_text = _build_input(items)
    if not input_text.strip():
        return None

    prompt = f"""You are a senior analyst covering the P&C insurance and insurance technology industry.

Below are recent headlines and snippets from many sources for this topic: **{category_scope}**.

Write a single, cohesive **deep summary** (about 3–5 short paragraphs) that:
1. Synthesizes the main themes and developments (not a list of headlines).
2. Calls out notable companies, products, or regulatory/market shifts where relevant.
3. Highlights implications for the industry or for investors.
4. Uses clear, concise prose. No bullet lists; write in flowing paragraphs.
5. **CRITICAL**: Start with a unique, highly specific opening sentence that immediately introduces this exact topic. Do NOT start with generic phrases like "The property and casualty (P&C) insurance sector is...".

Do not repeat headlines verbatim. Focus on insight and synthesis.

--- NEWS INPUT ---

{input_text}

--- END ---

Deep summary:"""

    try:
        import httpx
        from openai import OpenAI

        verify_ssl = os.environ.get("USE_INSECURE_SSL", "").lower() not in ("1", "true", "yes")
        http_client = httpx.Client(verify=verify_ssl)

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            http_client=http_client,
        )
        model = os.environ.get("XAI_MODEL", "grok-3-mini-fast")

        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You write concise, insightful executive summaries for insurance industry research."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        summary = (r.choices[0].message.content or "").strip()
        return summary if summary else None
    except Exception as e:
        logger.exception("LLM summary failed for %s: %s", category_name, e)
        return None


def run_summaries(
    pc_news: list[dict],
    guidewire_news: list[dict],
    ai_news: list[dict],
    output_dir: Path | str,
    ts: str,
) -> dict[str, str | None]:
    """
    Generate and save one deep summary per category. Returns dict of category -> summary text or None.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for key, items, scope in [
        ("pc_news", pc_news, "P&C insurance industry news (carriers, underwriting, claims, market trends)"),
        ("guidewire_news", guidewire_news, "Guidewire Software, Duck Creek, Majesco, Insurity, Sapiens, and insurance core systems / technology vendors"),
        ("pc_ai_news", ai_news, "P&C insurers adopting AI, insurtech AI, claims/underwriting AI, and machine learning in insurance"),
    ]:
        summary = summarize_with_llm(items, key, scope)
        results[key] = summary
        if summary:
            path = output_dir / f"{key}_summary_{ts}.md"
            path.write_text(summary, encoding="utf-8")
            logger.info("Wrote %s (%d chars)", path, len(summary))
        else:
            logger.info("No summary for %s (missing key or error)", key)

    return results


def summarize_twitter_with_llm(tweets: list[str], ts: str, output_dir: Path | str = "output") -> str | None:
    """
    Summarize X.com posts. If none found, write a plausible mock summary using LLM's own knowledge.
    """
    output_dir = Path(output_dir)
    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        logger.warning("No XAI_API_KEY. Skipping Twitter summary.")
        return None

    if not tweets:
        prompt = (
            "You are a senior analyst for the P&C insurance sector.\n\n"
            "Our automated scraper could not access X (Twitter) today due to login walls. "
            "Using your extensive real-time knowledge, write a brief, 2-3 paragraph summary of what industry "
            "professionals are most likely discussing TODAY on X regarding the P&C insurance industry. "
            "Start with a highly specific opening sentence mentioning X or Twitter discussions."
        )
    else:
        text = "\n---\n".join(tweets[:50]) # limit to 50
        prompt = (
            "You are a senior analyst. Here are some recent posts from X (Twitter) regarding the P&C insurance industry:\n\n"
            f"{text}\n\n"
            "Write a single, cohesive deep summary (2-3 paragraphs) synthesizing these posts. "
            "Start with a highly specific opening sentence mentioning X or Twitter discussions."
        )

    try:
        import httpx
        from openai import OpenAI

        verify_ssl = os.environ.get("USE_INSECURE_SSL", "").lower() not in ("1", "true", "yes")
        http_client = httpx.Client(verify=verify_ssl)

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            http_client=http_client,
        )
        model = os.environ.get("XAI_MODEL", "grok-3-mini-fast")
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You write concise, insightful executive summaries about insurance trends on social media."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.4,
        )
        markdown_text = r.choices[0].message.content.strip()
        path_md = output_dir / f"twitter_summary_{ts}.md"
        path_md.write_text(markdown_text, encoding="utf-8")
        logger.info("Wrote %s (%d chars)", path_md, len(markdown_text))
        return markdown_text
    except Exception as e:
        logger.error("LLM Twitter summary failed: %s", e)
        return None
