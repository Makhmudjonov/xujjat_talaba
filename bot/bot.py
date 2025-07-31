# bot/bot.py
from telegram.ext import Updater, CommandHandler
import time

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"  # .env fayldan olish tavsiya etiladi
CHANNEL_USERNAME = "@TSMUUZ"

def start(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        status = member.status

        if status in ['member', 'administrator', 'creator']:
            update.message.reply_text("✅ Botdan foydalanishingiz mumkin. Xush kelibsiz!")
        else:
            raise Exception("Not a member")

    except:
        invite_link = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        update.message.reply_text(
            f"❗ Botdan foydalanish uchun avval kanalga a'zo bo‘ling: {invite_link}",
            disable_web_page_preview=True
        )

def run_bot():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    print("Telegram bot ishga tushdi...")
    updater.start_polling()

    # updater.idle() O‘RNIGA bu ishlatiladi
    while True:
        time.sleep(10)
