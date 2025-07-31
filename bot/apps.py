# bot/apps.py
import os
import asyncio
from django.apps import AppConfig
from bot.bot import run_bot

class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    # def ready(self):
    #     if os.environ.get("RUN_MAIN") != "true":
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)
    #         loop.create_task(run_bot())
    #         loop.run_forever()
