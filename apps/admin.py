from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin # Import UserAdmin directly

from apps.models import (
    Answer, Application, ApplicationFile, ApplicationItem, ApplicationType, ContractInfo, CustomAdminUser, Direction, Faculty,
    GPARecord, Level, OdobAxloqStudent, Option, Question, Score, Section, SpecialApplicationStudent, Student, Test, TestSession, University, # Make sure CustomAdminUser is imported
)

@admin.register(University)
class UniversityAdmin(SimpleHistoryAdmin):
    list_display = ('name',)

@admin.register(Student)
class StudentAdmin(SimpleHistoryAdmin):
    list_display = (
        'full_name',
        'student_id_number',
        'email',
        'phone',
        'faculty',
        'group',
        'level'
    )
    list_filter = ('faculty', 'level', 'gender', 'university')
    search_fields = ('full_name', 'student_id_number', 'email', 'phone')
    readonly_fields = ('student_id_number', 'full_name', 'email', 'phone')

 
@admin.register(Faculty)
class FacultyAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(GPARecord)
class GPARecordAdmin(SimpleHistoryAdmin):
    list_display = ("student", "education_year", "level", "gpa", "credit_sum", "subjects", "debt_subjects")
    list_filter = ("education_year", "level", "can_transfer")
    search_fields = ("student__full_name",)

@admin.register(ContractInfo)
class ContractInfoAdmin(SimpleHistoryAdmin):
    list_display = ("student", "contract_number", "edu_year", "contract_sum", "debit", "credit")
    search_fields = ("student__full_name", "contract_number")

# Register your CustomAdminUser with its custom admin class
# Use @admin.register(CustomAdminUser) or admin.site.register(CustomAdminUser, CustomAdminUserAdmin)
# Do NOT use @admin.register(User)
# @admin.register(CustomAdminUser) # <--- Corrected this line
# class CustomAdminUserAdmin(UserAdmin): # <--- Inherit from UserAdmin directly
#     # These are default UserAdmin fields; you can customize them.
#     # If you have custom fields in CustomAdminUser, you'll need to add them here.
#     fieldsets = UserAdmin.fieldsets + (
#         ('Custom Fields', {'fields': ('sections', 'directions', 'faculties', 'levels', 'limit_by_course', 'allow_all_students')}),
#     )
#     add_fieldsets = UserAdmin.add_fieldsets + (
#         ('Custom Fields', {'fields': ('sections', 'directions', 'faculties', 'levels', 'limit_by_course', 'allow_all_students')}),
#     )
#     list_display = UserAdmin.list_display + ('limit_by_course', 'allow_all_students') # Add custom fields to list display
#     filter_horizontal = ('groups', 'user_permissions', 'sections', 'directions', 'faculties', 'levels') # Make many-to-many fields easier to manage


admin.site.register(Section)
admin.site.register(Direction)
# admin.site.register(Application, SimpleHistoryAdmin)


@admin.register(Score)
class ScoreAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'get_student_full_name', 'get_direction', 'value', 'reviewer', 'scored_at')
    search_fields = ('item__application__student__full_name',)
    list_filter = (
        'scored_at',
        'item__direction',  # ✅ Direction bo‘yicha filter to‘g‘rilandi
    )

    def get_student_full_name(self, obj):
        return obj.item.application.student.full_name
    get_student_full_name.short_description = "Talaba"

    def get_direction(self, obj):
        return obj.item.direction.name if obj.item.direction else "-"
    get_direction.short_description = "Yo‘nalish"



    # def get_section(self, obj):
    #     direction = obj.item.application.direction
    #     return direction.section.name if direction and direction.section else "-"
    # get_section.short_description = "Bo‘lim (Section)"

@admin.register(Application)
class ApplicationAdmin(SimpleHistoryAdmin):
    list_display = ('student', 'application_type', 'status', 'submitted_at')
    list_filter = ('status', 'application_type', 'section','student__university', 'student__university1', 'student__faculty')
    search_fields = ('student__full_name', 'student__student_id_number', 'student__university', 'student__university1', 'student__faculty')  # misol uchun

@admin.register(ApplicationType)
class ApplicationTypeAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'min_gpa')
    # list_filter = ('access_type',)


@admin.register(SpecialApplicationStudent)
class SpecialApplicationStudentAdmin(SimpleHistoryAdmin):
    list_display = ('hemis_id', 'application_type', 'student')
    search_fields = ('hemis_id',)
    list_filter = ('application_type',)

# @admin.register(Student)
# class StudentAdmin(SimpleHistoryAdmin):
#     list_display = ('hemis_id', 'last_name', 'first_name', 'gpa')
#     search_fields = ('hemis_id', 'last_name')


@admin.register(ApplicationItem)
class ApplicationItemAdmin(SimpleHistoryAdmin):
    list_display = ("id", "get_student_name", "get_level", "direction")
    
    def get_student_name(self, obj):
        return obj.application.student.full_name
    get_student_name.short_description = "Talaba"

    def get_level(self, obj):
        return obj.application.student.level.name
    get_level.short_description = "Bosqich (Level)"

    


@admin.register(CustomAdminUser)
class CustomAdminUserAdmin(UserAdmin):
    model = CustomAdminUser
    list_display = ("username", "email", "role", "is_active", "is_staff", "can_score")
    list_filter = ("role", "is_active", "is_staff", "can_score")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Shaxsiy ma'lumotlar", {"fields": ("first_name", "last_name", "email")}),
        ("Ruxsatlar", {
            "fields": (
                "is_active", "is_staff", "is_superuser",
                "groups", "user_permissions",
            )
        }),
        ("Admin rollari", {
            "fields": (
                "role", 'full_name', "sections", "faculties", "directions", "levels",
                "limit_by_course", "allow_all_students", "can_score", 'university1', 
            )
        }),
        ("Muhim sanalar", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "password1", "password2", "email",
                "role", "is_staff", "is_active",
                "sections", "faculties", "directions", "levels",
                "limit_by_course", "allow_all_students", "can_score", 'university1' # ✅ Qo‘shildi
            ),
        }),
    )



@admin.register(ApplicationFile)
class ApplicationFileAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'get_application', 'comment')

    def get_application(self, obj):
        return obj.item.application
    get_application.short_description = "Application"




#test admin
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2


@admin.register(Answer)
class AnswerAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'question', 'is_correct')
    list_filter = ('is_correct', 'session')

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4  # savolga default 4 javob varianti ko‘rsatiladi

class QuestionAdmin(SimpleHistoryAdmin):
    inlines = [OptionInline]
    list_display = ('text',)

admin.site.register(Question, QuestionAdmin)

@admin.register(Option)
class OptionAdmin(SimpleHistoryAdmin):
    list_display = ('question', 'label', 'text', 'is_correct')
    list_filter = ('is_correct',)


@admin.register(Test)
class TestAdmin(SimpleHistoryAdmin):
    list_display = ("title", "question_count", "time_limit", "start_time", "created_at")  # 🆕 start_time qo‘shildi
    search_fields = ("title",)
    list_filter = ("created_at", "levels", "start_time")  # 🆕
    filter_horizontal = ("levels",)

    fieldsets = (
        (None, {
            "fields": ("title", "question_count", "time_limit", "start_time", "levels")  # 🆕
        }),
    )


@admin.register(TestSession)
class TestSessionAdmin(SimpleHistoryAdmin):
    list_display = ("id", "student", "test", "started_at", "finished_at", "score")
    list_filter = ("test", "student")
    search_fields = ("student__full_name", "student__student_id_number", "test__title")
    readonly_fields = ("started_at", "finished_at", "score", "correct_answers", "total_questions")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "test")


@admin.register(OdobAxloqStudent)
class OdobAxloqStudentAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'hemis_id', 'sabab')
    search_fields = ('hemis_id',)
    list_filter = ('sabab',)



@admin.register(Level)
class LevelAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'code', 'name')
    search_fields = ('code', 'name')