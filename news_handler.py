import requests, re
from datetime import datetime, timedelta
from config import NEWSAPI_KEY

# Basit anahtar kelime & alias eşleşmesi (coin -> olası adlar)
COIN_ALIASES = {
    "bitcoin": ["bitcoin","btc"],
    "ethereum": ["ethereum","eth"],
    "binancecoin": ["binance coin","bnb","binance"],
    "ripple": ["ripple","xrp"],
    "cardano": ["cardano","ada"],
    "dogecoin": ["dogecoin","doge"],
    "solana": ["solana","sol"],
    "tron": ["tron","trx"],
    "polkadot": ["polkadot","dot"],
    "litecoin": ["litecoin","ltc"],
    "matic-network": ["polygon","matic"],
    "avalanche-2": ["avalanche","avax"],
    "chainlink": ["chainlink","link"],
    "uniswap": ["uniswap","uni"],
    "stellar": ["stellar","xlm"],
    "cosmos": ["cosmos","atom"],
    "monero": ["monero","xmr"],
    "okb": ["okb"],
    "hedera-hashgraph": ["hedera","hbar"],
    "aptos": ["aptos","apt"],
}

POS_WORDS = [
    "approval","adoption","etf onay","partnership","listing","investment",
    "rekor","all-time high","funding","bullish","yükseliş","destek"
]
NEG_WORDS = [
    "ban","hack","exploit","lawsuit","delist","SEC suçu","regulation crackdown",
    "dump","çöküş","scam","dolandırıcılık","yasak"
]

DOMAINS = [
    "coindesk.com","cointelegraph.com","decrypt.co","theblock.co",
    "bloomberg.com","reuters.com","wsj.com","ft.com"
]

def _contains_any(text, words):
    t = (text or "").lower()
    return any(w in t for w in words)

def guess_coin(text):
    t = (text or "").lower()
    for cid, aliases in COIN_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{re.escape(a)}\b", t):
                return cid
    return None

def score_news(item):
    title = item.get("title") or ""
    desc  = item.get("description") or ""
    text = f"{title} {desc}".lower()

    pos = sum(1 for w in POS_WORDS if w in text)
    neg = sum(1 for w in NEG_WORDS if w in text)

    if pos - neg >= 2:
        return "BUY"
    elif neg - pos >= 2:
        return "SELL"
    else:
        return "HOLD"

def fetch_crypto_news(query="crypto", hours=2, page_size=20):
    """NEWSAPI varsa çeker; yoksa boş döner (bot çalışmaya devam eder)."""
    if not NEWSAPI_KEY:
        return []

    fr = (datetime.utcnow() - timedelta(hours=hours)).isoformat(timespec="seconds") + "Z"
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": page_size,
        "from": fr,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY,
        "domains": ",".join(DOMAINS)
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    articles = data.get("articles", [])
    items = []
    for a in articles:
        items.append({
            "title": a.get("title"),
            "description": a.get("description"),
            "url": a.get("url"),
            "published": a.get("publishedAt"),
            "source": (a.get("source") or {}).get("name","")
        })
    return items

def analyze_news_item(item):
    # Haber hangi coin’e ait?
    coin = guess_coin(f"{item.get('title','')} {item.get('description','')}")
    if not coin:
        return None  # coin tespiti yoksa atla

    action = score_news(item)  # BUY/SELL/HOLD
    return {
        "coin": coin,
        "action": action
    }
