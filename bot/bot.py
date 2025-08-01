import logging
import re
import aiohttp
import asyncio
import threading
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

BOT_TOKEN = '8385707411:AAGLbIQehgLqA6N210eEzL979QCBc9kAwng'
CHANNEL_ID = '@tsmuuz'

user_states = {}

logging.basicConfig(level=logging.INFO)

async def check_subscription(user_id, application) -> bool:
    try:
        member = await application.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_subscription(user.id, context.application):
        await update.message.reply_text(f"{CHANNEL_ID} kanaliga obuna bo‘ling.")
        return

    await update.message.reply_text("HEMIS ID (12 raqam) kiriting.")
    user_states[user.id] = "awaiting_hemis_id"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    if not await check_subscription(user.id, context.application):
        return

    if user_states.get(user.id) == "awaiting_hemis_id":
        if re.fullmatch(r"\d{12}", text):
            await update.message.reply_text("Ma'lumotlar olinmoqda...")
            url = f"http://localhost:8000/api/student-info/{text}/"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await update.message.reply_text(format_student_info(data), parse_mode="HTML")
                    else:
                        await update.message.reply_text("HEMIS ID topilmadi.")
            user_states.pop(user.id, None)
        else:
            await update.message.reply_text("HEMIS ID noto‘g‘ri. 12 ta raqam kiriting.")
    else:
        await update.message.reply_text("/start buyrug‘idan foydalaning.")

def format_student_info(data):
    text = f"📄 <b>{data['full_name']}</b>\n"
    text += f"🏫 {data['university']} - {data['faculty']}\n"
    text += f"📘 {data['speciality']} | {data['level']}, {data['group']}\n"
    text += f"📌 Toifa: {data['toifa']}\n\n"

    for app in data['applications']:
        text += f"📝 <b>{app['application_type']}</b> ({app['created_at'][:10]})\n"
        for item in app['items']:
            text += f"  • {item['title']}: {item['total_score']} ball\n"
        text += "\n"
    return text

def run_bot():
    async def main():
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await app.initialize()   # Important for manual startup
        await app.start()
        await app.updater.start_polling()
    
    # use create_task instead of run_until_complete if already running
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(main())
    except RuntimeError:
        # No running loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())


def start_bot_in_thread():
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
