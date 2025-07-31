from django.apps import AppConfig
import threading

class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'

    def ready(self):
        import sys
        if 'runserver' not in sys.argv:
            return

        from . import bot  # bot.py faylingiz
        threading.Thread(target=bot.run, daemon=True).start()