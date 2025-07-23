from rest_framework import mixins, viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, NumberFilter
from drf_yasg.utils import swagger_auto_schema
from apps.models import Student
from apps.serializers import StudentsGpaSerializer
from komissiya.views import StandardResultsSetPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import openpyxl
from drf_yasg import openapi


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


# Custom GPA filter
class StudentGpaFilter(FilterSet):
    min_gpa = NumberFilter(method='filter_by_min_gpa')

    class Meta:
        model = Student
        fields = ['faculty', 'level', 'university1']

    def filter_by_min_gpa(self, queryset, name, value):
        return queryset.filter(gpa_records__gpa__gte=value).distinct()


class AdminStudentListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Student.objects.all().prefetch_related('gpa_records', 'faculty', 'level', 'university1')
    serializer_class = StudentsGpaSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = StudentGpaFilter

    @swagger_auto_schema(
        operation_summary="Admin uchun studentlar ro'yxati",
        tags=["Admin - Studentlar"],
        manual_parameters=[
            openapi.Parameter("university1", openapi.IN_QUERY, description="Universitet ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("level", openapi.IN_QUERY, description="Bosqich ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("faculty", openapi.IN_QUERY, description="Fakultet ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter("min_gpa", openapi.IN_QUERY, description="Minimal GPA bo‘yicha filter", type=openapi.TYPE_NUMBER),
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
                student.university or "",
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
