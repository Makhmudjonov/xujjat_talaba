# bot/apps.py
from django.apps import AppConfig
import threading

class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    def ready(self):
        from .bot import run_bot
        threading.Thread(target=run_bot, daemon=True).start()
