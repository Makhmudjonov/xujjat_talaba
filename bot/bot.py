# bot/bot.py
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, filters
import time
from telegram import Update

from apps.models import GPARecord, Score, Student

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"  # .env fayldan olish tavsiya etiladi
CHANNEL_USERNAME = "@TSMUUz"

# Foydalanuvchini kuzatish uchun
user_states = {}

def start(update, context):
    user_id = update.effective_user.id
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            update.message.reply_text("✅ Botdan foydalanishingiz mumkin. HEMIS ID ni yuboring:")
            user_states[user_id] = "waiting_for_hemis"
        else:
            raise Exception("Not a member")
    except:
        update.message.reply_text(
            f"❗ Botdan foydalanish uchun kanalga a'zo bo‘ling: https://t.me/{CHANNEL_USERNAME[1:]}"
        )


def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_states.get(user_id) == "waiting_for_hemis":
        student = Student.objects.filter(student_id_number=text).first()
        if not student:
            update.message.reply_text("🚫 Bunday HEMIS ID topilmadi.")
            return

        gpa = GPARecord.objects.filter(student=student).order_by("-year", "-semester").first()
        scores = Score.objects.filter(application_item__application__student=student)

        response = f"👤 {student.full_name}\n"
        response += f"🎓 GPA: {gpa.gpa if gpa else 'Topilmadi'}\n\n📊 Ballar:\n"

        if scores.exists():
            for score in scores:
                response += f"📌 {score.application_item.direction.name} → {score.score}\n"
        else:
            response += "Hech qanday ball topilmadi."

        update.message.reply_text(response)
        user_states.pop(user_id, None)
    else:
        update.message.reply_text("Iltimos, avval /start buyrug'ini bering.")


def run_bot():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(MessageHandler(filters.text & ~filters.command, handle_message))

    print("Bot ishga tushdi...")
    updater.start_polling()
    updater.idle()
