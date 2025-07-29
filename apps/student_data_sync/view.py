from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import requests
from django.utils.timezone import make_aware


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

        problematic_ids = [
    "364241100677",
    "364241101971",
    "364241100878",
    "364241101343",
    "364241100839",
    "364241100555",
    "364241100537",
    "364241100765",
    "364241101676",
    "364241101501",
    "364241101882",
    "364241101091",
    "364241101702",
    "364241100738",
    "364241101234",
    "364241101553",
    "364241101490",
    "364241101416",
    "364241101678",
    "364241100653",
    "364241100571",
    "364241100667",
    "364241100881",
    "364241101073",
    "364241101263",
    "364241101502",
    "364241101484",
    "364241101539",
    "364241101563",
    "364241101654",
    "364241101755",
    "364241101507",
    "364241100907",
    "364241101079",
    "364241100567",
    "364241101799",
    "364241101498",
    "364241100691",
    "364241101606",
    "364241101892",
    "364241101561",
    "364241101758",
    "364241101592",
    "364241101186",
    "364241101098",
    "364241100816",
    "364241101231",
    "364241101905",
    "364241101706",
    "364241100782",
    "364241101468",
    "364241101372",
    "364241101100",
    "364241100879",
    "364241100781",
    "364241101615",
    "364241101507",  # takrorlanmoqda
    "364241100666",
    "364241100677",  # takrorlanmoqda
    "364241101912"
]



        students = Student.objects.filter(student_id_number__in=problematic_ids).exclude(hemis_data_id__isnull=True).exclude(hemis_data_id='')

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
                                "created_at": make_aware(datetime.fromtimestamp(item["created_at"]))
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
