from rest_framework import mixins, viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import openpyxl
from django.db.models import Subquery, OuterRef, FloatField

from apps.filter.filters import StudentFilter
from apps.models import Student, GPARecord
from apps.serializers import StudentsGpaSerializer
from komissiya.views import StandardResultsSetPagination

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class AdminStudentListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = StudentsGpaSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['faculty', 'level', 'university', 'full_name']
    filterset_class = StudentFilter

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.all()

        # Admin filtratsiyasi:
        if user:
            if user.university1:
                qs = qs.filter(university1=user.university1)

            if user.faculties.exists():
                qs = qs.filter(faculty__in=user.faculties.all())

            if user.levels.exists():
                qs = qs.filter(level__in=user.levels.all())

            # Direction — ApplicationItem orqali
            if user.directions.exists():
                qs = qs.filter(applications__items__direction__in=user.directions.all())

            # Section — ApplicationItem orqali
            if user.sections.exists():
                qs = qs.filter(applications__items__section__in=user.sections.all())

            qs = qs.distinct()

        # GPA annotate
        latest_gpa_subquery = GPARecord.objects.filter(
            student=OuterRef('pk')
        ).order_by('-education_year', '-id').values('gpa')[:1]

        qs = qs.annotate(
            latest_gpa=Subquery(latest_gpa_subquery, output_field=FloatField())
        ).select_related('faculty', 'level', 'university1').prefetch_related('gpa_records')

        return qs.order_by('-latest_gpa')


    @swagger_auto_schema(
        operation_summary="Filterlangan studentlarni Excel (.xlsx) formatda yuklab olish",
        tags=["Admin - Studentlar"],
        manual_parameters=[
            openapi.Parameter("university", openapi.IN_QUERY, description="Universitet", type=openapi.TYPE_STRING),
            openapi.Parameter("level", openapi.IN_QUERY, description="Bosqich", type=openapi.TYPE_STRING),
            openapi.Parameter("faculty", openapi.IN_QUERY, description="Fakultet", type=openapi.TYPE_STRING),
            openapi.Parameter("full_name", openapi.IN_QUERY, description="FISH", type=openapi.TYPE_STRING),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="export", permission_classes=[IsAdminUser])
    def export_excel(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Studentlar"

        headers = [
            "ID", "F.I.SH.", "Shaxsiy ID", "Telefon", "Jinsi", "Universitet",
            "Fakultet", "Guruh", "Bosqich", "GPA (oxirgisi)", "Yil", "Kredit", 
            "Fanlar soni", "Qarzdor fanlar", "O‘tishi mumkinmi"
        ]
        ws.append(headers)

        for student in queryset:
            last_gpa = student.gpa_records.last() if student.gpa_records.exists() else None
            ws.append([
                student.id,
                student.full_name,
                student.student_id_number,
                student.phone or "",
                student.gender,
                student.university,
                student.faculty.name if student.faculty else "",
                student.group or "",
                student.level.name if student.level else "",
                last_gpa.gpa if last_gpa else "",
                last_gpa.education_year if last_gpa else "",
                last_gpa.credit_sum if last_gpa else "",
                last_gpa.subjects if last_gpa else "",
                last_gpa.debt_subjects if last_gpa else "",
                "Ha" if last_gpa and last_gpa.can_transfer else "Yo‘q"
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=studentlar.xlsx'
        wb.save(response)
        return response
