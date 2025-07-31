# import asyncio
# from telegram.ext import ApplicationBuilder, CommandHandler
# from telegram.error import BadRequest

# TOKEN = '8385707411:AAFFDH_7ixyPRQ0zLKsw_uG7M8_osxGQW0I'
# CHANNEL_ID = "@tsmuuz"

# async def check_subscription(user_id, application):
#     try:
#         member = await application.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
#         return member.status in ["member", "administrator", "creator"]
#     except BadRequest:
#         return False

# async def run_bot():
#     app = ApplicationBuilder().token(TOKEN).build()
#     # Qo'shimcha handlerlar bu yerda qo'shiladi
#     await app.initialize()
#     await app.start()
#     asyncio.create_task(app.updater.start_polling())


