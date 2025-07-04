from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin # Import UserAdmin directly

from apps.models import (
    Application, ApplicationItem, ApplicationType, ContractInfo, CustomAdminUser, Direction, Faculty,
    GPARecord, Score, Section, SpecialApplicationStudent, Student, # Make sure CustomAdminUser is imported
)

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

# Register your CustomAdminUser with its custom admin class
# Use @admin.register(CustomAdminUser) or admin.site.register(CustomAdminUser, CustomAdminUserAdmin)
# Do NOT use @admin.register(User)
@admin.register(CustomAdminUser) # <--- Corrected this line
class CustomAdminUserAdmin(UserAdmin): # <--- Inherit from UserAdmin directly
    # These are default UserAdmin fields; you can customize them.
    # If you have custom fields in CustomAdminUser, you'll need to add them here.
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('sections', 'directions', 'faculties', 'levels', 'limit_by_course', 'allow_all_students')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('sections', 'directions', 'faculties', 'levels', 'limit_by_course', 'allow_all_students')}),
    )
    list_display = UserAdmin.list_display + ('limit_by_course', 'allow_all_students') # Add custom fields to list display
    filter_horizontal = ('groups', 'user_permissions', 'sections', 'directions', 'faculties', 'levels') # Make many-to-many fields easier to manage


admin.site.register(Section)
admin.site.register(Direction)
admin.site.register(Application, SimpleHistoryAdmin)
admin.site.register(Score, SimpleHistoryAdmin)

@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_gpa')
    # list_filter = ('access_type',)


@admin.register(SpecialApplicationStudent)
class SpecialApplicationStudentAdmin(admin.ModelAdmin):
    list_display = ('hemis_id', 'application_type', 'student')
    search_fields = ('hemis_id',)
    list_filter = ('application_type',)

# @admin.register(Student)
# class StudentAdmin(admin.ModelAdmin):
#     list_display = ('hemis_id', 'last_name', 'first_name', 'gpa')
#     search_fields = ('hemis_id', 'last_name')


@admin.register(ApplicationItem)
class ApplicationItemAdmin(admin.ModelAdmin):
    list_display = ("id", "get_student_name", "get_level", "direction")

    def get_student_name(self, obj):
        return obj.application.student.full_name
    get_student_name.short_description = "Talaba"

    def get_level(self, obj):
        return obj.application.student.level.name
    get_level.short_description = "Bosqich (Level)"