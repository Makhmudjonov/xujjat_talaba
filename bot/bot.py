# bot/bot.py
import django
import os
import sys

from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import CallbackContext

# Django setup
sys.path.append("/home/tanlov/tanlov/xujjat_talaba")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.models import Student, ApplicationItem

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"
CHANNEL_USERNAME = "@TSMUUz"

user_states = {}  # user_id -> "awaiting_hemis"

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            update.message.reply_text("✅ Botdan foydalanishingiz mumkin. Iltimos, HEMIS ID raqamingizni yuboring:")
            user_states[user_id] = "awaiting_hemis"
        else:
            raise Exception("Not a member")
    except:
        update.message.reply_text(
            f"❗ Botdan foydalanish uchun kanalga a'zo bo‘ling: https://t.me/{CHANNEL_USERNAME[1:]}"
        )

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == "awaiting_hemis":
        try:
            student = Student.objects.get(student_id_number=text)
            items = ApplicationItem.objects.filter(application__student=student)

            gpa = None
            test_result = None
            for item in items:
                if item.gpa is not None:
                    gpa = item.gpa
                if item.test_result is not None:
                    test_result = item.test_result

            message = f"🎓 Talaba: {student.full_name}\n📘 GPA: {gpa or 'yo‘q'}\n🧪 Test natijasi: {test_result or 'yo‘q'}"
            update.message.reply_text(message)
            user_states[user_id] = None
        except Student.DoesNotExist:
            update.message.reply_text("❌ Bunday HEMIS ID topilmadi. Iltimos, qayta yuboring.")
    else:
        update.message.reply_text("Iltimos, /start buyrug‘i orqali boshlang va HEMIS ID ni yuboring.")

def run_bot():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(filters.text & ~filters.command, handle_message))

    print("🤖 Bot ishga tushdi...")
    updater.start_polling()
    updater.idle()
