import telebot
import requests
import time
import threading
from flask import Flask, request

TOKEN = ("8315970431:AAFbFj_3EI7vksgEBxJt-uima3f2vV2D1Eo")
WEBHOOK_URL = "https://your-render-url.onrender.com/webhook"   # CHANGE THIS

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

CHAT_ID = None   # auto detect when user first sends /start

# ================================
# GET LIVE PRICE
# ================================
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        return float(requests.get(url, timeout=5).json()["price"])
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
# ADVANCED STRATEGY (HIGH CONFIRMATION)
# ================================
def signal_strategy(symbol):
    closes, highs, lows = get_candle(symbol)

    if not closes:
        return "Signal error..."

    c1 = closes[-1]
    c2 = closes[-2]
    c3 = closes[-3]

    high = max(highs[-5:])
    low = min(lows[-5:])

    sma5 = sum(closes[-5:]) / 5
    sma10 = sum(closes[-10:]) / 10

    signal = ""
    sl = None
    tp = None

    # BUY conditions
    if c1 > sma5 > sma10 and c1 > high * 0.995:
        signal = "BUY"
        sl = low
        tp = c1 + (c1 * 0.004)

    # SELL conditions
    elif c1 < sma5 < sma10 and c1 < low * 1.005:
        signal = "SELL"
        sl = high
        tp = c1 - (c1 * 0.004)

    else:
        signal = "NO TRADE (sideways)"

    return f"""
📡 LIVE 5-Minute Signal — {symbol}
Price: {c1}

SMA5: {round(sma5,2)}
SMA10: {round(sma10,2)}

Signal: {signal}
SL: {sl}
TP: {tp}

Strategy: MA + Breakout + 3-Candle Confirmation
"""

# ================================
# AUTO SIGNAL SENDER — EVERY 5 MIN
# ================================
def auto_send():
    global CHAT_ID
    while True:
        if CHAT_ID:
            bot.send_message(CHAT_ID, signal_strategy("BTCUSDT"), parse_mode="Markdown")
            bot.send_message(CHAT_ID, signal_strategy("XAUUSDT"), parse_mode="Markdown")
        time.sleep(300)  # 5 min

threading.Thread(target=auto_send, daemon=True).start()

# ================================
# TELEGRAM COMMANDS
# ================================
@bot.message_handler(commands=['start'])
def start(message):
    global CHAT_ID
    CHAT_ID = message.chat.id

    bot.send_message(message.chat.id,
    """
🔥 Webhook Bot Activated!

Live 5-min high confirmation signals:
- BTCUSDT
- XAUUSDT (Gold)

हर 5 मिनट auto signal aayega.
Bol de “btc” ya “gold” to fresh signal milega.
    """)

@bot.message_handler(func=lambda msg: True)
def reply_all(message):
    text = message.text.lower()

    if "btc" in text:
        bot.send_message(message.chat.id, signal_strategy("BTCUSDT"), parse_mode="Markdown")

    elif "gold" in text or "xau" in text:
        bot.send_message(message.chat.id, signal_strategy("XAUUSDT"), parse_mode="Markdown")

    else:
        bot.send_message(message.chat.id, "Batao bhai — BTC ya GOLD ka signal chahiye?")

# ================================
# WEBHOOK ENDPOINT
# ================================
@app.route("/webhook", methods=["POST"])
def webhook():
    json_update = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return "OK", 200

# ================================
# SET WEBHOOK AT STARTUP
# ================================
@app.route("/")
def home():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    return "Running"

# ================================
# RUN FLASK
# ================================
if _name_ == "_main_":
    app.run(host="0.0.0.0", port=10000)
