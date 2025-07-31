# apps/management/commands/run_bot.py

from django.core.management.base import BaseCommand
from apps.bot import start_bot  # bot boshlovchi funksiyangiz shu bo‘lsa

class Command(BaseCommand):
    help = 'Telegram botni ishga tushuradi'

    def handle(self, *args, **kwargs):
        start_bot()  # bu yerda botni ishga tushuruvchi funksiya bo‘lishi kerak
