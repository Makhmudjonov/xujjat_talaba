from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import logging
from apps.models import Student  # modelni to‘g‘ri import qiling

logging.basicConfig(level=logging.INFO)
CHANNEL_ID = "@tsmuuz"

class Command(BaseCommand):
    help = "Starts the Telegram bot"

    def handle(self, *args, **options):
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            chat_member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                await update.message.reply_text("Kanalga a'zo bo'ling: " + CHANNEL_ID)
                return
            await update.message.reply_text("Hemis ID raqamingizni yuboring:")

        async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
            student_id = update.message.text.strip()
            try:
                student = Student.objects.select_related("faculty", "specialty", "level", "university1").get(student_id_number=student_id)
                msg = (
                    f"👤 FISH: {student.full_name}\n"
                    f"🏛 OTM: {student.university1.name if student.university1 else '-'}\n"
                    f"🏢 Fakultet: {student.faculty.name if student.faculty else '-'}\n"
                    f"📚 Mutaxassislik: {student.specialty.name if student.specialty else '-'}\n"
                    f"🎓 Kurs: {student.level.name if student.level else '-'}\n"
                    f"🆔 Hemis ID: {student.student_id_number}"
                )
                await update.message.reply_text(msg)
            except Student.DoesNotExist:
                await update.message.reply_text("❌ Talaba topilmadi.")

        async def main():
            application = ApplicationBuilder().token("8385707411:AAERO_nVYkVU6Y_3QOjN-ilgWP6c-jV16zQ").build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_id))
            await application.run_polling()

        import asyncio
        asyncio.run(main())
