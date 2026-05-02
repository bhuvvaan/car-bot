from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set in .env file")

async def echo(update, context):
    text = update.message.text
    await update.message.reply_text(f"You said: {text}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, echo))
    print("Bot is running. Send it a message on Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()