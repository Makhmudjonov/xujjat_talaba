import openpyxl
from openpyxl.utils import get_column_letter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from io import BytesIO

class ApplicationExportExcelAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        user = self.request.user

        qs = Application.objects.prefetch_related(
            "items__direction__section",
            "items__files",
            "items__score",
            "student__faculty",
            "student__level",
        ).select_related("application_type", "student")

        if user.university1:
            qs = qs.filter(student__university1=user.university1)

        if user.faculties.exists():
            qs = qs.filter(student__faculty__in=user.faculties.all())

        if user.levels.exists():
            qs = qs.filter(student__level__in=user.levels.all())

        if user.directions.exists():
            qs = qs.filter(items__direction__in=user.directions.all())

        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        student = self.request.query_params.get("student")
        if student:
            qs = qs.filter(student__full_name__icontains=student)

        return qs.distinct()

    @swagger_auto_schema(
        operation_summary="Application ro'yxatini filterga qarab Excel formatda yuklab olish",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, description="Status (pending, accepted, rejected)", type=openapi.TYPE_STRING),
            openapi.Parameter("student", openapi.IN_QUERY, description="Talaba ismi bo‘yicha qidiruv", type=openapi.TYPE_STRING),
        ],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Applications"

        headers = [
            "ID", "Student", "Faculty", "Level", "Application Type", "Status",
            "Directions", "Score", "Comment"
        ]
        ws.append(headers)

        for app in queryset:
            directions = ", ".join(item.direction.name for item in app.items.all())
            scores = ", ".join(str(item.score.value if item.score else "-") for item in app.items.all())
            comments = ", ".join(item.reviewer_comment or "" for item in app.items.all())

            ws.append([
                app.id,
                app.student.full_name,
                app.student.faculty.name if app.student.faculty else "",
                app.student.level.name if app.student.level else "",
                app.application_type.title,
                app.status,
                directions,
                scores,
                comments
            ])

        # Auto-width
        for column_cells in ws.columns:
            length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
            ws.column_dimensions[get_column_letter(column_cells[0].column)].width = length + 3

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=applications.xlsx'
        return response
