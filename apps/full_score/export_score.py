import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from rest_framework.views import APIView
from apps.gpaStudent.studentList import IsAdminUser
from apps.models import Student
from apps.serializers import StudentCombinedScoreSerializer


class ExportStudentScoreExcelView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = Student.objects.prefetch_related(
            'applications__items__score',
            'applications__items__direction',
            'gpa_records',
            'faculty',
            'level'
        ).all()

        serializer = StudentCombinedScoreSerializer(students, many=True, context={'request': request})

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Scores"

        headers = ['ID', 'Full Name', 'Faculty', 'Course', 'Group','Toifa', 'GPA Ball', 'Score Total', 'Total Score']
        ws.append(headers)

        for row in serializer.data:
            total_score_data = row.get('total_score', {})
            ws.append([
                row.get('id'),
                row.get('full_name'),
                row.get('faculty'),
                row.get('course'),
                row.get('group'),
                row.get('toifa'),
                total_score_data.get('gpa', 0),
                total_score_data.get('score_total', 0),
                total_score_data.get('total', 0),
            ])

        # Auto-width
        for col in ws.columns:
            max_length = 0
            column = col[0].column  # 1-based index
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[get_column_letter(column)].width = max_length + 4

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=student_scores.xlsx'
        wb.save(response)
        return response
