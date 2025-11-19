# main.py
# Advanced PRO signal bot: BTCUSDT + XAUUSDT
# Multi-timeframe (5m + 15m), SMA/EMA/MACD/RSI/ATR, volume confirmation
# Requirements: pyTelegramBotAPI, requests

import time
import telebot
import requests
import threading
import math
from statistics import mean

# ---------------- CONFIG ----------------
BOT_TOKEN = ("8315970431:AAFbFj_3EI7vksgEBxJt-uima3f2vV2D1Eo")
bot = telebot.TeleBot(BOT_TOKEN)

PAIRS = {
    "BTCUSDT": "Bitcoin",
    "XAUUSDT": "Gold"
}

# Binance endpoints
BASE_URL = "https://api.binance.com/api/v3/klines"

# signal interval / loop
SEND_INTERVAL_SECONDS = 300  # 5 minutes

# candle limits we will fetch
LIMIT_5M = 100
LIMIT_15M = 200

# ---------------- HELPERS: fetch candles ----------------
def fetch_klines(symbol: str, interval: str, limit: int):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        resp = requests.get(BASE_URL, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        # each item: [openTime, open, high, low, close, volume, ...]
        return data
    except Exception as e:
        print(f"fetch_klines error {symbol} {interval}: {e}")
        return None

# ---------------- INDICATORS ----------------
def to_floats(arr, idx):
    return [float(x[idx]) for x in arr]

def sma(values, period):
    if len(values) < period:
        return sum(values)/len(values)
    return sum(values[-period:]) / period

def ema(values, period):
    # simple EMA implementation: start with SMA for first value
    if not values:
        return None
    k = 2 / (period + 1)
    ema_prev = sum(values[:period]) / period if len(values) >= period else values[0]
    for price in values[period:]:
        ema_prev = price * k + ema_prev * (1 - k)
    return ema_prev

def full_ema_series(values, period):
    # return EMA series with same length (first values will be SMA-based)
    if not values:
        return []
    res = []
    for i in range(len(values)):
        if i+1 < period:
            res.append(sum(values[:i+1])/(i+1))
        elif i+1 == period:
            res.append(sum(values[:period])/period)
        else:
            k = 2 / (period + 1)
            res.append(values[i]k + res[-1](1-k))
    return res

def rsi(values, period=14):
    if len(values) < period+1:
        return None
    gains = []
    losses = []
    for i in range(1, period+1):
        diff = values[i] - values[i-1]
        gains.append(max(0, diff))
        losses.append(abs(min(0, diff)))
    avg_gain = sum(gains)/period
    avg_loss = sum(losses)/period if sum(losses) != 0 else 1e-9
    rs = avg_gain/avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    # Wilder smoothing for rest
    for i in range(period+1, len(values)):
        diff = values[i] - values[i-1]
        gain = max(0, diff)
        loss = abs(min(0, diff))
        avg_gain = (avg_gain*(period-1) + gain)/period
        avg_loss = (avg_loss*(period-1) + loss)/period
        rs = avg_gain / (avg_loss if avg_loss != 0 else 1e-9)
        rsi_val = 100 - (100 / (1 + rs))
    return rsi_val

def macd(values):
    # returns tuple (macd_last, signal_last, macd_hist_last)
    if len(values) < 26:
        return None, None, None
    ema12_series = full_ema_series(values, 12)
    ema26_series = full_ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12_series[-len(ema26_series):], ema26_series)]
    # signal is 9-period EMA of macd_line
    signal_series = full_ema_series(macd_line, 9)
    macd_last = macd_line[-1]
    signal_last = signal_series[-1] if signal_series else None
    hist = macd_last - signal_last if signal_last is not None else None
    return macd_last, signal_last, hist

def atr(klines, period=14):
    # klines entries have high (2), low (3), close (4) as strings
    highs = to_floats(klines, 2)
    lows = to_floats(klines, 3)
    closes = to_floats(klines, 4)
    trs = []
    for i in range(1, len(klines)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if not trs:
        return None
    # Wilder's ATR smoothing
    atr_val = sum(trs[:period]) / period if len(trs) >= period else sum(trs) / len(trs)
    for tr in trs[period:]:
        atr_val = (atr_val*(period-1) + tr) / period
    return atr_val

# ---------------- SIGNAL GENERATOR (PRO) ----------------
def generate_pro_signal(symbol):
    # fetch 5m and 15m candles
    k5 = fetch_klines(symbol, "5m", LIMIT_5M := 100)
    k15 = fetch_klines(symbol, "15m", LIMIT_15M := 100)
    if not k5 or not k15:
        return f"⚠ {symbol} data fetch error."

    closes5 = to_floats(k5, 4)
    volumes5 = to_floats(k5, 5)
    closes15 = to_floats(k15, 4)
    volumes15 = to_floats(k15, 5)

    last_price = closes5[-1]

    # indicators 5m
    sma9_5 = sma(closes5, 9)
    sma20_5 = sma(closes5, 20)
    sma50_5 = sma(closes5, 50)
    macd5, signal5, hist5 = macd(closes5)
    rsi5 = rsi(closes5, 14)
    atr5 = atr(k5, 14)
    vol_avg5 = mean(volumes5[-20:]) if len(volumes5) >= 20 else mean(volumes5)
    vol_now5 = volumes5[-1]

    # indicators 15m
    sma9_15 = sma(closes15, 9)
    sma20_15 = sma(closes15, 20)
    sma50_15 = sma(closes15, 50)
    macd15, signal15, hist15 = macd(closes15)
    rsi15 = rsi(closes15, 14)
    atr15 = atr(k15, 14)
    vol_avg15 = mean(volumes15[-20:]) if len(volumes15) >= 20 else mean(volumes15)
    vol_now15 = volumes15[-1]

    # trend checks
    trend5 = "UP" if sma9_5 > sma20_5 else ("DOWN" if sma9_5 < sma20_5 else "SIDE")
    trend15 = "UP" if sma9_15 > sma20_15 else ("DOWN" if sma9_15 < sma20_15 else "SIDE")

    # volume confirmation
    vol_conf_5 = vol_now5 > vol_avg5 * 1.2
    vol_conf_15 = vol_now15 > vol_avg15 * 1.1

    # macd confirmation: bullish crossover if macd>signal and hist positive, bearish opposite
    macd_conf_5 = (macd5 is not None and signal5 is not None and macd5 > signal5 and hist5 > 0)
    macd_conf_15 = (macd15 is not None and signal15 is not None and macd15 > signal15 and hist15 > 0)

    macd_bear_5 = (macd5 is not None and signal5 is not None and macd5 < signal5 and hist5 < 0)
    macd_bear_15 = (macd15 is not None and signal15 is not None and macd15 < signal15 and hist15 < 0)

    # decide signal: require alignment of trends + MACD confirmation + RSI not extreme + volume boost
    buy_ok = (trend5 == "UP" and trend15 == "UP" and macd_conf_5 and macd_conf_15 and vol_conf_5 and ((rsi5 is None) or (rsi5 < 85)))
    sell_ok = (trend5 == "DOWN" and trend15 == "DOWN" and macd_bear_5 and macd_bear_15 and vol_conf_5 and ((rsi5 is None) or (rsi5 > 15)))

    # Determine ATR for SL sizing (prefer 15m ATR if exists)
    used_atr = atr15 if atr15 else atr5 if atr5 else 0.0
    sl_buffer = (used_atr * 1.2) if used_atr else (last_price * 0.002)  # fallback 0.2%

    if buy_ok:
        direction = "BUY"
        sl = round(last_price - sl_buffer, 2)
        tp1 = round(last_price + used_atr * 1.5, 2) if used_atr else round(last_price + last_price*0.003, 2)
        tp2 = round(last_price + used_atr * 3, 2) if used_atr else round(last_price + last_price*0.006, 2)
        tp3 = round(last_price + used_atr * 5, 2) if used_atr else round(last_price + last_price*0.01, 2)
        conf = "HIGH"
    elif sell_ok:
        direction = "SELL"
        sl = round(last_price + sl_buffer, 2)
        tp1 = round(last_price - used_atr * 1.5, 2) if used_atr else round(last_price - last_price*0.003, 2)
        tp2 = round(last_price - used_atr * 3, 2) if used_atr else round(last_price - last_price*0.006, 2)
        tp3 = round(last_price - used_atr * 5, 2) if used_atr else round(last_price - last_price*0.01, 2)
        conf = "HIGH"
    else:
        direction = "NO SIGNAL"
        sl = "-"
        tp1 = tp2 = tp3 = "-"
        conf = "LOW/NO"

    # Build message
    msg = f"""
🔥 PRO SIGNAL - {symbol} ({PAIRS.get(symbol, '')}) 🔥

Price: {round(last_price, 2)}
Signal: {direction}   (Confirmation: {conf})

Indicators (5m / 15m):
• Trend (SMA9 vs SMA20): {trend5} / {trend15}
• MACD hist: {round(hist5,4) if hist5 is not None else 'NA'} / {round(hist15,4) if hist15 is not None else 'NA'}
• RSI(5m): {round(rsi5,2) if rsi5 else 'NA'}  RSI(15m): {round(rsi15,2) if rsi15 else 'NA'}
• ATR(15m): {round(atr15,4) if atr15 else 'NA'}
• Volume boost(5m): {'YES' if vol_conf_5 else 'NO'}

Entries & Risk:
• Entry Price: {round(last_price,2)}
• Stop Loss: {sl}
• TP1: {tp1}  TP2: {tp2}  TP3: {tp3}
• SL size based on ATR: {round(sl_buffer,4) if used_atr else 'fallback'}

Notes:
• Take only when signal is HIGH and time & risk fit your plan.
• Use position sizing so that risk per trade <= 1-2% of capital.
• This is algorithmic signal — verify before execution.

"""
    return msg

# ---------------- BACKGROUND SENDER ----------------
active_users = set()

def pro_signal_loop():
    while True:
        if active_users:
            for symbol in PAIRS.keys():
                try:
                    msg = generate_pro_signal(symbol)
                except Exception as e:
                    msg = f"⚠ Error generating {symbol}: {e}"
                for uid in list(active_users):
                    try:
                        bot.send_message(uid, msg, parse_mode="Markdown")
                    except Exception:
                        # if sending fails (blocked), remove user later optionally
                        pass
        time.sleep(SEND_INTERVAL_SECONDS)

threading.Thread(target=pro_signal_loop, daemon=True).start()

# ---------------- BOT HANDLERS ----------------
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.chat.id
    active_users.add(uid)
    bot.send_message(uid,
                     "🚀 PRO Signal Bot activated.\nYou will receive 5-minute high-confirmation signals for BTC & Gold.\nSend 'btc' or 'xau' to get on-demand signal.\nSend /stop to stop signals.")

@bot.message_handler(commands=['stop'])
def stop_cmd(m):
    uid = m.chat.id
    if uid in active_users:
        active_users.remove(uid)
    bot.send_message(uid, "Auto signals stopped. Send /start to resume.")

@bot.message_handler(func=lambda mess: True)
def all_messages(m):
    text = (m.text or "").lower()
    uid = m.chat.id
    # ensure user in active_users to get auto signals if they message
    active_users.add(uid)

    if "btc" in text:
        bot.reply_to(m, generate_pro_signal("BTCUSDT"), parse_mode="Markdown")
    elif "xau" in text or "gold" in text:
        bot.reply_to(m, generate_pro_signal("XAUUSDT"), parse_mode="Markdown")
    elif "signal" in text:
        # ask which
        bot.reply_to(m, "Which pair? Send 'BTC' or 'XAU' or both.")
    elif "stop" in text:
        if uid in active_users:
            active_users.remove(uid)
        bot.reply_to(m, "Stopped auto signals for you.")
    else:
        bot.reply_to(m, "Bot active ✅\nSend 'BTC' or 'XAU' for instant pro-signal, or wait for auto 5-min signals.")

# ---------------- RUN ----------------
print("PRO Signal Bot running...")
bot.infinity_polling()
