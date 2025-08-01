import logging
import sys
from django.apps import AppConfig
import threading

from bot.bot import start_bot_in_thread


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'


    def ready(self):
        start_bot_in_thread()