import time
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.db import transaction

from apps.models import GroupHemis, Speciality, Student, University


class SyncStudentDataStomAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = Student.objects.filter(student_id_number__startswith='366')
        updated = 0
        skipped = 0
        errors = []

        token = "BqJegwTQCKAOldxIh8u0GsoS7IzkxmzQ"  # Tokeningizni bu yerga yozing
        headers = {
            "Authorization": f"Bearer {token}"
        }

        for idx, student in enumerate(students):
            try:
                url = f"https://student.tsdi.uz/rest/v1/data/student-list?search={student.student_id_number}"
                res = requests.get(url, headers=headers)

                if res.status_code != 200:
                    skipped += 1
                    errors.append({
                        "student_id": student.student_id_number,
                        "error": f"HTTP {res.status_code}"
                    })
                    continue

                data = res.json()
                if not data:
                    skipped += 1
                    errors.append({
                        "student_id": student.student_id_number,
                        "error": "Empty response"
                    })
                    continue

                d = data[0]  # Javoblar ro'yxatidan birinchi element

                # University yaratish yoki olish
                university, _ = University.objects.get_or_create(
                    name=d["university"]
                )

                # Speciality yaratish yoki yangilash
                specialty_data = d.get("specialty")
                if specialty_data:
                    speciality, _ = Speciality.objects.update_or_create(
                        university=university,
                        name=specialty_data.get("name", ""),
                        defaults={
                            "code": specialty_data.get("code", ""),
                            "hemis_id": specialty_data.get("id", "")
                        }
                    )
                else:
                    speciality = None

                # GroupHemis yaratish yoki yangilash
                group_data = d.get("group")
                if group_data:
                    group_hemis, _ = GroupHemis.objects.update_or_create(
                        university=university,
                        name=group_data.get("name", ""),
                        defaults={
                            "lang": group_data.get("educationLang", {}).get("name", ""),
                            "hemis_id": group_data.get("id", "")
                        }
                    )
                else:
                    group_hemis = None

                # Student modelini yangilash
                student.group_hemis = group_hemis
                student.specialty = speciality
                student.save()

                updated += 1

            except Exception as e:
                skipped += 1
                errors.append({
                    "student_id": student.student_id_number,
                    "error": str(e)
                })

            if (idx + 1) % 10 == 0:
                time.sleep(3)

        return Response({
            "updated": updated,
            "skipped": skipped,
            "errors": errors
        }, status=status.HTTP_200_OK)
