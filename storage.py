import json, time, os
from datetime import datetime, timedelta
from config import TOP_COINS, SIGNAL_COOLDOWN_MIN, NEWS_DEDUPE_HOURS

DB_PATH = os.getenv("DB_PATH", "alfa3_db.json")

DEFAULT_DB = {
    "portfolio": { "coin": "bitcoin", "amount_try": 700.0 },
    "followed": TOP_COINS,
    "last_signals": {},         # {coin: {"id": "...", "ts": 1690000000}}
    "sent_news": {}             # {url: 1690000000}
}

def _now():
    return int(time.time())

def _load():
    if not os.path.exists(DB_PATH):
        return DEFAULT_DB.copy()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_DB.copy()

def _save(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_followed_coins():
    db = _load()
    return db.get("followed", TOP_COINS)

def get_portfolio():
    db = _load()
    return db.get("portfolio", {"coin":"bitcoin","amount_try":700.0})

def set_portfolio(coin, amount_try=None):
    db = _load()
    if amount_try is None:
        amount_try = db.get("portfolio", {}).get("amount_try", 700.0)
    db["portfolio"] = {"coin": coin, "amount_try": amount_try}
    _save(db)

def should_send_signal(coin, signal_id):
    """Aynı sinyali cooldown bitmeden tekrar gönderme."""
    db = _load()
    last = db.get("last_signals", {}).get(coin)
    now = _now()
    if last and last.get("id") == signal_id and (now - last.get("ts", 0)) < SIGNAL_COOLDOWN_MIN * 60:
        return False
    db.setdefault("last_signals", {})[coin] = {"id": signal_id, "ts": now}
    _save(db)
    return True

def was_news_sent(url):
    db = _load()
    sent = db.get("sent_news", {})
    ts = sent.get(url)
    if not ts:
        return False
    # Eski haberleri otomatik temizle
    horizon = _now() - NEWS_DEDUPE_HOURS * 3600
    return ts > horizon

def mark_news_sent(url):
    db = _load()
    db.setdefault("sent_news", {})[url] = _now()
    _save(db)
