from django.apps import AppConfig
import threading
import sys

class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'

    def ready(self):
        if 'runserver' in sys.argv:
            from django.core.management import call_command
            threading.Thread(target=lambda: call_command('run_bot'), daemon=True).start()