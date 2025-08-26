import time
from datetime import datetime
import requests

from config import (
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TOP_COINS,
    PRICE_LOOP_SEC, NEWS_LOOP_SEC
)
from storage import (
    get_portfolio, set_portfolio, get_followed_coins,
    should_send_signal, was_news_sent, mark_news_sent
)
from analyzer import analyze_coin
from news_handler import fetch_crypto_news, analyze_news_item

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram env eksik, mesaj konsola:", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception as e:
        print("Telegram hatası:", e)

def format_reasons(reasons):
    return "\n".join([f"• {r}" for r in reasons])

def price_loop():
    pf = get_portfolio()
    current = pf["coin"]
    coins = get_followed_coins()

    best_buy = None  # (coin, score, analysis)

    for c in coins:
        try:
            res = analyze_coin(c)
            if not res:
                continue
            # Portföydeki coin için SELL sinyali varsa bildir
            if c == current and res["decision"] == "SELL":
                sid = f"{c}-SELL"
                if should_send_signal(c, sid):
                    msg = (f"📉 SAT ÖNERİSİ — [{c.upper()}]\n"
                           f"Fiyat: ${res['price']}\nSkor: {res['score']}\n{format_reasons(res['reasons'])}")
                    send_telegram(msg)

            # Aday en iyi BUY sinyali
            if res["decision"] == "BUY":
                if best_buy is None or res["score"] > best_buy[1]:
                    best_buy = (c, res["score"], res)
        except Exception as e:
            print(f"{c} analiz hatası:", e)
        time.sleep(1)  # rate limit nazikliği

    # Switch (zayıf -> güçlü) önerisi
    if best_buy and best_buy[0] != current:
        tgt, score, res = best_buy
        sid = f"SWITCH-{current}-TO-{tgt}"
        if should_send_signal(tgt, sid):
            msg = (f"🔁 DEĞİŞİM ÖNERİSİ — [{current.upper()} ➜ {tgt.upper()}]\n"
                   f"Yeni hedef Fiyat: ${res['price']} | Skor: {score}\n"
                   f"Nedenler:\n{format_reasons(res['reasons'])}\n\n"
                   f"Onay için: 'onaylandı {tgt}' — Reddet: 'reddedildi'")
            send_telegram(msg)

def news_loop():
    # Haberleri çek ve sadece **aksiyon** çıkaranları ve coin adı net olanları gönder
    items = fetch_crypto_news(query="crypto OR bitcoin OR ethereum", hours=2, page_size=30)
    if not items:
        return

    pf = get_portfolio()
    current = pf["coin"]

    for it in items:
        try:
            url = it.get("url")
            if not url or was_news_sent(url):
                continue

            res = analyze_news_item(it)
            if not res:
                continue

            coin = res["coin"]
            action = res["action"]  # BUY/SELL/HOLD

            # Mesaj **yalnızca aksiyon üretirse** gönderilsin
            if action == "HOLD":
                continue

            # Strateji:
            # - Portföydeki coine SELL haberi -> bildir
            # - Portföy dışı coine güçlü BUY -> switch öneri
            if coin == current and action == "SELL":
                msg = (f"📰 Haber Kaynaklı SAT — [{coin.upper()}]\n"
                       f"{it.get('title')}\n{it.get('url')}")
                send_telegram(msg)
                mark_news_sent(url)
            elif coin != current and action == "BUY":
                msg = (f"📰 Haber Kaynaklı AL/GEÇİŞ Önerisi — [{coin.upper()}]\n"
                       f"{it.get('title')}\n{it.get('url')}\n\n"
                       f"Onay için: 'onaylandı {coin}' — Reddet: 'reddedildi'")
                send_telegram(msg)
                mark_news_sent(url)
        except Exception as e:
            print("Haber işleme hatası:", e)

def run_bot():
    print("Alfa 3 — gelişmiş sürüm başlatıldı.")
    t_price = 0
    t_news  = 0
    while True:
        now = time.time()
        if now - t_price >= PRICE_LOOP_SEC:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Fiyat/pattern döngüsü")
            price_loop()
            t_price = now

        if now - t_news >= NEWS_LOOP_SEC:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Haber döngüsü")
            news_loop()
            t_news = now

        time.sleep(1)
