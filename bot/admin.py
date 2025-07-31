from django.contrib import admin
from .models import TelegramUser

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "username", "first_name", "is_member", "joined_at")
    search_fields = ("username", "first_name", "last_name", "user_id")
