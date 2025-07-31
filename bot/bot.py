# bot/bot.py
import os
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
from django.core.wsgi import get_wsgi_application
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xujjat_talaba.settings')
django.setup()

from apps.models import Student, Application, ApplicationItem, TestSession

TELEGRAM_TOKEN = "8385707411:AAEeDTBEBrm3bv6Hi1zHoIvJAOLZFVVgTIQ"
CHANNEL_USERNAME = "@TSMUUZ"

user_verified = set()  # Tasdiqlangan foydalanuvchilarni saqlash

def get_gpa_score(gpa):
    gpa_score_map = {
        5.0: 10.0, 4.9: 9.7, 4.8: 9.3, 4.7: 9.0,
        4.6: 8.7, 4.5: 8.3, 4.4: 8.0, 4.3: 7.7,
        4.2: 7.3, 4.1: 7.0, 4.0: 6.7, 3.9: 6.3,
        3.8: 6.0, 3.7: 5.7, 3.6: 5.3, 3.5: 5.0
    }
    return gpa_score_map.get(round(gpa, 2), 0.0)

def start(update, context):
    user_id = update.effective_user.id

    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            update.message.reply_text("✅ Botdan foydalanishingiz mumkin.\n\nIltimos, HEMIS ID raqamingizni yuboring:")
            user_verified.add(user_id)
        else:
            raise Exception("Not member")
    except:
        invite_link = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        update.message.reply_text(
            f"❗ Botdan foydalanish uchun kanalga a’zo bo‘ling:\n👉 {invite_link}",
            disable_web_page_preview=True
        )

def handle_hemis(update, context):
    user_id = update.effective_user.id
    if user_id not in user_verified:
        update.message.reply_text("❗ Iltimos, avval /start buyrug‘ini yuboring va kanalga a’zo ekanligingizni tasdiqlang.")
        return

    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("❗ Noto‘g‘ri ID. Iltimos, faqat raqamli HEMIS ID yuboring.")
        return

    hemis_id = text
    student = Student.objects.filter(student_id_number=hemis_id).first()
    if not student:
        update.message.reply_text("❌ Bunday HEMIS ID topilmadi.")
        return

    application = Application.objects.filter(student=student).prefetch_related("items__direction", "items__score").first()
    if not application:
        update.message.reply_text("❌ Siz hali ariza topshirmagansiz.")
        return

    msg = [f"📄 Talaba: {student.full_name}", f"📘 Ariza turi: {application.application_type}"]
    total_score = 0

    for item in application.items.all():
        if not item.direction:
            continue
        direction = item.direction.name
        dir_lc = direction.lower()

        if dir_lc == "kitobxonlik madaniyati":
            test = TestSession.objects.filter(student=student).first()
            if test:
                score = round(test.score * 0.2, 2)
                msg.append(f"📚 {direction}: {score} (test)")
                total_score += score
            else:
                msg.append(f"📚 {direction}: Mavjud emas")
        elif dir_lc == "talabaning akademik o‘zlashtirishi":
            gpa_score = get_gpa_score(student.gpa if student.gpa else 0)
            msg.append(f"📊 {direction}: {gpa_score} (GPA)")
            total_score += gpa_score
        else:
            score = item.score.value if item.score else 0
            msg.append(f"📝 {direction}: {score}")
            total_score += score

    msg.append(f"\n🔢 Jami ball: {round(total_score, 2)}")
    msg.append(f"⭐ Jami ball * 0.2 = {round(total_score * 0.2, 2)}")

    update.message.reply_text("\n".join(msg))

def run_bot():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_hemis))

    print("Telegram bot ishga tushdi...")
    updater.start_polling()

    while True:
        time.sleep(10)
