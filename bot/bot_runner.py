# bot/bot_runner.py
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .handlers import router as handler_router  # .handlers -> local import

TOKEN = "8385707411:AAGUGTpAJXGKF41D5gj-LBnRpGklVk85jIQ"
dp = Dispatcher()

async def bots():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp.include_router(handler_router)
    await dp.start_polling(bot)

def run_bot():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(bots())
