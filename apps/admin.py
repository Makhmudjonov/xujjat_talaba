from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin



from apps.models import Application, ContractInfo, CustomAdminUser, Direction, Faculty, GPARecord, Score, Section, Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'student_id_number',
        'email',
        'phone',
        'faculty',
        'group',
        'level',
    )
    list_filter = ('faculty', 'level', 'gender')
    search_fields = ('full_name', 'student_id_number', 'email', 'phone')
    readonly_fields = ('student_id_number', 'full_name', 'email', 'phone')


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'hemis_id')
    search_fields = ('name', 'code')

@admin.register(GPARecord)
class GPARecordAdmin(admin.ModelAdmin):
    list_display = ("student", "education_year", "level", "gpa", "credit_sum", "subjects", "debt_subjects")
    list_filter = ("education_year", "level", "can_transfer")
    search_fields = ("student__full_name",)

@admin.register(ContractInfo)
class ContractInfoAdmin(admin.ModelAdmin):
    list_display = ("student", "contract_number", "edu_year", "contract_sum", "debit", "credit")
    search_fields = ("student__full_name", "contract_number")

admin.site.register(Section)
admin.site.register(Direction)
admin.site.register(Application, SimpleHistoryAdmin)
admin.site.register(Score, SimpleHistoryAdmin)
# admin.site.register(CustomAdminUser)
admin.site.register(CustomAdminUser, UserAdmin)
