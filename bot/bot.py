# bot/bot.py
from telegram.ext import Updater, CommandHandler
import time

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"  # .env fayldan olish tavsiya etiladi
CHANNEL_USERNAME = "@TSMUU"

def start(update, context):
    user_id = update.effective_user.id
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            update.message.reply_text("✅ Botdan foydalanishingiz mumkin. HEMIS ID ni yuboring:")
        else:
            raise Exception("Not a member")
    except:
        update.message.reply_text(
            f"❗ Botdan foydalanish uchun kanalga a'zo bo‘ling: https://t.me/{CHANNEL_USERNAME[1:]}"
        )

def run_bot():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    print("Bot ishga tushdi...")
    updater.start_polling()
    updater.idle()
