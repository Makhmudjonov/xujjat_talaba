from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.models import Student
from apps.serializers import StudentCombinedScoreSerializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from .pagination import StandardResultsSetPagination  # agar siz custom pagination class ishlatsangiz

class StudentScoreView(ListAPIView):
    serializer_class = StudentCombinedScoreSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['full_name', 'group']
    ordering_fields = ['gpaball', 'score_total', 'total_score']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user

        # Boshlang'ich queryset
        queryset = Student.objects.prefetch_related(
            'applications__items__score',
            'gpa_records',
            'faculty',
            'level'
        )

        # Faqat admin roliga tekshiruv
        if user.role in ['admin', 'dekan', 'kichik_admin']:
            if user.university1:
                queryset = queryset.filter(university=user.university1)
            if user.faculties.exists():
                queryset = queryset.filter(faculty__in=user.faculties.all())
            if user.levels.exists():
                queryset = queryset.filter(level__in=user.levels.all())

        # Superuser hammasini ko‘ra oladi
        return queryset


