from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
from car import get_car_details, refresh_vehicle_manager, tool_get_battery_status, tool_get_lock_status
from anthropic import Anthropic
import os
import asyncio
from tools import tools
from claude import handle_message_with_claude

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = int(os.getenv("MY_CHAT_ID", "0"))


if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set in .env file")

if not MY_CHAT_ID:
    raise ValueError("MY_CHAT_ID not set in .env file")

refresh_vehicle_manager()

async def echo(update, context):

    # Whitelist: ignore messages from anyone else
    if update.message.chat_id != MY_CHAT_ID:
        return

    user_message = update.message.text
    
    try:
        response = await handle_message_with_claude(user_message)
        await update.message.reply_text(response)
            
    except Exception as e:
        print(f'Failed with the error {e}')
        await update.message.reply_text("Something went wrong, try again later.")
         
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, echo))
    print("Bot is running. Send it a message on Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()