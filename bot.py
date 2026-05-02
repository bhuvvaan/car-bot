from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
from car import get_car_details, create_vehicle_manager
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = int(os.getenv("MY_CHAT_ID", "0"))

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set in .env file")

if not MY_CHAT_ID:
    raise ValueError("MY_CHAT_ID not set in .env file")

async def echo(update, context):

    # Whitelist: ignore messages from anyone else
    if update.message.chat_id != MY_CHAT_ID:
        return

    text = update.message.text
    if text == 'Charge':
        vm = create_vehicle_manager()
        my_vehicle = list(vm.vehicles.values())[0]
        await update.message.reply_text(f'{my_vehicle.ev_battery_percentage}')
    else:    
        await update.message.reply_text(f"You said: {text}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, echo))
    print("Bot is running. Send it a message on Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()