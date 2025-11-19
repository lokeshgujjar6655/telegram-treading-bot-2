# main.py
# Advanced Telegram Trading Assistant (Educational + Chart Analysis + Interactive buttons)
# Requirements:
# - TELEGRAM_TOKEN and OPENAI_API_KEY must be set as environment variables
# - python-telegram-bot==20.3, openai==1.3.5, pillow

import os
import logging
import tempfile
from functools import wraps

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import openai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("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")
TELEGRAM_TOKEN = os.getenv("8518940185:AAHsookzvoS-o1df5u6UYnQcdcinN2UMpIM")
if not OPENAI_KEY or not TELEGRAM_TOKEN:
    logger.error("Please set OPENAI_API_KEY and TELEGRAM_TOKEN environment variables.")
openai.api_key = OPENAI_KEY

# helper: ensure we store the last image per user
def ensure_user_storage(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if "last_image" not in context.user_data:
            context.user_data["last_image"] = None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Home keyboard (options)
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("Full Analysis ✅", callback_data="full")],
        [
            InlineKeyboardButton("Trend Analysis", callback_data="trend"),
            InlineKeyboardButton("Support / Resistance", callback_data="sr"),
        ],
        [
            InlineKeyboardButton("Entry / SL / Targets", callback_data="entry"),
            InlineKeyboardButton("Candlestick Patterns", callback_data="candle"),
        ],
        [
            InlineKeyboardButton("Swing Trading View", callback_data="swing"),
            InlineKeyboardButton("RSI / Volume / Momentum", callback_data="indicator"),
        ],
        [InlineKeyboardButton("Teach me (Basics → Advanced)", callback_data="teach")],
    ]
    return InlineKeyboardMarkup(keyboard)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! 👋\n"
        "Main tumhara Trading Assistant hoon — Hindi + English mix.\n\n"
        "1) Chart image bhejo.\n"
        "2) Phir niche ke buttons se choose karo kya chahiye.\n\n"
        "⚠️ Note: Main educational analysis deta hoon — not financial advice. "
        "Hamesha apna risk manage karo.\n\n"
        "Bhejo chart ya press below options after sending chart.",
        reply_markup=main_keyboard(),
    )

# /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Use:\n"
        "- Send a chart image.\n"
        "- Press any button (Full Analysis / Trend / S/R / Entry...) to get focused output.\n"
        "- Use Teach me to learn concepts step-by-step.\n\n"
        "Bot gives analysis & educational content only."
    )

# When user sends image
@ensure_user_storage
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Koi valid image bhejo.")
        return

    # download best quality
    photo = await update.message.photo[-1].get_file()
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    await photo.download_to_drive(tmp.name)
    context.user_data["last_image"] = tmp.name

    await update.message.reply_text(
        "Chart received ✅\nChoose what analysis you want from buttons below.",
        reply_markup=main_keyboard(),
    )

# Helper to call OpenAI for analysis (text prompts)
# We send a prompt describing what we want. If image exists we mention it.
async def ask_openai(prompt: str, image_path: str | None = None):
    """
    Use ChatCompletion with a clear system+user prompt.
    If image_path provided, we'll attempt to include it in the message as an 'input_image' element.
    (Compatibility may depend on your OpenAI plan.) We'll fallback to text-only if needed.
    """
    try:
        if image_path:
            # Attempt image-enabled chat format (some SDK versions support 'input_image' style)
            with open(image_path, "rb") as f:
                messages = [
                    {"role": "system", "content": "You are an experienced trading analyst. Provide clear Hindi+English mix explanations suitable for swing traders."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image", "image": f},
                            {"type": "text", "text": prompt}
                        ],
                    },
                ]
                # The exact call below mirrors earlier examples. If your OpenAI SDK version doesn't accept the above,
                # you can instead use a text-only prompt and include "Image: [attached]" mention.
                resp = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=900,
                    temperature=0.3,
                )
        else:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an experienced trading analyst. Provide clear Hindi+English mix explanations suitable for swing traders."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=900,
                temperature=0.3,
            )
        text = resp["choices"][0]["message"]["content"]
        return text
    except Exception as e:
        logger.exception("OpenAI call failed")
        # fallback: return helpful message
        return f"OpenAI error: {e}\n\n(If image-analysis didn't work, I'll try text-only. Send '/teach' for learning modules.)"

# Callback queries for buttons
@ensure_user_storage
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cmd = query.data
    img = context.user_data.get("last_image")

    # If user hasn't sent image yet and requests image analysis, prompt them
    if cmd in {"full", "trend", "sr", "entry", "candle", "swing", "indicator"} and not img:
        await query.edit_message_text(
            "Pehle ek chart image bhejo, phir analysis ka option choose karo.\n\n"
            "Alternatively press 'Teach me' to learn trading concepts.",
            reply_markup=main_keyboard(),
        )
        return

    # Map to prompts
    prompts = {
        "full": "Give a FULL advanced swing-trading analysis in Hindi+English mix. Include: trend, major support & resistance, swing highs/lows, breakout probability, candlestick patterns, RSI/volume/momentum observations (visual estimate), clear Entry levels, Stoploss, Targets T1/T2/T3, and a short risk/reward note and summary in simple terms.",
        "trend": "Provide clear Trend analysis in Hindi+English: is it uptrend, downtrend, or sideways. Explain why (price structure, higher highs/lows or not), and short actionable notes for swing traders.",
        "sr": "Identify major Support and Resistance levels visually, explain significance and how to trade near these levels. Include approximate numeric levels if visible and example rules (buy on hold, fail -> sell) in Hindi+English.",
        "entry": "Based on the chart, suggest conservative and aggressive Entry ideas, corresponding Stoploss placements and Targets (T1/T2/T3). Explain reasoning and risk management. Educational tone.",
        "candle": "List and explain important Candlestick patterns visible (if any) and what they mean for the next move. Teach how to confirm candles with volume and context.",
        "swing": "Give a Swing Trading view: where to look for swing entries, how to identify swing highs/lows, timeframes to watch, and example setups in simple Hindi+English.",
        "indicator": "Discuss RSI, Volume, Momentum observations based on the image visually, and how to use these indicators to confirm trades. Give practical checklists.",
        "teach": "Provide a modular teaching plan: start with basics (trend, support/resistance), then candlesticks, indicators (RSI, MACD, ATR), and then entry/exit strategies with examples. Provide short exercises and checklist for each module."
    }

    # For Teach module we may not need an image
    prompt = prompts.get(cmd, "Give short analysis.")

    # Acknowledge start
    await query.edit_message_text("Working on it... hold on (just a sec).")

    # Call OpenAI
    analysis_text = await ask_openai(prompt, img if cmd != "teach" else None)

    # Send result (split if too long)
    MAX_LEN = 3500
    if len(analysis_text) <= MAX_LEN:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=analysis_text)
    else:
        # split into chunks
        for i in range(0, len(analysis_text), MAX_LEN):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=analysis_text[i:i+MAX_LEN])

    # Re-show keyboard so user can ask more
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Choose next:", reply_markup=main_keyboard())

# Teach command as text fallback
async def teach_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Loading teaching modules...")
    text = await ask_openai(
        "Provide a modular trading course for beginners up to advanced with small exercises and checklists. Keep language Hindi+English mix."
    )
    await update.message.reply_text(text)

# Fallback text handler (user typed text)
@ensure_user_storage
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text in {"menu", "options"}:
        await update.message.reply_text("Choose an option:", reply_markup=main_keyboard())
        return

    # If user asks quick question, forward to OpenAI as Q&A
    prompt = (
        f"Tera user asked: {update.message.text}\n\n"
        "Answer in Hindi + English mix, keep it short, clear, practical and educational for a swing trader."
    )
    await update.message.reply_text("Soch raha hoon... thoda time lagega.")
    resp = await ask_openai(prompt, context.user_data.get("last_image"))
    await update.message.reply_text(resp)

# Entry point
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("teach", teach_cmd))

    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
