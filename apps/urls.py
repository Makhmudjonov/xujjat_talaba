from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ApplicationItemViewSet,
    DirectionViewSet,
    StudentAccountAPIView,
    StudentApplicationTypeListAPIView,
    StudentApplicationViewSet,
    StudentLoginAPIView
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

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

    
    # Yuqorida router orqali ro'yxatdan o'tkazilgan ViewSet'lar uchun barcha URL'larni o'z ichiga oladi
    path('', include(router.urls)),
]