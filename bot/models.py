from django.db import models

class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True)  # Telegram user_id
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    is_member = models.BooleanField(default=False)  # Kanalga a'zo bo'lganmi
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name or ''} @{self.username or ''}"
