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
        students = Student.objects.prefetch_related('applications__items__score', 'gpa_records', 'faculty', 'level')
        serializer = StudentCombinedScoreSerializer(students, many=True, context={'request': request})

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Student Scores"

        headers = ['ID', 'Full Name', 'Faculty', 'Course', 'Group', 'GPA Ball', 'Score Total', 'Total Score']
        ws.append(headers)

        for row in serializer.data:
            ws.append([
                row['id'],
                row['full_name'],
                row['faculty'],
                row['course'],
                row['group'],
                row['gpaball'],
                row['score_total'],
                row['total_score'],
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=student_scores.xlsx'
        wb.save(response)
        return response
