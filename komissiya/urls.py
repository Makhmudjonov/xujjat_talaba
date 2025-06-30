from django.urls import path
from .views import ApplicationDetailAPIView, KomissiyaLoginAPIView, KomissiyaApplicationView, ApplicationScoreCreateAPIView

urlpatterns = [
    path('login/', KomissiyaLoginAPIView.as_view(), name='komissiya-login'),
    path('applications/', KomissiyaApplicationView.as_view(), name='komissiya-applications'),
    path('applications/<int:pk>/score/', ApplicationScoreCreateAPIView.as_view(), name='application-score-create'),
    path('applications/<int:pk>/', ApplicationDetailAPIView.as_view(), name='application-detail'),

]
