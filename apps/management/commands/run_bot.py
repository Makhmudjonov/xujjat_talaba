# apps/management/commands/run_bot.py

import asyncio
from django.core.management.base import BaseCommand

from bot.bot import run_bot

class Command(BaseCommand):
    help = 'Telegram botni ishga tushuradi'

    def handle(self, *args, **kwargs):
        try:
            asyncio.run(run_bot())
        except RuntimeError as e:
            # Event loop allaqachon ishlayapti bo‘lsa:
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
            loop.run_forever()
