import telebot
import openai

# ENV variables (Render / Local)
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
OPENAI_KEY = "YOUR_OPENAI_API_KEY"

bot = telebot.TeleBot("8315970431:AAFbFj_3EI7vksgEBxJt-uima3f2vV2D1Eo")
openai.api_key = ("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")


# ---- START COMMAND ----
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg,
        "**Trading Assistant में आपका स्वागत है!**\n\n"
        "नीचे options में से चुनें:\n\n"
        "1️⃣ Trading सीखना\n"
        "2️⃣ Chart Analysis\n"
        "3️⃣ Buy/Sell Signal\n"
        "4️⃣ Risk Management Tips\n\n"
        "👉 कोई भी number भेजो (1–4)"
    )


# ---- MESSAGE HANDLER ----
@bot.message_handler(func=lambda m: True)
def reply(msg):
    user = msg.text.strip()

    if user == "1":
        send_ai(msg, "मुझे trading basics और advance सिखाओ।")
    elif user == "2":
        send_ai(msg, "यूज़र chart analysis चाहता है। Simple और clear बताओ।")
    elif user == "3":
        send_ai(msg, "Market का buy/sell signal दो (education purpose).")
    elif user == "4":
        send_ai(msg, "Risk management के top rules बताओ trader के लिए।")
    else:
        send_ai(msg, f"यूज़र ने पूछा: {user}. Trading expert की तरह जवाब दो।")


# ---- AI SEND FUNCTION ----
def send_ai(msg, prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        bot.reply_to(msg, response.choices[0].message['content'])
    except Exception as e:
        bot.reply_to(msg, f"Error: {e}")


print("Bot running...")
bot.polling()
