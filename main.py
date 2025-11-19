import telebot
from openai import OpenAI

# ========== YOUR KEYS ==========
BOT_TOKEN = ("8315970431:AAFbFj_3EI7vksgEBxJt-uima3f2vV2D1Eo")
OPENAI_API_KEY = ("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")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ========== MENU ==========
MENU = """
⭐ *Trading Assistant Menu* ⭐

1️⃣ Trading सिखाओ  
2️⃣ Chart / Photo Analyse करो  
3️⃣ Signal दो  
4️⃣ Option Trading Help  
5️⃣ Crypto Analyse  
6️⃣ Swing Trading  
7️⃣ Full Strategy  

जो option चाहिए number भेजो।
"""

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, MENU, parse_mode="Markdown")

# ========== CHOICE HANDLER ==========
@bot.message_handler(func=lambda m: m.text.isdigit())
def handle_number(msg):
    c = msg.text

    replies = {
        "1": "📘 Trading सीखने के लिए topic भेजो।",
        "2": "📸 Chart की फोटो भेजो, analyse करके दूँगा।",
        "3": "📊 Market बताओ (Nifty / BankNifty / Crypto)।",
        "4": "🟢 Options में क्या help चाहिए? Strike? Entry?",
        "5": "💰 Crypto coin name भेजो।",
        "6": "📈 Swing trading: Stock name भेजो।",
        "7": "🧠 Strategy किस market के लिए चाहिए?"
    }

    bot.reply_to(msg, replies.get(c, "❌ Wrong option!"))

# ========== PHOTO ANALYSIS ==========
@bot.message_handler(content_types=['photo'])
def photo_handler(msg):
    bot.reply_to(msg, "⏳ Chart analyse हो रहा है...")

    # Download photo
    file_id = msg.photo[-1].file_id
    file = bot.get_file(file_id)
    img_bytes = bot.download_file(file.file_path)

    # Call OpenAI vision model
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": "Analyse this trading chart."},
                {"type": "image", "image": img_bytes}
            ]}
        ]
    )

    answer = response.choices[0].message["content"]
    bot.reply_to(msg, answer)

# ========== TEXT CHAT ==========
@bot.message_handler(func=lambda m: True)
def ai_chat(msg):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": msg.text}
        ]
    )

    bot.reply_to(msg, response.choices[0].message["content"])

# ========== RUN BOT ==========
print("BOT STARTED…")
bot.infinity_polling()
