import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from django.db import transaction

from apps.models import GroupHemis, Speciality, Student, University


class SyncStudentDataTmaAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        students = Student.objects.filter(student_id_number__startswith='364')


        updated = 0
        skipped = 0
        errors = []

        for student in students:
            try:
                url = f"https://student.tma.uz/rest/v1/data/student-list?search={student.student_id_number}"
                res = requests.get(url, headers = {
                    "Authorization": "Bearer WKI1_kxxXtK06KdgoP8r75qlByM5G5nh"
                })
                if res.status_code != 200 or not res.json():
                    skipped += 1
                    continue

                d = res.json()[0]

                univer, _ = University.objects.get_or_create(
                    name=d["university"]
                )

                # GroupHemis
                speciality, created = Speciality.objects.update_or_create(
                    university=univer,
                    name=d['specialty']['name'],
                    defaults={
                        'code': d['specialty']['code'],
                        'hemis_id': d['specialty']['id']
                    }
                )
                
                group_hemis, created = GroupHemis.objects.update_or_create(
                    university=univer,
                    name=d['group']['name'],
                    defaults={
                        'lang': d['group']['educationLang']['name'],
                        'hemis_id': d['group']['id']
                    }
                )

                # Student update
                student.group_hemis = group_hemis
                student.specialty = speciality
                student.save()

                updated += 1

            except Exception as e:
                errors.append({
                    "student_id": student.student_id_number,
                    "error": str(e)
                })

        return Response({
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }, status=status.HTTP_200_OK)
