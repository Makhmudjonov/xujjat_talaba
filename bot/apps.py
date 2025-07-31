import sys
import threading
import asyncio
from django.apps import AppConfig

class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    def ready(self):
        if 'runserver' in sys.argv:
            from bot.bot import run_bot

            def start():
                asyncio.run(run_bot())

            threading.Thread(target=start, daemon=True).start()
