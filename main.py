main.py (Corrected Full Working Version)

Advanced Telegram Trading Assistant – Hindi + English

Compatible with openai==1.3.5 and python-telegram-bot==20.3

import os import logging import tempfile from functools import wraps

from telegram import ( Update, InlineKeyboardButton, InlineKeyboardMarkup, ) from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, )

from openai import OpenAI

#########################################

Logging Setup

######################################### logging.basicConfig( format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, ) logger = logging.getLogger(name)

#########################################

ENV Variables

######################################### OPENAI_KEY = os.getenv("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") TELEGRAM_TOKEN = os.getenv("8518940185:AAHsookzvoS-o1df5u6UYnQcdcinN2UMpIM")

if not OPENAI_KEY or not TELEGRAM_TOKEN: logger.error("OPENAI_API_KEY or TELEGRAM_TOKEN not set!")

client = OpenAI(api_key=OPENAI_KEY)

#########################################

User Storage Decorator

######################################### def ensure_user_storage(func): @wraps(func) async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs): if "last_image" not in context.user_data: context.user_data["last_image"] = None return await func(update, context, *args, **kwargs) return wrapper

#########################################

Keyboards

######################################### def main_keyboard(): keyboard = [ [InlineKeyboardButton("Full Analysis ✅", callback_data="full")], [ InlineKeyboardButton("Trend Analysis", callback_data="trend"), InlineKeyboardButton("Support / Resistance", callback_data="sr"), ], [ InlineKeyboardButton("Entry / SL / Targets", callback_data="entry"), InlineKeyboardButton("Candlestick Patterns", callback_data="candle"), ], [ InlineKeyboardButton("Swing Trading View", callback_data="swing"), InlineKeyboardButton("RSI / Volume / Momentum", callback_data="indicator"), ], [InlineKeyboardButton("Teach Me (Basic → Advanced)", callback_data="teach")], ] return InlineKeyboardMarkup(keyboard)

#########################################

Start Command

######################################### async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "Namaste! 👋\nMain tumhara Trading Assistant hoon (Hindi + English).\n\n" "1️⃣ Chart image bhejo.\n2️⃣ Niche se analysis button choose karo.\n\n" "⚠️ Note: Education only — financial advice nahi.", reply_markup=main_keyboard(), )

#########################################

Help Command

######################################### async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "Use: Image bhejo → Button dabao → Analysis milega.\n" "Teach mode bhi available hai." )

#########################################

Handle Image

######################################### @ensure_user_storage async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE): if not update.message.photo: await update.message.reply_text("Valid chart image bhejo.") return

photo = await update.message.photo[-1].get_file()
tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
await photo.download_to_drive(tmp.name)

context.user_data["last_image"] = tmp.name

await update.message.reply_text(
    "Chart received ✔️\nChoose what you want:", reply_markup=main_keyboard()
)

#########################################

OpenAI Handler (Updated & Correct)

######################################### async def ask_openai(prompt: str, image_path: str | None): try: if image_path: with open(image_path, "rb") as f: resp = client.responses.create( model="gpt-4o-mini", input=[ {"role": "system", "content": "You are a professional trading analyst. Hindi+English mix."}, {"role": "user", "content": prompt}, ], image=[f], max_output_tokens=900, ) else: resp = client.responses.create( model="gpt-4o-mini", input=[ {"role": "system", "content": "You are a professional trading analyst. Hindi+English mix."}, {"role": "user", "content": prompt}, ], max_output_tokens=900, )

return resp.output_text

except Exception as e:
    logger.exception("OpenAI failed")
    return f"OpenAI Error: {e}"

#########################################

Button Handler

######################################### @ensure_user_storage async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

cmd = query.data
img = context.user_data.get("last_image")

prompts = {
    "full": "Give a complete advanced trading analysis with trend, S/R, entries, SL, targets.",
    "trend": "Explain market trend clearly.",
    "sr": "Identify major support and resistance.",
    "entry": "Give entry, stoploss, and targets.",
    "candle": "Explain visible candlestick patterns.",
    "swing": "Give swing trading view and setup.",
    "indicator": "Discuss RSI, momentum, volume.",
    "teach": "Teach trading from basics to advanced with exercises.",
}

if cmd != "teach" and not img:
    await query.edit_message_text(
        "Pehle chart image bhejo ❗", reply_markup=main_keyboard()
    )
    return

prompt = prompts.get(cmd, "Simple analysis.")

await query.edit_message_text("Processing... ⏳")

analysis = await ask_openai(prompt, img if cmd != "teach" else None)

MAX = 3500
chat_id = update.effective_chat.id

if len(analysis) <= MAX:
    await context.bot.send_message(chat_id, analysis)
else:
    for i in range(0, len(analysis), MAX):
        await context.bot.send_message(chat_id, analysis[i:i+MAX])

await context.bot.send_message(chat_id, "Choose next:", reply_markup=main_keyboard())

#########################################

Teach Command

######################################### async def teach_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("Teaching module starting... ⏳") text = await ask_openai("Make a full trading course.", None) await update.message.reply_text(text)

#########################################

Text Handler

######################################### @ensure_user_storage async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): txt = update.message.text.strip().lower()

if txt in {"menu", "options"}:
    await update.message.reply_text("Choose:", reply_markup=main_keyboard())
    return

prompt = f"User asked: {update.message.text} — answer in Hindi+English." 
await update.message.reply_text("Thinking... ⏳")
ans = await ask_openai(prompt, context.user_data.get("last_image"))
await update.message.reply_text(ans)

#########################################

MAIN ENTRY

######################################### def main(): app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("teach", teach_cmd))

app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.add_handler(CallbackQueryHandler(button_handler))

logger.info("Bot Running...")
app.run_polling()

if name == "main": main()
