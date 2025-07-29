from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import requests

from apps.models import Student


class SyncStudentDataAPIView(APIView):
    permission_classes = [IsAdminUser]

    @method_decorator(csrf_exempt)
    def get(self, request):
        updated_count = 0
        not_found = []
        errors = []

        students = Student.objects.all()

        for student in students:
            if student.hemis_data_id:
                continue  # Already synced

            try:
                response = requests.get(
                    f"https://student.tma.uz/rest/v1/data/student-list?search={student.student_id_number}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data") and data["data"].get("items"):
                        hemis_id = data["data"]["items"][0]["id"]
                        student.hemis_data_id = hemis_id
                        student.save()
                        updated_count += 1
                    else:
                        not_found.append(student.student_id_number)
                else:
                    errors.append({
                        "student_id_number": student.student_id_number,
                        "status_code": response.status_code
                    })
            except Exception as e:
                errors.append({
                    "student_id_number": student.student_id_number,
                    "error": str(e)
                })

        return Response({
            "updated_count": updated_count,
            "not_found": not_found,
            "errors": errors
        })
