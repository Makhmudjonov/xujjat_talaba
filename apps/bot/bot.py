# import logging
# from telegram import Update
# from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
# import asyncio

# from apps.models import Student

# TOKEN = "8385707411:AAERO_nVYkVU6Y_3QOjN-ilgWP6c-jV16zQ"
# CHANNEL_ID = "@tsmuuz"

# logging.basicConfig(level=logging.INFO)

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     chat_member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
#     if chat_member.status not in ['member', 'administrator', 'creator']:
#         await update.message.reply_text("Kanalga a'zo bo'ling: " + CHANNEL_ID)
#         return
#     await update.message.reply_text("Hemis ID raqamingizni yuboring:")

# async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     student_id = update.message.text.strip()
#     try:
#         student = Student.objects.select_related("faculty", "specialty", "level", "university1").get(student_id_number=student_id)
#         msg = (
#             f"👤 FISH: {student.full_name}\n"
#             f"🏛 OTM: {student.university1.name if student.university1 else '-'}\n"
#             f"🏢 Fakultet: {student.faculty.name if student.faculty else '-'}\n"
#             f"📚 Mutaxassislik: {student.specialty.name if student.specialty else '-'}\n"
#             f"🎓 Kurs: {student.level.name if student.level else '-'}\n"
#             f"🆔 Hemis ID: {student.student_id_number}"
#         )
#         await update.message.reply_text(msg)
#     except Student.DoesNotExist:
#         await update.message.reply_text("❌ Talaba topilmadi.")

# async def run():
#     app = ApplicationBuilder().token(TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_id))
#     await app.run_polling()

# def start_bot():
#     asyncio.run(run())

import os
import django
from core.settings import DATABASES
from apps.models import TelegramUser
from telegram import Update
from telegram.ext import Updater, ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext



def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user.id
    try:
        student = TelegramUser.objects.get(telegram_id=user)
        update.message.reply_text(f"Salom {student.full_name}! Hemis ID raqamingizni yuboring:")
    except TelegramUser.DoesNotExist:
        new_user = TelegramUser(telegram_id=user, full_name=update.effective_user.full_name)
        new_user.save()
        update.message.reply_text("Salom! Hemis ID raqamingizni yuboring:")



def main() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    token = "8385707411:AAERO_nVYkVU6Y_3QOjN-ilgWP6c-jV16zQ"
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()