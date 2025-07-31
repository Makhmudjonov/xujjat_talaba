from django.apps import AppConfig
import threading
import sys

class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'

    def ready(self):
        if 'runserver' in sys.argv:
            from apps.management.commands import run_bot
            threading.Thread(target=run_bot.run_bot, daemon=True).start()