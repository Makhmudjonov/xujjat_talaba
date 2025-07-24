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
    filterset_fields = ['faculty', 'level']
    search_fields = ['full_name', 'group']
    ordering_fields = ['gpaball', 'score_total', 'total_score']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Student.objects.prefetch_related(
            'applications__items__score', 'gpa_records', 'faculty', 'level'
        )

        # Faqat superuserlarga barcha malumotlar ko‘rinadi
        if not user.is_superuser:
            if user.faculty:
                queryset = queryset.filter(faculty=user.faculty)
            if user.level:
                queryset = queryset.filter(level=user.level)

        return queryset

    @swagger_auto_schema(
        operation_summary="Studentlar ballari ro‘yxati (admin filtering)",
        manual_parameters=[
            openapi.Parameter('faculty', openapi.IN_QUERY, description="Fakultet ID (ixtiyoriy, admin o‘z fakultetini ko‘radi)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('level', openapi.IN_QUERY, description="Kurs ID (ixtiyoriy, admin o‘z kursini ko‘radi)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('search', openapi.IN_QUERY, description="F.I.Sh yoki guruh bo‘yicha qidirish", type=openapi.TYPE_STRING),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Saralash: gpaball, score_total, total_score", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Sahifa raqami", type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Har bir sahifadagi elementlar soni", type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

