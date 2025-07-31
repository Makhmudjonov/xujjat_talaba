import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from django.conf import settings
import django
import os

# Django muhitini sozlash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.models import Student  # O'zgartiring: mos modelni import qiling

# Telegram log
logging.basicConfig(level=logging.INFO)

# Kanal ID (yoki username) — e'tibor bering, kanalga bot admin bo'lishi kerak!
CHANNEL_ID = "@tsmuuz"

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_member = await context.bot.get_chat_member(CHANNEL_ID, user.id)

    if chat_member.status not in ['member', 'administrator', 'creator']:
        await update.message.reply_text("Botdan foydalanish uchun kanalga a'zo bo'ling: " + CHANNEL_ID)
        return

    await update.message.reply_text("Hemis ID raqamingizni yuboring (masalan: 12345678):")

# Foydalanuvchi ID yuborganida
async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_id = update.message.text.strip()

    try:
        student = Student.objects.select_related('faculty', 'level', 'university1', 'specialty').get(student_id_number=student_id)
        info = (
            f"👤 FISH: {student.full_name}\n"
            f"🏛 OTM: {student.university1.name if student.university1 else '-'}\n"
            f"🏢 Fakultet: {student.faculty.name if student.faculty else '-'}\n"
            f"📚 Mutaxassislik: {student.specialty.name if student.specialty else '-'} ({student.specialty.code})\n"
            f"🎓 Kurs: {student.level.name if student.level else '-'}\n"
            f"🆔 Hemis ID: {student.student_id_number}"
        )
        await update.message.reply_text(info)
    except Student.DoesNotExist:
        await update.message.reply_text("❌ Bunday hemis ID topilmadi. Iltimos, to‘g‘ri kiriting.")

# Botni ishga tushirish
if __name__ == '__main__':
    bot_token = "8385707411:AAERO_nVYkVU6Y_3QOjN-ilgWP6c-jV16zQ"  # O'zgartiring: o'z bot tokeningizni kiriting

    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_id))

    print("Bot ishlayapti...")
    app.run_polling()
