import sys
from django.apps import AppConfig
import threading


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'

    def ready(self):
        from .bot_runner import run_bot
        if 'runserver' in sys.argv:  # faqat runserver bo‘lsa
            thread = threading.Thread(target=run_bot, name="TelegramBot")
            thread.daemon = True
            thread.start()