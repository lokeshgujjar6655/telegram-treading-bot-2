import telebot
import requests
import time
import threading

TOKEN =("8315970431:AAFbFj_3EI7vksgEBxJt-uima3f2vV2D1Eo")
bot = telebot.TeleBot(TOKEN)

# ================================
# GET LIVE PRICE
# ================================
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        return float(data["price"])
    except:
        return None

# ================================
# CANDLE DATA (5 MIN)
# ================================
def get_candle(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=20"
        data = requests.get(url, timeout=5).json()

        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]

        return closes, highs, lows

    except:
        return None, None, None

# ================================
# ADVANCED STRATEGY
# ================================
def signal_strategy(symbol):
    closes, highs, lows = get_candle(symbol)

    if not closes:
        return "Data error..."

    c1 = closes[-1]
    c2 = closes[-2]
    c3 = closes[-3]

    high = max(highs[-5:])
    low = min(lows[-5:])

    # Moving averages
    sma5 = sum(closes[-5:]) / 5
    sma10 = sum(closes[-10:]) / 10

    signal = ""
    sl = None
    tp = None

    # ===============================
    # BUY SIGNAL (high confirmation)
    # ===============================
    if c1 > sma5 > sma10 and c1 > high * 0.995:
        signal = "BUY"
        sl = low
        tp = c1 + (c1 * 0.004)

    # ===============================
    # SELL SIGNAL (high confirmation)
    # ===============================
    elif c1 < sma5 < sma10 and c1 < low * 1.005:
        signal = "SELL"
        sl = high
        tp = c1 - (c1 * 0.004)

    else:
        signal = "NO TRADE — Market Sideways"

    return f"""
📊 LIVE SIGNAL — {symbol}
Timeframe: 5 Min

Price: {c1}

SMA5: {round(sma5, 2)}
SMA10: {round(sma10, 2)}

Signal: {signal}

SL: {sl}
TP: {tp}

Strategy: MA + Breakout + 5-Candle Confirmation
    """

# ================================
# AUTO SIGNAL BROADCAST (EVERY 5 MIN)
# ================================
CHAT_ID = None  # auto-set when user sends /start

def auto_signal():
    while True:
        if CHAT_ID:
            msg1 = signal_strategy("BTCUSDT")
            bot.send_message(CHAT_ID, msg1, parse_mode="Markdown")

            msg2 = signal_strategy("XAUUSDT")
            bot.send_message(CHAT_ID, msg2, parse_mode="Markdown")

        time.sleep(300)  # 5 minutes

threading.Thread(target=auto_signal, daemon=True).start()

# ================================
# BOT COMMANDS
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    global CHAT_ID
    CHAT_ID = message.chat.id

    bot.send_message(message.chat.id,
    """
🔥 Auto 5-Minute Crypto + Gold Signal Bot Activated!

Pairs:
- BTCUSDT
- XAUUSDT (Gold)

Every 5 min → High confirmation signal aayega.

Kuch bhi likh do → fresh analysis milega.
    """)

@bot.message_handler(func=lambda msg: True)
def reply_to_all(message):
    text = message.text.lower()

    if "btc" in text:
        bot.send_message(message.chat.id, signal_strategy("BTCUSDT"), parse_mode="Markdown")
    elif "gold" in text or "xau" in text:
        bot.send_message(message.chat.id, signal_strategy("XAUUSDT"), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Bol bhai — BTC ya GOLD ka signal chahiye?")

# ================================
# RUN
# ================================
bot.polling(none_stop=True)
