#!/usr/bin/env python3
"""
P&C Market Research – single-page dashboard.

Displays stock prices and LLM deep summaries per news category (no article grids).
Run: python web.py  then open http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import markdown
from flask import Flask, render_template

app = Flask(__name__, template_folder=Path(__file__).resolve().parent / "templates")

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _latest_json(prefix: str) -> tuple[list | None, str | None]:
    """Return (parsed JSON list, timestamp) for the latest file matching prefix_*.json."""
    pattern = prefix + "_*.json"
    files = sorted(OUTPUT_DIR.glob(pattern), reverse=True)
    if not files:
        return None, None
    path = files[0]
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return None, None
    match = re.search(r"(\d{4}-\d{2}-\d{2}T[\d\-Z]+)\.json$", path.name)
    ts = match.group(1) if match else path.stem.replace(prefix + "_", "")
    return data if isinstance(data, list) else [data], ts


def _latest_summary(prefix: str) -> tuple[str | None, str | None]:
    """Return (markdown content, timestamp) for the latest file matching prefix_summary_*.md."""
    pattern = prefix + "_summary_*.md"
    files = sorted(OUTPUT_DIR.glob(pattern), reverse=True)
    if not files:
        return None, None
    path = files[0]
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, None
    match = re.search(r"summary_(\d{4}-\d{2}-\d{2}T[\d\-Z]+)\.md$", path.name)
    ts = match.group(1) if match else ""
    return text.strip(), ts


@app.route("/")
def index():
    stocks, stocks_ts = _latest_json("pc_stock_prices")
    pc_summary, pc_ts = _latest_summary("pc_news")
    gw_summary, gw_ts = _latest_summary("guidewire_news")
    ai_summary, ai_ts = _latest_summary("pc_ai_news")
    tw_summary, tw_ts = _latest_summary("twitter")

    def md_to_html(md: str | None) -> str:
        if not md:
            return ""
        return markdown.markdown(md, extensions=["nl2br"])

    return render_template(
        "dashboard.html",
        stocks=stocks or [],
        stocks_updated=stocks_ts,
        pc_summary_html=md_to_html(pc_summary),
        pc_summary_updated=pc_ts,
        guidewire_summary_html=md_to_html(gw_summary),
        guidewire_summary_updated=gw_ts,
        ai_summary_html=md_to_html(ai_summary),
        ai_summary_updated=ai_ts,
        twitter_summary_html=md_to_html(tw_summary),
        twitter_summary_updated=tw_ts,
    )


if __name__ == "__main__":
    import sys
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        out_dir = Path(__file__).resolve().parent / "public"
        out_dir.mkdir(parents=True, exist_ok=True)
        with app.app_context():
            html = index()
            (out_dir / "index.html").write_text(html, encoding="utf-8")
        print(f"Built static dashboard at {out_dir}/index.html")
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
