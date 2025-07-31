# bot/bot.py
from telegram.ext import Updater, CommandHandler
import time

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"  # .env fayldan olish tavsiya etiladi

def start(update, context):
    update.message.reply_text("Assalomu alaykum! Bot ishga tushdi.")

def run_bot():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    print("Telegram bot ishga tushdi...")
    updater.start_polling()

    # updater.idle() O‘RNIGA bu ishlatiladi
    while True:
        time.sleep(10)
