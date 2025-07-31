from django.apps import AppConfig
import threading

class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'

    def ready(self):
        import sys
        if 'runserver' not in sys.argv:
            return

        from apps.management.commands import run_bot  # bot.py faylingiz
        threading.Thread(target=run_bot.run, daemon=True).start()