from django.contrib import admin

from komissiya.models import KomissiyaMember

@admin.register(KomissiyaMember)
class KomissiyaMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'faculty', 'direction', 'section', 'course')
    list_filter = ('role', 'faculty', 'direction', 'section', 'course')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

