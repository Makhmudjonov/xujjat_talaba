import requests
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.models import Student

from rest_framework.permissions import IsAdminUser



class BatchUpdateSpecialtiesTmaAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        updated_students = []
        failed_students = []

        # Faqat 364 bilan boshlanuvchi student_id_number larni olish
        students = Student.objects.filter(student_id_number__startswith="364")

        for student in students:
            student_id = student.student_id_number
            url = f"https://student.tma.uz/rest/v1/data/student-list?search={student_id}"
            headers = {
                "Authorization": "Bearer WKI1_kxxXtK06KdgoP8r75qlByM5G5nh"
            }

            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Yangi format: data["data"]["items"][0]["specialty"]["name"]
                items = data.get("data", {}).get("items", [])
                if not items:
                    failed_students.append({
                        "student_id_number": student_id,
                        "reason": "API: no items"
                    })
                    continue

                specialty = items[0].get("specialty", {})
                specialty_name = specialty.get("name")

                if not specialty_name:
                    failed_students.append({
                        "student_id_number": student_id,
                        "reason": "specialty.name not found"
                    })
                    continue

                if student.specialty != specialty_name:
                    old = student.specialty
                    student.specialty = specialty_name
                    student.save()
                    updated_students.append({
                        "student_id_number": student_id,
                        "old_specialty": old,
                        "new_specialty": specialty_name
                    })

            except Exception as e:
                failed_students.append({
                    "student_id_number": student_id,
                    "reason": str(e)
                })

        return Response({
            "updated_count": len(updated_students),
            "failed_count": len(failed_students),
            "updated_students": updated_students,
            "failed_students": failed_students
        })
