# apps/views.py
from datetime import datetime
import json
from django.forms import ValidationError
import requests

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_date
from django.core.exceptions import PermissionDenied

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.authentication import TokenAuthentication



from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.pagenation import CustomPagination

from .models import (
    ApplicationItem, ApplicationType, Faculty, Level, Student, ContractInfo, GPARecord,
    Section, Direction, Application, ApplicationFile, Score, CustomAdminUser
)
from .serializers import (
    AdminLoginSerializer, AdminUserSerializer, ApplicationDetailSerializer, ApplicationFullSerializer, ApplicationItemAdminSerializer, ApplicationItemSerializer, ApplicationTypeSerializer, ScoreCreateSerializer, StudentAccountSerializer, StudentLoginSerializer, LevelSerializer, DirectionWithApplicationSerializer,
    ApplicationCreateSerializer, DirectionSerializer, ApplicationSerializer,
    ApplicationFileSerializer, ScoreSerializer, SubmitMultipleApplicationsSerializer
)
from .permissions import (
    IsStudentAndOwnerOrReadOnlyPending,
    IsDirectionReviewerOrReadOnly,)

from rest_framework.permissions import IsAdminUser

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
        
        # 7️⃣  GPA list
            gpa_r = requests.get(
                "https://student.tma.uz/rest/v1/education/gpa-list",
                headers={"Authorization": f"Bearer {hemis_token}"},
                timeout=15,
            )
            if gpa_r.status_code == 200:
                for it in gpa_r.json().get("data", []):
                    GPARecord.objects.update_or_create(
                        student=student,
                        education_year=it["educationYear"]["name"],
                        level=it["level"]["name"],
                        defaults={
                            "gpa": it["gpa"],
                            "credit_sum": float(it["credit_sum"]),
                            "subjects": it["subjects"],
                            "debt_subjects": it["debt_subjects"],
                            "can_transfer": it["can_transfer"],
                            "method": it["method"],
                            "created_at": datetime.fromtimestamp(it["created_at"]),
                        },
                    )

            # 8️⃣  Contract
            c_r = requests.get(
                "https://student.tma.uz/rest/v1/student/contract",
                headers={"Authorization": f"Bearer {hemis_token}"},
                timeout=15,
            )
            if c_r.status_code == 200 and c_r.json().get("data"):
                cd = c_r.json()["data"]
                ContractInfo.objects.update_or_create(
                    student=student,
                    defaults={
                        "contract_number": cd["contractNumber"],
                        "contract_date": datetime.strptime(
                            cd["contractDate"], "%d.%m.%Y"
                        ).date(),
                        "edu_organization": cd["eduOrganization"],
                        "edu_speciality": cd["eduSpeciality"],
                        "edu_period": cd["eduPeriod"],
                        "edu_year": cd["eduYear"],
                        "edu_type": cd["eduType"],
                        "edu_form": cd["eduForm"],
                        "edu_course": cd["eduCourse"],
                        "contract_type": cd["eduContractType"],
                        "pdf_link": cd["pdfLink"],
                        "contract_sum": cd["eduContractSum"],
                        "gpa": cd["gpa"],
                        "debit": cd.get("debit"),
                        "credit": cd.get("credit"),
                    },
                )

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
                            item=app_item,
                            file=upload,
                            section_id=f.get("section"),
                            comment=f.get("comment", "")
                        )

        return Response(
            {"detail": "Ariza muvaffaqiyatli yaratildi."},
            status=status.HTTP_201_CREATED
        )

class NewApplicationsAPIView(generics.ListAPIView):
    """
    **Admin** yoki komissiya uchun:
    Yangi (yoki istalgan) arizalar toʻliq tarkib bilan.
    """
    serializer_class   = ApplicationFullSerializer
    permission_classes = [permissions.IsAuthenticated]  # kerak bo‘lsa IsAdminUser
    pagination_class   = None  # pagination xohlasangiz DRF’ning standard klasini qo‘ying

    def get_queryset(self):
        """
        Faqat ko‘rib chiqilmagan (‘pending’) arizalarni qaytarish.
        Agar hammasi kerak bo‘lsa, filterni o‘chirib tashlang.
        """
        return (
            Application.objects
            .filter(status=Application.STATUS_PENDING)
            .select_related("application_type", "section", "student")
            .prefetch_related(
                "items__direction",
                "items__score",
                "items__files",
            )
            .order_by("-submitted_at")
        )

    # Swagger’ga chiroyli ko‘rinishi uchun
    @swagger_auto_schema(operation_summary="Yangi kelgan arizalar ro‘yxati (to‘liq)")
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
    
class ScoreCreateAPIView(CreateAPIView):
    serializer_class = ScoreCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        # Agar foydalanuvchi faqat ko‘ruvchi bo‘lsa
        if user.role == "dekan":
            raise PermissionDenied("Sizning rolingiz faqat ko‘rish uchun mo‘ljallangan.")

        item = serializer.validated_data["item"]

        # Access tekshiruvi (section/direction/faculty asosida)
        if not user.has_access_to(item.direction):
            raise PermissionDenied("Siz bu yo‘nalishga baho qo‘yolmaysiz.")

        # Score ni saqlash
        score = serializer.save(reviewer=user)

        # Application statusini yangilash
        application = item.application
        application.status = "accepted"
        application.save()
    
    @swagger_auto_schema(
        operation_summary="Admin tomonidan ApplicationItem ga baho qo‘yish",
        request_body=ScoreCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    

class ApplicationListAPIView(ListAPIView):
    serializer_class = ApplicationFullSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user

        qs = Application.objects.prefetch_related(
            "items__direction__section",
            "items__files",
            "items__score",
            "student__faculty",
            "student__level",
        ).select_related("application_type", "student")

        if user.faculties.exists():
            qs = qs.filter(student__faculty__in=user.faculties.all())

        if user.levels.exists():
            qs = qs.filter(student__level__in=user.levels.all())

        if user.directions.exists():
            qs = qs.filter(items__direction__in=user.directions.all())

        # Agar query paramda status bo‘lsa
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        return qs.distinct()
    
    @swagger_auto_schema(
    operation_summary="Adminlar uchun applicationlar ro‘yxati",
    manual_parameters=[
        openapi.Parameter("status", openapi.IN_QUERY, description="Filter by status (pending, accepted, rejected)", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    


class AdminLoginAPIView(APIView):
    permission_classes = []        # login uchun token talab qilinmaydi

    @swagger_auto_schema(
        operation_description="Admin/kichik‑admin/dekan uchun JWT login",
        request_body=AdminLoginSerializer,
        responses={
            200: openapi.Response(
                description="Muvaffaqiyatli login",
                examples={
                    "application/json": {
                        "access":  "eyJh... (JWT access)",
                        "refresh": "eyJh... (JWT refresh)",
                        "user": {
                            "id": 1,
                            "username": "admin",
                            "full_name": "Super Admin"
                        },
                        "role": "admin",
                        "faculties": ["Davolash"],
                        "sections":  ["1‑bo'lim"],
                        "directions": ["Terapevtik profil"],
                        "levels": ["Bakalavr 3‑kurs"],
                        "allow_all_students": False,
                        "limit_by_course":     True
                    }
                }
            ),
            400: "Login yoki parol noto‘g‘ri / Admin emas",
        },
    )
    def post(self, request):
        ser = AdminLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user: CustomAdminUser = ser.validated_data["user"]

        return Response({
            "access":  ser.validated_data["access"],
            "refresh": ser.validated_data["refresh"],
            "user": {
                "id":        user.id,
                "username":  user.username,
                "full_name": user.get_full_name(),
            },
            "role": user.role,
            # Many‑to‑many maydonlar – string ro‘yxatga aylantiramiz
            "faculties":  [f.name       for f in user.faculties.all()],
            "sections":   [s.name       for s in user.sections.all()],
            "directions": [d.name       for d in user.directions.all()],
            "levels":     [l.name       for l in user.levels.all()],
            "allow_all_students": user.allow_all_students,
            "limit_by_course":    user.limit_by_course,
        })
    

class AdminUserListAPIView(ListAPIView):
    queryset = CustomAdminUser.objects.exclude(role='student')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

class ApplicationRetrieveView(RetrieveAPIView):
    queryset = Application.objects.prefetch_related(
        "items__files", "items__score", "items__direction", "student__faculty", "student__level"
    ).select_related("application_type", "student")
    serializer_class = ApplicationDetailSerializer
    permission_classes = [IsAuthenticated]





