from django.contrib import admin
from django.db.models import Count

from apps.models import Application

class DuplicateApplicationFilter(admin.SimpleListFilter):
    title = "2+ Application qilgan studentlar"
    parameter_name = "duplicate_apps"

    def lookups(self, request, model_admin):
        return (
            ('yes', '2 yoki undan ortiq ariza topshirganlar'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            # Har bir student uchun application sonini hisoblaymiz
            students_with_multiple_apps = (
                Application.objects.values('student')
                .annotate(app_count=Count('id'))
                .filter(app_count__gt=1)
                .values_list('student', flat=True)
            )
            return queryset.filter(student__in=students_with_multiple_apps)
        return queryset
