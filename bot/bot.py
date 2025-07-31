# bot/bot.py

import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import BadRequest
from telegram import Update

TOKEN = '8385707411:AAH1JCAJ1E0LcIKBgXgs5m-Jt73RVD5NirM'
CHANNEL_ID = "@tsmuuz"

async def check_subscription(user_id, application):
    try:
        member = await application.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_member = await check_subscription(user_id, context.application)

    if is_member:
        await update.message.reply_text("🎉 Kanalga obuna bo‘lgansiz! Xush kelibsiz!")
        # bu yerda student_id so‘rashingiz mumkin
    else:
        invite_link = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
        await update.message.reply_text(
            f"⚠️ Iltimos, quyidagi kanalga a’zo bo‘ling:\n{invite_link}",
        )

async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    print("🤖 Telegram bot ishga tushdi...")
    await app.updater.start_polling()
