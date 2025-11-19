# main.py
# Advanced Trading Coach + Analyzer + Signal Generator (Hindi+English)
# Requirements:
# - TELEGRAM_TOKEN and OPENAI_API_KEY environment variables set
# - requirements.txt: python-telegram-bot==20.3, openai==1.3.5, pillow

import os
import logging
import tempfile
from functools import wraps
from typing import Optional

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

from openai import OpenAI

# ---------- Logging ----------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Env & OpenAI client ----------
OPENAI_KEY = os.getenv("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")
TELEGRAM_TOKEN = os.getenv("8518940185:AAHsookzvoS-o1df5u6UYnQcdcinN2UMpIM")

if not OPENAI_KEY or not TELEGRAM_TOKEN:
    logger.error("Set OPENAI_API_KEY and TELEGRAM_TOKEN environment variables.")
client = OpenAI(api_key=OPENAI_KEY)

# ---------- Helpers ----------
def ensure_user_storage(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if "last_image" not in context.user_data:
            context.user_data["last_image"] = None
        return await func(update, context, *args, **kwargs)
    return wrapper

def build_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("Full Analysis ✅", callback_data="full")],
        [InlineKeyboardButton("Quick Signals ⚡", callback_data="signals"),
         InlineKeyboardButton("Teach Me 📚", callback_data="teach")],
        [InlineKeyboardButton("Trend", callback_data="trend"),
         InlineKeyboardButton("Support/Resistance", callback_data="sr")],
        [InlineKeyboardButton("Entry/SL/Targets", callback_data="entry"),
         InlineKeyboardButton("Candles", callback_data="candle")],
        [InlineKeyboardButton("Indicators (RSI/Vol)", callback_data="indicator"),
         InlineKeyboardButton("Settings", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_signals_submenu():
    keyboard = [
        [InlineKeyboardButton("Conservative Signal", callback_data="signal_conservative")],
        [InlineKeyboardButton("Aggressive Signal", callback_data="signal_aggressive")],
        [InlineKeyboardButton("Scan Similar Setups", callback_data="signal_scan")],
        [InlineKeyboardButton("Back to Menu", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- OpenAI wrapper (safe) ----------
async def ask_openai(prompt: str, image_path: Optional[str] = None) -> str:
    """
    Uses OpenAI responses API. If image_path is provided, try to attach the image.
    Returns text response or error message.
    """
    try:
        if image_path:
            with open(image_path, "rb") as f:
                resp = client.responses.create(
                    model="gpt-4o-mini",
                    input=[
                        {"role": "system", "content": "You are a professional trading analyst. Answer in Hindi+English mix and keep it practical for swing traders."},
                        {"role": "user", "content": prompt},
                    ],
                    image=[f],
                    max_output_tokens=900,
                )
        else:
            resp = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": "You are a professional trading analyst. Answer in Hindi+English mix and keep it practical for swing traders."},
                    {"role": "user", "content": prompt},
                ],
                max_output_tokens=900,
            )

        # resp.output_text is a convenience property in many SDKs — fallback to concatenating text parts if needed
        if hasattr(resp, "output_text") and resp.output_text:
            return resp.output_text
        # fallback: try to extract content
        if getattr(resp, "output", None):
            parts = []
            for item in resp.output:
                if isinstance(item, dict) and item.get("content"):
                    if isinstance(item["content"], str):
                        parts.append(item["content"])
                    elif isinstance(item["content"], list):
                        for c in item["content"]:
                            if isinstance(c, dict) and c.get("text"):
                                parts.append(c["text"])
            return "\n".join(parts) if parts else str(resp)
        return str(resp)

    except Exception as e:
        logger.exception("OpenAI error")
        return f"OpenAI Error: {e}\n(If image analysis failed, try sending text-only or use Teach module.)"

# ---------- Command handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "Namaste! 👋\nMain tumhara Advanced Trading Assistant hoon (Hindi+English mix).\n\n"
            "📌 Send a chart image or press any option below to start.\n\n"
            "⚠️ Note: This is educational only — not financial advice.",
            reply_markup=build_main_keyboard()
        )
    except Exception:
        logger.exception("start handler failed")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send chart image → Press any button. Use Teach Me to learn step-by-step.")

# ---------- Image receiver ----------
@ensure_user_storage
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.photo:
            await update.message.reply_text("Koi valid chart image bhejo.")
            return
        photo = await update.message.photo[-1].get_file()
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        await photo.download_to_drive(tmp.name)
        context.user_data["last_image"] = tmp.name
        await update.message.reply_text("Chart received ✔️\nChoose an option:", reply_markup=build_main_keyboard())
    except Exception:
        logger.exception("handle_image failed")
        await update.message.reply_text("Image processing error. Try again please.")

# ---------- Button / Callback handler ----------
@ensure_user_storage
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        cmd = query.data
        last_image = context.user_data.get("last_image")

        # Back to menu
        if cmd == "back":
            await query.edit_message_text("Main menu:", reply_markup=build_main_keyboard())
            return

        # Settings (simple)
        if cmd == "settings":
            await query.edit_message_text("Settings:\n - Language: Hindi+English (fixed)\n - Mode: Educational\nBack to menu.", reply_markup=build_main_keyboard())
            return

        # Teach module (text only)
        if cmd == "teach":
            await query.edit_message_text("Loading Teach module... ⏳")
            prompt = ("Provide a modular trading course (Basics → Advanced) in short lessons. "
                      "Each lesson: explanation (Hindi+English), 1 practical example, 1 exercise/checklist.")
            text = await ask_openai(prompt, None)
            await context.bot.send_message(update.effective_chat.id, text)
            await context.bot.send_message(update.effective_chat.id, "Back to menu:", reply_markup=build_main_keyboard())
            return

        # Signals submenu
        if cmd == "signals":
            await query.edit_message_text("Choose signals type:", reply_markup=build_signals_submenu())
            return

        # If we need an image and none provided:
        image_required_cmds = {"full", "trend", "sr", "entry", "candle", "swing", "indicator", "signal_conservative", "signal_aggressive", "signal_scan"}
        if cmd in image_required_cmds and not last_image:
            await query.edit_message_text("Pehle chart image bhejo ❗", reply_markup=build_main_keyboard())
            return

        # Map commands -> prompts
        if cmd == "full":
            prompt = ("Full advanced analysis: trend, major S/R, swing highs/lows, breakout probability, "
                      "candlestick signals, RSI/volume/momentum observations (visual), entry ideas, SL, T1/T2/T3, risk/reward.")
            res = await ask_openai(prompt, last_image)
            await query.edit_message_text("Full Analysis delivered ✅")
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Next:", reply_markup=build_main_keyboard())
            return

        if cmd == "trend":
            prompt = "Analyze trend (Up/Down/Sideways). Explain structure (HH/HL or LH/LL) and short actionable note."
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "sr":
            prompt = "Identify major support and resistance levels (approx). Give trade ideas near those levels."
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "entry":
            prompt = "Suggest conservative and aggressive entry points, SL, and targets. Include RR and trade management notes."
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "candle":
            prompt = "List any important candlestick patterns visible and explain how to confirm them in context."
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "indicator":
            prompt = "Visually estimate RSI/volume/momentum behavior and give checklist rules to use them for confirmation."
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        # Signals: conservative/aggressive/scan
        if cmd == "signal_conservative":
            prompt = ("As a conservative swing trader, suggest an entry plan from this chart, "
                      "with smaller position, tight SL and realistic targets. Mention risk % and RR. Provide reasoning.")
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, "Conservative Signal:", reply_markup=None)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "signal_aggressive":
            prompt = ("As an aggressive trader, suggest a higher-risk entry or breakout plan from this chart. "
                      "Include SL, T1/T2, and explicit warning about higher risk.")
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, "Aggressive Signal:", reply_markup=None)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        if cmd == "signal_scan":
            prompt = ("Scan and describe if this chart matches any common profitable setups (breakout, pullback, range flip). "
                      "If yes, list similar setups to look for and the checklist to confirm them.")
            res = await ask_openai(prompt, last_image)
            await context.bot.send_message(update.effective_chat.id, res)
            await context.bot.send_message(update.effective_chat.id, "Back:", reply_markup=build_main_keyboard())
            return

        # fallback
        await query.edit_message_text("Unknown option, back to menu.", reply_markup=build_main_keyboard())
    except Exception:
        logger.exception("callback_handler error")
        try:
            await update.callback_query.edit_message_text("Internal error occurred. Try again or send /help.")
        except Exception:
            pass

# ---------- Text Q&A ----------
@ensure_user_storage
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        if text.lower() in {"menu", "options"}:
            await update.message.reply_text("Menu:", reply_markup=build_main_keyboard())
            return
        await update.message.reply_text("Soch raha hoon... ⏳")
        ans = await ask_openai(f"User question: {text}\nAnswer in Hindi+English, concise and practical.", context.user_data.get("last_image"))
        await update.message.reply_text(ans)
    except Exception:
        logger.exception("text_handler failed")
        await update.message.reply_text("Error processing your message. Try /help.")

# ---------- Global error handler ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # Notify user gently if possible
    try:
        if hasattr(update, "effective_message") and update.effective_message:
            await update.effective_message.reply_text("Oops, kuch error ho gaya. Try again or send /help.")
    except Exception:
        logger.exception("Failed sending error message to user")

# ---------- Main ----------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_error_handler(error_handler)

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
