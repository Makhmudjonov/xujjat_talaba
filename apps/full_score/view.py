from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, F, FloatField, ExpressionWrapper, Prefetch

from apps.models import Student, GPARecord, Score, ApplicationItem
from apps.serializers import StudentCombinedScoreSerializer
from .pagination import StandardResultsSetPagination


class StudentScoreView(ListAPIView):
    serializer_class = StudentCombinedScoreSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['faculty', 'level']  # filter by faculty/course
    search_fields = ['full_name', 'group']
    ordering_fields = ['gpaball', 'score_total', 'total_score']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Student.objects.select_related(
            'faculty', 'level'
        ).prefetch_related(
            Prefetch('gpa_records'),
            Prefetch(
                'applications__items__score',
                queryset=Score.objects.select_related('item')
            ),
            Prefetch(
                'applications__items',
                queryset=ApplicationItem.objects.select_related('direction')
            )
        )
