# apps/views.py
from datetime import datetime
import json
from django.forms import ValidationError
import requests

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_date

from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .models import (
    ApplicationItem, ApplicationType, Faculty, Level, Student, ContractInfo, GPARecord,
    Section, Direction, Application, ApplicationFile, Score, CustomAdminUser
)
from .serializers import (
    ApplicationItemAdminSerializer, ApplicationItemSerializer, ApplicationTypeSerializer, StudentAccountSerializer, StudentLoginSerializer, LevelSerializer, DirectionWithApplicationSerializer,
    ApplicationCreateSerializer, DirectionSerializer, ApplicationSerializer,
    ApplicationFileSerializer, ScoreSerializer, CustomAdminUserSerializer, SubmitMultipleApplicationsSerializer
)
from .permissions import (
    IsStudentAndOwnerOrReadOnlyPending,
    IsDirectionReviewerOrReadOnly,
)
from .utils import get_tokens_for_student


User = get_user_model()  # faqat bir marta


# ────────────────────────────────────────────────────────────
#  STUDENT LOGIN
# ────────────────────────────────────────────────────────────
class StudentLoginAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=StudentLoginSerializer,
        operation_description="HEMIS orqali student login qilish",
        responses={
            200: openapi.Response(
                description="Login successful",
                examples={
                    "application/json": {
                        "student_id": 1,
                        "full_name": "ISMI FAMILIYASI",
                        "token": {
                            "access": "access_token",
                            "refresh": "refresh_token"
                        }
                    }
                },
            )
        },
    )
    def post(self, request):
        ser = StudentLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login, password = ser.validated_data.values()

        # HEMIS logini
        auth_r = requests.post(
            "https://student.tma.uz/rest/v1/auth/login",
            json={"login": login, "password": password},
            headers={"accept": "application/json"},
            timeout=15,
        )
        if auth_r.status_code != 200:
            return Response({"detail": "Login yoki parol noto‘g‘ri"}, 401)

        hemis_token = auth_r.json()["data"]["token"]

        # Profil
        me_r = requests.get(
            "https://student.tma.uz/rest/v1/account/me",
            headers={"Authorization": f"Bearer {hemis_token}"},
            timeout=15,
        )
        if me_r.status_code != 200:
            return Response({"detail": "Profilni olishda xatolik"}, 400)

        d = me_r.json()["data"]

        try:
            with transaction.atomic():
                User = get_user_model()
                user, created = User.objects.get_or_create(
                    username=d["student_id_number"],
                    defaults={"first_name": d["full_name"], "role": "student"}
                )
                if created:
                    user.set_unusable_password()
                    user.save()

                faculty, _ = Faculty.objects.get_or_create(
                    hemis_id=d["faculty"]["id"],
                    defaults={"name": d["faculty"]["name"], "code": d["faculty"]["code"]},
                )

                level, _ = Level.objects.get_or_create(
                    code=d["level"]["code"],
                    defaults={"name": d["level"]["name"]},
                )

                student, _ = Student.objects.get_or_create(
                    user=user,
                    defaults={"student_id_number": d["student_id_number"]}
                )

                student.user = user
                student.full_name = d["full_name"]
                student.short_name = d.get("short_name")
                student.email = d.get("email")
                student.phone = d.get("phone")
                student.image = d.get("image")
                student.gender = d["gender"]["name"]
                student.birth_date = datetime.fromtimestamp(d["birth_date"]).date()
                student.address = d.get("address") or ""
                student.university = d.get("university")
                student.faculty = faculty
                student.group = d["group"]["name"]
                student.level = level
                student.save()

        except Exception as exc:
            return Response({"detail": str(exc)}, 500)

        jwt = get_tokens_for_student(user)
        return Response(
            {
                "student_id": student.id,
                "full_name": student.full_name,
                "token": jwt,
                "role": user.role,
            },
            200,
        )


class StudentAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba ma'lumotlari topilmadi"}, status=404)

        serializer = StudentAccountSerializer(student)
        return Response(serializer.data)
    
class ApplicationItemViewSet(viewsets.ModelViewSet):
    queryset = ApplicationItem.objects.all()
    serializer_class = ApplicationItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            return ApplicationItem.objects.filter(application__student__user=user)
        return ApplicationItem.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        student = getattr(user, 'student', None)
        if not student:
            raise ValidationError("Faqat studentlar ariza topshirishi mumkin.")

        direction = serializer.validated_data.get('direction')
        section = direction.section if direction else None

        application_type_id = self.request.data.get('application_type_id')
        if not application_type_id:
            raise ValidationError("application_type_id talab qilinadi.")

        application, created = Application.objects.get_or_create(
            student=student,
            application_type_id=application_type_id,
            defaults={'status': 'pending', 'section': section}
        )

        serializer.save(application=application, section=section)


class StudentApplicationTypeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student
        # Grab IDs of types this student has already applied to
        applied_type_ids = Application.objects.filter(student=student) \
                                              .values_list('application_type_id', flat=True)

        if applied_type_ids:
            # Return only those types they've applied for
            application_types = ApplicationType.objects.filter(id__in=applied_type_ids)
        else:
            # Return all types if none applied yet
            application_types = ApplicationType.objects.all()

        serializer = ApplicationTypeSerializer(
            application_types,
            many=True,
            context={'student': student}
        )
        return Response(serializer.data)

    
class ApplicationItemViewSet(viewsets.ModelViewSet):
    queryset = ApplicationItem.objects.all()
    serializer_class = ApplicationItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'student'):
            return ApplicationItem.objects.filter(application__student__user=user)
        return ApplicationItem.objects.none()

    def perform_create(self, serializer):
        student = self.request.user.student
        direction = serializer.validated_data.get('direction')
        section = direction.section if direction else None

        application_type_id = self.request.data.get('application_type_id')
        if not application_type_id:
            raise ValidationError("application_type_id talab qilinadi.")

        # Application yaratish yoki olish
        application, created = Application.objects.get_or_create(
            student=student,
            application_type_id=application_type_id,
            defaults={'status': 'pending', 'section': section}
        )

        serializer.save(application=application, section=section)

class DirectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = DirectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Direction.objects.select_related("section").all()
        user = self.request.user
        student = getattr(user, 'student', None)
        app_type_id = self.request.query_params.get("application_type_id")

        if student and app_type_id:
            # Ushbu turdagi arizalarda allaqachon qo‘shilgan yo‘nalishlarni olish
            applied_dirs = ApplicationItem.objects.filter(
                application__student=student,
                application__application_type_id=app_type_id
            ).values_list('direction_id', flat=True)
            # Ularni siyosatdan chiqaramiz
            qs = qs.exclude(id__in=applied_dirs)

        return qs.order_by('section__name', 'name')
    
class StudentApplicationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes    = [MultiPartParser, FormParser]

    def list(self, request):
        student = request.user.student
        qs = Application.objects.filter(student=student)
        serializer = ApplicationSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."},
                            status=status.HTTP_400_BAD_REQUEST)

        data = request.data

        # 1) application_type
        try:
            app_type_id = int(data.get("application_type"))
            app_type = get_object_or_404(ApplicationType, id=app_type_id)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid application_type."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 2) parse items JSON
        try:
            items = json.loads(data.get("items", "[]"))
        except json.JSONDecodeError:
            return Response({"detail": "Items noto‘g‘ri formatda."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(items, list) or not items:
            return Response({"detail": "Kamida bitta yo‘nalish bo‘lishi kerak."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 3) Prevent duplicate **direction** within this type
        for idx, it in enumerate(items):
            dir_id = it.get("direction")
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

        # 4) Create atomically
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
                app_item = ApplicationItem.objects.create(
                    application=application,
                    title=dir_obj.name,
                    direction=dir_obj,
                    student_comment=it.get("student_comment", "")
                )
                for j, f in enumerate(it.get("files", [])):
                    upload = request.FILES.get(f"files_{i}_{j}")
                    if upload:
                        ApplicationFile.objects.create(
                            application=application,
                            file=upload,
                            section_id=f.get("section"),
                            comment=f.get("comment", "")
                        )

        return Response(
            {"detail": "Ariza muvaffaqiyatli yaratildi."},
            status=status.HTTP_201_CREATED
        )
