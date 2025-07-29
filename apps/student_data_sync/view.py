from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import requests

from apps.models import GPARecord, Student


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
                    f"https://student.tma.uz/rest/v1/data/student-list?search={student.student_id_number}",
                    headers={
                        "Authorization": "Bearer WKI1_kxxXtK06KdgoP8r75qlByM5G5nh",
                        "Content-Type": "application/json"
                    }
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



class SyncGPAAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        success_count = 0
        error_logs = []

        students = Student.objects.filter(student_id_number__startswith="364").exclude(hemis_data_id__isnull=True).exclude(hemis_data_id='')

        for student in students:
            try:
                url = f"https://student.tma.uz/rest/v1/data/student-gpa-list?_student={student.hemis_data_id}"
                response = requests.get(url,headers={
                        "Authorization": "Bearer WKI1_kxxXtK06KdgoP8r75qlByM5G5nh",
                        "Content-Type": "application/json"
                    })
                data = response.json()

                if data.get("data") and data["data"].get("items"):
                    for item in data["data"]["items"]:
                        # hemis_data_id = item["id"]

                        gpa_record, created = GPARecord.objects.update_or_create(
                            student=student,
                            level=item["level"]["name"],
                            defaults={
                                "hemis_data_id": item["id"],
                                "education_year": item["educationYear"]["name"],
                                "gpa": item["gpa"],
                                "credit_sum": float(item["credit_sum"]),
                                "subjects": item["subjects"],
                                "debt_subjects": item["debt_subjects"],
                                "can_transfer": item["can_transfer"],
                                "method": item["method"],
                                "created_at": datetime.fromtimestamp(item["created_at"]),
                            }
                        )


                        if created:
                            success_count += 1

                else:
                    error_logs.append(f"No GPA data for student {student.full_name} ({student.student_id_number})")

            except Exception as e:
                error_logs.append(f"Error syncing student {student.full_name} ({student.student_id_number}): {str(e)}")

        return Response({
            "message": f"{success_count} new GPA records added.",
            "errors": error_logs
        })
