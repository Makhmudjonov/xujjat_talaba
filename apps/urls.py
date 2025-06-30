from django.urls import path
from .views import StudentLoginAPIView
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *




router = DefaultRouter()
# router.register(r'sections', SectionViewSet)
router.register(r'directions', DirectionViewSet)
router.register(r'applications', ApplicationViewSet)
router.register(r'application-files', ApplicationFileViewSet)
router.register(r'scores', ScoreViewSet)
router.register(r'admins', CustomAdminUserViewSet)
router.register(r'levels', LevelViewSet)


urlpatterns = [
    path('students/login/', StudentLoginAPIView.as_view(), name='student-login'),
    path('', include(router.urls)),

]