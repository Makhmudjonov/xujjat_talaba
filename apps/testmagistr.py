from datetime import timezone
import json
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from apps.models import Application, ApplicationFile, ApplicationItem, ApplicationType, Direction, OdobAxloqStudent, Score
from rest_framework.permissions import IsAdminUser

from apps.serializers import ApplicationTypeSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status, viewsets, permissions, generics,parsers



class MagistrStudentApplicationTypeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student

        # Odob-axloq ro‘yxatidan tekshirish
        record = OdobAxloqStudent.objects.filter(hemis_id=student.student_id_number).first()
        if record:
            return Response(
                {"detail": f"{record.sabab}"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Talabaning allaqachon topshirgan ariza turlarini olish
        applied_type_ids = Application.objects.filter(student=student) \
                                              .values_list('application_type_id', flat=True)

        # Agar mavjud bo‘lsa — faqat topshirilgan turlarni qaytaramiz
        if applied_type_ids:
            application_types = ApplicationType.objects.filter(id__in=applied_type_ids)
        else:
            application_types = ApplicationType.objects.all()

        serializer = ApplicationTypeSerializer(
            application_types,
            many=True,
            context={'student': student}
        )
        return Response(serializer.data)
    


class MagistrStudentApplicationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def list(self, request):
        # Existing list method (unchanged)
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."}, status=status.HTTP_400_BAD_REQUEST)
        # ... (rest of the list method as per your implementation)
        pass

    def create(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data

        try:
            app_type_id = int(data.get("application_type"))
            app_type = get_object_or_404(ApplicationType, id=app_type_id)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid application_type."}, status=status.HTTP_400_BAD_REQUEST)
        
        # ⏱️ Vaqtni tekshirish:
        # now = timezone.now()
        # if app_type.start_time and now < app_type.start_time:
        #     return Response(
        #         {"detail": "Ariza topshirish hali boshlanmagan."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # if app_type.end_time and now > app_type.end_time:
        #     return Response(
        #         {"detail": "Ariza topshirish muddati tugagan."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        try:
            items = json.loads(data.get("items", "[]"))
        except json.JSONDecodeError:
            return Response({"detail": "Items noto‘g‘ri formatda."}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(items, list) or not items:
            return Response({"detail": "Kamida bitta yo‘nalish bo‘lishi kerak."}, status=status.HTTP_400_BAD_REQUEST)
        
        
        for idx, it in enumerate(items):
            fayl = it.get("files")


            
            dir_id = it.get("direction")

            direc = Direction.objects.get(id=dir_id)

            if direc.type == 'toifa':
                if not fayl:
                    return Response(
                        {"detail": f"Ijtimoiy himoya reestrda turgan talabalar tasdiqlovchi hujjat yuklash shart"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            if not dir_id:
                return Response(
                    {"detail": f"{idx+1}-yo‘nalishda direction yo‘q."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if ApplicationItem.objects.filter(
                application__student=student,
                application__application_type=app_type,
                direction_id=dir_id
            ).exists():
                return Response(
                    {"detail": f"{idx+1}-yo‘nalish ({dir_id}) bo‘yicha allaqachon ariza topshirgansiz."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            first_dir = get_object_or_404(Direction, id=items[0]["direction"])
            application = Application.objects.create(
                student=student,
                application_type=app_type,
                comment=data.get("comment", ""),
                section=first_dir.section,
            )

            for i, it in enumerate(items):
                dir_obj = get_object_or_404(Direction, id=it["direction"])

                gpa_val = it.get("gpa")
                test_result_val = it.get("test_result")

                def get_gpa_score(gpa):
                    if gpa is None:
                        return 0.0  # yoki None, yoki istalgan default qiymat
                    gpa_score_map = {
                        5.0: 10.0,
                        4.9: 9.7,
                        4.8: 9.3,
                        4.7: 9.0,
                        4.6: 8.7,
                        4.5: 8.3,
                        4.4: 8.0,
                        4.3: 7.7,
                        4.2: 7.3,
                        4.1: 7.0,
                        4.0: 6.7,
                        3.9: 6.3,
                        3.8: 6.0,
                        3.7: 5.7,
                        3.6: 5.3,
                        3.5: 5.0,
                    }
                    return gpa_score_map.get(round(gpa, 1), 0.0)


                gpa_float = float(gpa_val) if gpa_val not in [None, ""] else None
                test_result_float = float(test_result_val) if test_result_val not in [None, ""] else None

                gpa_score  = get_gpa_score(gpa_float)
                

                app_item = ApplicationItem.objects.create(
                    application=application,
                    title=dir_obj.name,
                    direction=dir_obj,
                    student_comment=it.get("student_comment", ""),
                    gpa=gpa_float,
                    test_result=test_result_float,
                    gpa_score=gpa_score,
                )

                for j, f in enumerate(it.get("files", [])):
                    upload = request.FILES.get(f"files_{i}_{j}")
                    if upload:
                        ApplicationFile.objects.create(
                            item=app_item,
                            file=upload,
                            section_id=f.get("section"),
                            comment=f.get("comment", "")
                        )

                if dir_obj.type == "score" and gpa_float is not None:
                    Score.objects.create(item=app_item, reviewer=request.user, value=gpa_float)
                elif dir_obj.type == "test" and test_result_float is not None:
                    Score.objects.create(item=app_item, reviewer=request.user, value=test_result_float)

        return Response(
            {"detail": "Ariza muvaffaqiyatli yaratildi."},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["put", "patch"], url_path="update-item")
    def update_item(self, request, pk=None):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            app_item = ApplicationItem.objects.select_related('application').get(
                id=pk, application__student=student
            )
        except ApplicationItem.DoesNotExist:
            return Response({"detail": "Ariza topilmadi yoki sizga tegishli emas."}, status=status.HTTP_404_NOT_FOUND)
        

        # update_item metodida app_item dan application_type ni oling
         # 🔒 Ariza topshirish muddati tekshiruvi
        if not app_item.application.application_type.is_active():
            return Response({"error": "Ariza topshirish muddati tugagan"}, status=status.HTTP_403_FORBIDDEN)

        student_comment = request.data.get("student_comment", "")
        app_item.student_comment = student_comment
        app_item.save()

        try:
            files_data = json.loads(request.data.get("files", "[]"))
        except json.JSONDecodeError:
            return Response({"detail": "Fayl ro‘yxati noto‘g‘ri formatda."}, status=status.HTTP_400_BAD_REQUEST)

        for j, file_info in enumerate(files_data):
            upload = request.FILES.get(f"files_{pk}_{j}")
            if upload:
                ApplicationFile.objects.create(
                    item=app_item,
                    file=upload,
                    section_id=file_info.get("section"),
                    comment=file_info.get("comment", "")
                )

        return Response({"detail": "Ma’lumotlar yangilandi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="files")
    def upload_file(self, request, pk=None):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            app_item = ApplicationItem.objects.select_related('application').get(
                id=pk, application__student=student
            )
        except ApplicationItem.DoesNotExist:
            return Response({"detail": "Ariza topilmadi yoki sizga tegishli emas."}, status=status.HTTP_404_NOT_FOUND)
        
         # 🔒 Ariza topshirish muddati tekshiruvi
        if not app_item.application.application_type.is_active():
            return Response({"error": "Ariza topshirish muddati tugagan"}, status=status.HTTP_403_FORBIDDEN)

        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Fayl yuklanmadi."}, status=status.HTTP_400_BAD_REQUEST)

        comment = request.data.get("comment", "")

        ApplicationFile.objects.create(
            item=app_item,
            file=upload,
            comment=comment,
        )

        return Response({"detail": "Fayl muvaffaqiyatli yuklandi."}, status=status.HTTP_201_CREATED)