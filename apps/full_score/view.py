from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.models import Student
from apps.serializers import StudentCombinedScoreSerializer

class StudentScoreView(ListAPIView):
    queryset = Student.objects.prefetch_related('applications__items__score', 'gpa_records', 'faculty', 'level')
    serializer_class = StudentCombinedScoreSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['faculty', 'level']  # filter by faculty/course
    search_fields = ['full_name', 'group']
    ordering_fields = ['gpaball', 'score_total', 'total_score']
