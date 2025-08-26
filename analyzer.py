import requests, time
import pandas as pd
import numpy as np

COINGECKO_TIMEOUT = 15

def fetch_ohlcv(coin):
    """Son 2 gün, saatlik fiyat serisi."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    params = {"vs_currency":"usd","days":"2","interval":"hourly"}
    r = requests.get(url, params=params, timeout=COINGECKO_TIMEOUT)
    data = r.json()
    if "prices" not in data:
        return None
    df = pd.DataFrame(data["prices"], columns=["ts","price"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df["price"] = df["price"].astype(float)
    return df

def rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = (avg_gain / avg_loss).replace([np.inf, -np.inf], np.nan).fillna(0)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    cross_up = macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]
    cross_dn = macd_line.iloc[-2] > signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]
    return macd_line.iloc[-1], signal_line.iloc[-1], cross_up, cross_dn

def bollinger(prices, window=20):
    sma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = sma + 2*std
    lower = sma - 2*std
    return upper, sma, lower

def slope(prices, window=6):
    """Basit trend eğimi: son 'window' noktada doğrusal regresyon eğimi ~ numpy polyfit."""
    y = prices.tail(window).values
    x = np.arange(len(y))
    if len(y) < window:
        return 0.0
    m, _ = np.polyfit(x, y, 1)
    return float(m)

def detect_patterns(prices, rsi_val, macd_up, macd_dn, upper, lower):
    """Basit, güvenli pattern seti."""
    last_p = prices.iloc[-1]
    u = upper.iloc[-1] if not np.isnan(upper.iloc[-1]) else None
    l = lower.iloc[-1] if not np.isnan(lower.iloc[-1]) else None

    reasons = []
    score = 0

    # RSI
    if rsi_val < 30:
        reasons.append("RSI aşırı düşük (<30)")
        score += 2
    elif rsi_val > 70:
        reasons.append("RSI aşırı yüksek (>70)")
        score -= 2

    # MACD
    if macd_up:
        reasons.append("MACD yukarı kesişim")
        score += 2
    if macd_dn:
        reasons.append("MACD aşağı kesişim")
        score -= 2

    # Bollinger breakout
    if u and last_p > u * 1.005:
        reasons.append("Üst Bollinger üstü kırılım (momentum)")
        score += 1
    if l and last_p < l * 0.995:
        reasons.append("Alt Bollinger altı kırılım (zayıflık)")
        score -= 1

    # Kısa periyot trend eğimi
    m = slope(prices, window=6)
    if m > 0:
        reasons.append("Kısa vadeli trend ↑")
        score += 1
    elif m < 0:
        reasons.append("Kısa vadeli trend ↓")
        score -= 1

    # Karar
    if score >= 3:
        decision = "BUY"
    elif score <= -3:
        decision = "SELL"
    else:
        decision = "HOLD"

    return decision, reasons, score

def analyze_coin(coin):
    df = fetch_ohlcv(coin)
    if df is None or len(df) < 30:
        return None

    prices = df["price"]
    rsi_series = rsi(prices)
    rsi_val = float(rsi_series.iloc[-1])

    macd_line, sig_line, macd_up, macd_dn = macd(prices)
    upper, sma, lower = bollinger(prices)

    decision, reasons, score = detect_patterns(prices, rsi_val, macd_up, macd_dn, upper, lower)

    return {
        "coin": coin,
        "price": round(prices.iloc[-1], 4),
        "rsi": round(rsi_val, 2),
        "macd": round(macd_line, 4),
        "macd_signal": round(sig_line, 4),
        "boll_upper": round(upper.iloc[-1], 4) if not np.isnan(upper.iloc[-1]) else None,
        "boll_lower": round(lower.iloc[-1], 4) if not np.isnan(lower.iloc[-1]) else None,
        "decision": decision,
        "reasons": reasons,
        "score": score
    }
