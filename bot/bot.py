import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import BadRequest
from telegram import Update




TOKEN = '8385707411:AAFFDH_7ixyPRQ0zLKsw_uG7M8_osxGQW0I'
CHANNEL_ID = "@tsmuuz"

async def check_subscription(user_id, application):
    try:
        member = await application.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from apps.models import TelegramUser
    user = update.effective_user
    user_id = user.id
    is_member = await check_subscription(user_id, context.application)

    # Bazaga yozish yoki yangilash
    TelegramUser.objects.update_or_create(
        user_id=user_id,
        defaults={
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_member": is_member,
        }
    )

    if is_member:
        await update.message.reply_text("🎉 Kanalga obuna bo‘lgansiz! Xush kelibsiz!")
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
    asyncio.create_task(app.updater.start_polling())



