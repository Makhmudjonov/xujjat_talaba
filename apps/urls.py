from django.urls import path, include
from apps.application.applicationExcel import ApplicationExportExcelAPIView
from apps.filter.view import ApplicationTypeStatsAPIView, FacultyStudentStatsAPIView, GPAStatsAPIView, PublicStatsAPIView, StudentGenderStatsAPIView, UniversityStudentStatsAPIView
from rest_framework.routers import DefaultRouter

from apps.gpaStudent.studentList import AdminStudentListViewSet
from .views import (
    AdminAccountAPIView,
    AdminLoginAPIView,
    AdminUserListAPIView,
    ApplicationItemViewSet,
    ApplicationListAPIView,
    ApplicationRetrieveView,
    DirectionViewSet,
    FinishTestAPIView,
    GetNextQuestionAPIView,
    LeaderboardAPIView,
    QuizUploadAPIView,
    ScoreCreateAPIView,
    StartTestAPIView,
    StudentAccountAPIView,
    StudentApplicationTypeListAPIView,
    StudentApplicationViewSet,
    StudentLoginAPIView,
    SubmitAnswerAPIView,
    TestResumeView,
    TestViewSet,
    ApplicationFileUpdateAPIView,
    UpdateToifaAPIView
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from django.conf import settings
from django.conf.urls.static import static

# DefaultRouter yordamida ViewSet'lar uchun avtomatik URL'lar yaratamiz
router = DefaultRouter()
# router.register(r'directions', DirectionViewSet)
# router.register(r'applications', ApplicationViewSet)
# router.register(r'application-files', ApplicationFileViewSet)
# router.register(r'scores', ScoreViewSet)
# router.register(r'admins', CustomAdminUserViewSet) # Admin foydalanuvchilar uchun
# router.register(r'levels', LevelViewSet)
# router.register(r'applications', ApplicationViewSet, basename='application')

router.register(r'student/application-items', ApplicationItemViewSet, basename='application-item')
# router.register(r'admin/forms', ApplicationItemAdminViewSet, basename='admin-forms')
# router.register(r'student/applications', StudentApplicationViewSet, basename='student-applications')

# router.register(r'application-items', ApplicationItemViewSet, basename='application-item')

router.register(r"directions", DirectionViewSet, basename="direction")
router.register("student/applications", StudentApplicationViewSet, basename="student-applications")
router.register(r'tests', TestViewSet, basename='test')
router.register(r'admin/students-gpa', AdminStudentListViewSet, basename='student')





# Barcha URL patternlari
urlpatterns = [
    # Talaba login qilish uchun API endpointi
    path('students/login/', StudentLoginAPIView.as_view(), name='student-login'),

    path("admin/applications/export/", ApplicationExportExcelAPIView.as_view(), name="application-export-excel"),

    path('stats/', PublicStatsAPIView.as_view(), name='public-stats'),
    path('stats/faculty-students/', FacultyStudentStatsAPIView.as_view(), name='faculty-students-stats'),
    path('stats/gpa/', GPAStatsAPIView.as_view(), name='gpa-stats'),
    path('stats/applications-by-type/', ApplicationTypeStatsAPIView.as_view(), name='application-type-stats'),
    path('stats/students-by-gender/', StudentGenderStatsAPIView.as_view(), name='students-by-gender'),
    path('stats/students-by-university/', UniversityStudentStatsAPIView.as_view(), name='students-by-university'),
    # Joriy talabaning o'z arizalarini olish uchun API endpointi
    # Bu endpoint talabalarga o'z arizalari ro'yxatini ko'rish imkonini beradi.
    # path('student-applications/', StudentApplicationAPIView.as_view(), name='student-applications'),

    # Bir nechta arizalarni va ularga tegishli fayllarni bir martada yuborish uchun yangi API endpointi
    # Bu endpoint front-enddan barcha tanlangan arizalarni bitta so'rovda qabul qiladi.
    # path('student/submit-all-applications/', SubmitMultipleApplicationsAPIView.as_view()),

    path("student/account/", StudentAccountAPIView.as_view(), name="student-account"),
    path('student/application-types/', StudentApplicationTypeListAPIView.as_view(), name='student-application-types'),
    # path('student/application-types/', StudentApplicationTypeListAPIView.as_view(), name='student-application-types'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh uchun
    #admins api 
    path("admin/score/create/", ScoreCreateAPIView.as_view(), name="score-create"),
    path("admin/applications/", ApplicationListAPIView.as_view(), name="admin-application-list"),
    path("admin/login/", AdminLoginAPIView.as_view(), name="admin-login"),

    path('admin-users/', AdminUserListAPIView.as_view(), name='admin-user-list'),
    path("admin/account/", AdminAccountAPIView.as_view(), name="admin-account"),
    path('admin/applications/<int:pk>/', ApplicationRetrieveView.as_view(), name='admin-application-detail'),

    path('admin/leaderboard/', LeaderboardAPIView.as_view(), name='leaderboard'),

    path('student/files/<int:pk>/', ApplicationFileUpdateAPIView.as_view()),

    path('students/update-toifa/', UpdateToifaAPIView.as_view(), name='update-toifa'),

    path('test/start/', StartTestAPIView.as_view(), name='start-test'),
    path('test/<int:session_id>/next/', GetNextQuestionAPIView.as_view(), name='next-question'),
    path('test/<int:session_id>/answer/', SubmitAnswerAPIView.as_view(), name='submit-answer'),
    path('test/<int:session_id>/finish/', FinishTestAPIView.as_view(), name='finish-test'),
    path('test/<int:session_id>/resume/', TestResumeView.as_view(), name='resume-test'),
    # path('test/<int:session_id>/result/', TestResultAPIView.as_view(), name='test-result'),

    path("admin/tests/upload/", QuizUploadAPIView.as_view(), name="quiz-upload"),

    
    
    # Yuqorida router orqali ro'yxatdan o'tkazilgan ViewSet'lar uchun barcha URL'larni o'z ichiga oladi
    path('', include(router.urls)),
]

