from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
import openai, os

openai.api_key = os.getenv("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")

async def start(update: Update, context):
    await update.message.reply_text("Namaste! Chart bhejo, main analyse kar deta hoon.")

async def handle_image(update: Update, context):
    photo = await update.message.photo[-1].get_file()
    img_path = "chart.jpg"
    await photo.download_to_drive(img_path)

    with open(img_path, "rb") as f:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "input_image", "image": f},
                    {"type": "text", "text": "Is chart ka Hindi me analysis do."}
                ]
            }]
        )

    reply = response.choices[0].message.content
    await update.message.reply_text(reply)

app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.run_polling()
