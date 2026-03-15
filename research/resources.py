"""
Curated resources for P&C market research.

Sources:
- P&C insurers: stockanalysis.com, InvestSnips, TopForeignStocks (NYSE P&C list)
- Guidewire competitors: Duck Creek, Majesco, Insurity, Sapiens, etc.
- News: Insurance Journal, NewsAPI, RSS feeds
"""

# Major P&C insurance companies - stock tickers (US exchanges)
# Ordered roughly by market cap / relevance for daily tracking
PC_INSURANCE_TICKERS = [
    "CB",    # Chubb
    "PGR",   # Progressive
    "TRV",   # Travelers
    "ALL",   # Allstate
    "WRB",   # W.R. Berkley
    "CINF",  # Cincinnati Financial
    "MKL",   # Markel
    "AFG",   # American Financial Group
    "AIZ",   # Assurant
    "AXS",   # Axis Capital
    "CNA",   # CNA Financial
    "EG",    # Everest Group
    "KNSL",  # Kinsale Capital
    "LMND",  # Lemonade
    "MCY",   # Mercury General
    "ORI",   # Old Republic International
    "RDN",   # Radian Group
    "RNR",   # RenaissanceRe
    "THG",   # Hanover Insurance
    "SIGI",  # Selective Insurance
    "SAFT",  # Safety Insurance
    "HIG",   # Hartford (P&C segment material)
    "GWRE",  # Guidewire Software
]

# Guidewire Software (GWRE) and main competitors - for news and context
GUIDEWIRE_AND_COMPETITORS = {
    "GWRE": "Guidewire Software",
    # Competitors (public or notable; use for news search)
    "Duck Creek": "Duck Creek Technologies",
    "Majesco": "Majesco",
    "Insurity": "Insurity",
    "Sapiens": "Sapiens International",
    "Vertafore": "Vertafore",
    "EIS": "EIS Group",
    "Socotra": "Socotra",
}

# Search phrases for news APIs / RSS (P&C insurance general)
PC_NEWS_QUERIES = [
    "property casualty insurance",
    "P&C insurance",
    "property and casualty insurers",
]

# Search phrases for Guidewire + competitors news
GUIDEWIRE_NEWS_QUERIES = [
    "Guidewire Software",
    "Duck Creek Technologies",
    "Majesco insurance software",
    "Insurity insurance",
    "Sapiens insurance",
    "insurance core systems",
    "P&C insurance technology",
]

# Search phrases for P&C insurers adopting AI
PC_AI_NEWS_QUERIES = [
    "P&C insurance AI",
    "property casualty insurance artificial intelligence",
    "insurance company AI machine learning",
    "insurtech AI",
    "claims AI insurance",
    "underwriting AI insurance",
]

# RSS feeds (no API key) - multiple sources, never rely on one
# Direct publisher feeds
RSS_FEEDS_INSURANCE_JOURNAL = [
    "https://www.insurancejournal.com/rss/news/",
]
RSS_FEEDS_FINANCIAL = [
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # CNBC Business
    "https://www.cnbc.com/id/15837362/device/rss/rss.html",  # CNBC US News
]

# Google News RSS - search by query (latest first, aggregated from many publishers)
# Format: https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en
GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en"

# Query terms for Google News (URL-encoded in code)
GOOGLE_NEWS_QUERIES_PC = [
    "property casualty insurance",
    "P&C insurance",
    "Chubb Progressive Travelers Allstate insurance",
    "property and casualty insurers",
]
GOOGLE_NEWS_QUERIES_GUIDEWIRE = [
    "Guidewire Software",
    "Duck Creek Technologies insurance",
    "insurance core systems technology",
    "Majesco Insurity Sapiens insurance software",
]
GOOGLE_NEWS_QUERIES_AI = [
    "insurance AI artificial intelligence",
    "insurtech AI",
    "P&C insurance AI machine learning",
    "claims underwriting AI insurance",
]

# Combined direct feeds (no Google) for backward compatibility
ALL_RSS_FEEDS = list(dict.fromkeys(
    RSS_FEEDS_INSURANCE_JOURNAL + RSS_FEEDS_FINANCIAL
))

# Topic-only feeds so each dashboard section shows different content (no shared generic top)
# Guidewire and AI use only insurance + topic-specific Google News (no MarketWatch/CNBC)
RSS_FEEDS_FOR_GUIDEWIRE = RSS_FEEDS_INSURANCE_JOURNAL  # + Google News added in code
RSS_FEEDS_FOR_PC_AI = RSS_FEEDS_INSURANCE_JOURNAL       # + Google News added in code
