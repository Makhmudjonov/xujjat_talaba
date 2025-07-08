from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminLoginAPIView,
    AdminUserListAPIView,
    ApplicationItemViewSet,
    ApplicationListAPIView,
    ApplicationRetrieveView,
    DirectionViewSet,
    FinishTestAPIView,
    GetNextQuestionAPIView,
    QuizUploadAPIView,
    ScoreCreateAPIView,
    StartTestAPIView,
    StudentAccountAPIView,
    StudentApplicationTypeListAPIView,
    StudentApplicationViewSet,
    StudentLoginAPIView,
    SubmitAnswerAPIView,
    TestViewSet
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



# Barcha URL patternlari
urlpatterns = [
    # Talaba login qilish uchun API endpointi
    path('students/login/', StudentLoginAPIView.as_view(), name='student-login'),
    

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
    path("admin/score/create/", ScoreCreateAPIView.as_view(), name="score-create"),
    path("admin/applications/", ApplicationListAPIView.as_view(), name="admin-application-list"),
    path("admin/login/", AdminLoginAPIView.as_view(), name="admin-login"),

    path('admin-users/', AdminUserListAPIView.as_view(), name='admin-user-list'),

    path('admin/applications/<int:pk>/', ApplicationRetrieveView.as_view(), name='admin-application-detail'),

    #test path
    path('test/start/', StartTestAPIView.as_view(), name='start-test'),
    path('test/<int:session_id>/next/', GetNextQuestionAPIView.as_view(), name='next-question'),
    path('test/<int:session_id>/answer/', SubmitAnswerAPIView.as_view(), name='submit-answer'),
    path('test/<int:session_id>/finish/', FinishTestAPIView.as_view(), name='finish-test'),
    # path('test/<int:session_id>/result/', TestResultAPIView.as_view(), name='test-result'),

    path("admin/tests/upload/", QuizUploadAPIView.as_view(), name="quiz-upload"),
    
    # Yuqorida router orqali ro'yxatdan o'tkazilgan ViewSet'lar uchun barcha URL'larni o'z ichiga oladi
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)