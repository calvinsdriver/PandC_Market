"""
Fetch P&C insurance companies stock prices.

Uses Yahoo Finance via yfinance (no API key).
Resources: https://github.com/ranaroussi/yfinance
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

import yfinance as yf

from research.resources import PC_INSURANCE_TICKERS

logger = logging.getLogger(__name__)

# yfinance uses curl_cffi.requests; SSL certs often fail on macOS without certifi or with verify=False
def _ssl_session():
    use_insecure = os.environ.get("USE_INSECURE_SSL", "").lower() in ("1", "true", "yes")
    if use_insecure:
        from curl_cffi import requests as curl_requests
        return curl_requests.Session(impersonate="chrome", verify=False)
    try:
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
    except ImportError:
        pass
    return None


def fetch_pc_stock_prices(
    tickers: list[str] | None = None,
    period: str = "1y",
) -> list[dict]:
    """
    Fetch latest price and basic stats for P&C insurance tickers.

    Args:
        tickers: List of symbols; defaults to PC_INSURANCE_TICKERS.
        period: yfinance period (1d, 5d, 1mo, etc.).

    Returns:
        List of dicts with symbol, name, price, change, volume, etc.
    """
    tickers = tickers or PC_INSURANCE_TICKERS
    tickers = [t for t in tickers if t]
    if not tickers:
        return []

    session = _ssl_session()
    kw = dict(
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if session is not None:
        kw["session"] = session

    try:
        data = yf.download(tickers, **kw)
    except Exception as e:
        logger.exception("yfinance download failed: %s", e)
        return []

    results = []
    now_utc = datetime.now(timezone.utc).isoformat()

    def ticker(sym):
        return yf.Ticker(sym, session=session) if session else yf.Ticker(sym)

    # Single ticker: columns are Flat
    if len(tickers) == 1:
        t = tickers[0]
        info = _ticker_info(ticker(t))
        row = data.iloc[-1] if len(data) > 0 else None
        
        history = []
        if 'Close' in data.columns:
            h = data['Close'].dropna().tolist()
            if len(h) > 50:
                step = len(h) / 50.0
                history = [h[int(i*step)] for i in range(50)]
            else:
                history = h
                
        results.append(_row_to_quote(t, row, info, history))
        return results

    # Multi ticker: columns are MultiIndex (Ticker, OHLCV)
    for t in tickers:
        try:
            if t not in data.columns.get_level_values(0):
                info = _ticker_info(ticker(t))
                results.append(_row_to_quote(t, None, info, []))
                continue
            sub = data[t].copy()
            row = sub.iloc[-1] if len(sub) > 0 else None
            
            history = []
            if 'Close' in sub.columns:
                h = sub['Close'].dropna().tolist()
                if len(h) > 50:
                    step = len(h) / 50.0
                    history = [h[int(i*step)] for i in range(50)]
                else:
                    history = h
                    
            info = _ticker_info(ticker(t))
            results.append(_row_to_quote(t, row, info, history))
        except Exception as e:
            logger.warning("Skip ticker %s: %s", t, e)
            results.append({
                "symbol": t,
                "name": t,
                "error": str(e),
                "fetched_at_utc": now_utc,
            })

    return results


def _ticker_info(ticker: yf.Ticker) -> dict:
    try:
        info = ticker.info
        return {
            "shortName": info.get("shortName") or info.get("longName") or ticker.ticker,
            "marketCap": info.get("marketCap"),
        }
    except Exception:
        return {"shortName": ticker.ticker, "marketCap": None}


def _row_to_quote(
    symbol: str,
    row,
    info: dict,
    history: list[float] | None = None,
) -> dict:
    now_utc = datetime.now(timezone.utc).isoformat()
    out = {
        "symbol": symbol,
        "name": info.get("shortName") or symbol,
        "fetched_at_utc": now_utc,
    }
    if row is not None and hasattr(row, "get"):
        # MultiIndex result: row is a Series with Close, Open, etc.
        close = row.get("Close") if hasattr(row, "get") else getattr(row, "Close", None)
        open_ = row.get("Open") if hasattr(row, "get") else getattr(row, "Open", None)
        volume = row.get("Volume") if hasattr(row, "get") else getattr(row, "Volume", None)
        if close is not None:
            out["price"] = float(close)
        if open_ is not None and close is not None:
            out["change_pct"] = round((float(close) - float(open_)) / float(open_) * 100, 2)
        if volume is not None:
            out["volume"] = int(volume)
    if info.get("marketCap") is not None:
        out["market_cap"] = info["marketCap"]
        
    if history and len(history) > 1:
        min_p = min(history)
        max_p = max(history)
        rng = max_p - min_p if max_p > min_p else 1
        pts = []
        for i, p in enumerate(history):
            x = (i / (len(history)-1)) * 100
            y = 30 - ((p - min_p) / rng) * 30
            pts.append(f"{x:.1f},{y:.1f}")
        out["sparkline_pts"] = " ".join(pts)
        out["sparkline_color"] = "var(--negative)" if history[-1] < history[0] else "var(--accent)"
        
    return out


def run_and_save(output_dir: Path | str = "output") -> list[dict]:
    """Fetch P&C stock prices and save JSON + markdown report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = fetch_pc_stock_prices()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    path_json = output_dir / f"pc_stock_prices_{ts}.json"
    with open(path_json, "w") as f:
        json.dump(rows, f, indent=2)
    logger.info("Wrote %s", path_json)

    path_md = output_dir / f"pc_stock_prices_{ts}.md"
    path_md.write_text(_format_markdown(rows), encoding="utf-8")
    logger.info("Wrote %s", path_md)

    return rows


def _format_markdown(rows: list[dict]) -> str:
    lines = [
        "# P&C Insurance Stock Prices",
        "",
        f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "| Symbol | Name | Price | Change % | Volume | Market Cap |",
        "|--------|------|-------|----------|--------|------------|",
    ]
    for r in rows:
        price = r.get("price")
        price_s = f"${price:.2f}" if isinstance(price, (int, float)) else "—"
        ch = r.get("change_pct")
        ch_s = f"{ch}%" if ch is not None else "—"
        vol = r.get("volume")
        vol_s = f"{vol:,}" if vol is not None else "—"
        cap = r.get("market_cap")
        cap_s = f"${cap/1e9:.2f}B" if isinstance(cap, (int, float)) else "—"
        lines.append(f"| {r.get('symbol', '')} | {r.get('name', '')} | {price_s} | {ch_s} | {vol_s} | {cap_s} |")
    return "\n".join(lines)
