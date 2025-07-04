# apps/views.py
from datetime import datetime
import json
from django.forms import ValidationError
import requests

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_date

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
        """TMA HEMIS → student ma’lumotlarini olyapmiz va lokal DB ga saqlaymiz"""
        ser = StudentLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        login, password = ser.validated_data.values()

        # 1️⃣  HEMIS logini
        auth_r = requests.post(
            "https://student.tma.uz/rest/v1/auth/login",
            json={"login": login, "password": password},
            headers={"accept": "application/json"},
            timeout=15,
        )
        if auth_r.status_code != 200:
            return Response({"detail": "Login yoki parol noto‘g‘ri"}, 401)

        hemis_token = auth_r.json()["data"]["token"]

        # 2️⃣  Profil
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

                # 3️⃣  User
                User = get_user_model()
                user, created = User.objects.get_or_create(username=d["student_id_number"],defaults={
        "first_name": d["full_name"],
        "role": "student"
    })
                if created:
                    user.set_unusable_password()
                    user.save()

                # 4️⃣  Faculty
                fac_data = d["faculty"]
                faculty, _ = Faculty.objects.get_or_create(
                    hemis_id=fac_data["id"],
                    defaults={"name": fac_data["name"], "code": fac_data["code"]},
                )

                # 5️⃣  Level
                lev_data = d["level"]
                level, _ = Level.objects.get_or_create(
                    code=lev_data["code"],
                    defaults={"name": lev_data["name"]},
                )

                student, _ = Student.objects.get_or_create(
                user=user,
                defaults={
                    "student_id_number": d["student_id_number"]
                }
            )
                # ——— maydonlarni to‘ldiramiz
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

        # 9️⃣  JWT
        jwt = get_tokens_for_student(user)
        return Response(
            {"student_id": student.id, "full_name": student.full_name, "token": jwt, "role": user.role,},
            200,
        )


# ────────────────────────────────────────────────────────────
#  Qolgan ViewSet va API lar (o‘zgarmagan)
# ────────────────────────────────────────────────────────────

class DirectionViewSet(viewsets.ModelViewSet):
    queryset = Direction.objects.select_related("section").all()
    serializer_class = DirectionSerializer
    permission_classes = [permissions.IsAuthenticated]


class IsStudentOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.student.user == request.user

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Application.objects.all()   # Qo'shing


    def get_queryset(self):
        user = self.request.user
        return Application.objects.filter(student__user=user).prefetch_related('scores', 'files')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStudentAndOwnerOrReadOnlyPending()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student)



class ApplicationFileViewSet(viewsets.ModelViewSet):
    queryset = ApplicationFile.objects.all()
    serializer_class = ApplicationFileSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.select_related("application", "reviewer").all()
    serializer_class = ScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)


class CustomAdminUserViewSet(viewsets.ModelViewSet):
    queryset = CustomAdminUser.objects.all()
    serializer_class = CustomAdminUserSerializer
    permission_classes = [permissions.IsAdminUser]


class LevelViewSet(viewsets.ModelViewSet):
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAuthenticated]


class StudentApplicationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sections = Section.objects.prefetch_related("directions").all()
        return Response(DirectionWithApplicationSerializer(sections, many=True).data)

    def post(self, request):
        ser = ApplicationCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Ariza jo‘natildi"}, 201)


class SubmitMultipleApplicationsAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        results = []
        student = request.user.student

        idx = 0
        while True:
            prefix = f"applications[{idx}]"
            direction_id = request.data.get(f"{prefix}[direction]")
            comment = request.data.get(f"{prefix}[comment]")
            file = request.FILES.get(f"{prefix}[file]")
            if not direction_id:
                break

            try:
                direction = Direction.objects.get(pk=direction_id)
                section = direction.section

            except Direction.DoesNotExist:
                results.append({"direction_id": direction_id, "error": "Direction topilmadi"})
                idx += 1
                continue

            qs = Application.objects.filter(student=student, direction=direction)
            if qs.filter(status__in=[Application.STATUS_REVIEWED,
                                     Application.STATUS_ACCEPTED,
                                     Application.STATUS_REJECTED]).exists():
                results.append({"direction_id": direction_id, "error": "Allaqachon ko‘rib chiqilgan"})
                idx += 1
                continue

            app, created = Application.objects.get_or_create(
                student=student, section=section, direction=direction, defaults={"comment": comment}
            )
            if not created:
                app.comment = comment
                app.save()

            if file:
                ApplicationFile.objects.update_or_create(
                    application=app,
                    section=direction.section,
                    defaults={"file": file, "comment": comment},
                )

            results.append({"direction_id": direction_id,
                            "success": "Yaratildi" if created else "Yangilandi"})
            idx += 1

        return Response(results, 200)


#student account view

class StudentAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba ma'lumotlari topilmadi"}, status=404)

        serializer = StudentAccountSerializer(student)
        return Response(serializer.data)
    
class AdminApplicationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'is_superuser') and not hasattr(user, 'sections'):
            return Response({"detail": "Siz admin emassiz"}, status=403)

        applications = Application.objects.all()

        # ✅ Faqat o‘ziga tegishli arizalarni ko‘rsatamiz
        if not user.allow_all_students:
            if user.sections.exists():
                applications = applications.filter(direction__section__in=user.sections.all())

            if user.directions.exists():
                applications = applications.filter(direction__in=user.directions.all())

            if user.faculties.exists():
                applications = applications.filter(student__faculty__in=user.faculties.all())

            if user.levels.exists():
                applications = applications.filter(student__level__in=user.levels.all())

            if user.limit_by_course:
                course_levels = user.levels.all()
                applications = applications.filter(student__level__in=course_levels)

        serializer = ApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
class StudentApplicationTypeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student  # Login bo‘lgan foydalanuvchi

        application_types = ApplicationType.objects.all()
        serializer = ApplicationTypeSerializer(application_types, many=True, context={'student': student})
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

        # Application obyektini topamiz yoki yaratamiz
        application, created = Application.objects.get_or_create(
            student=student,
            application_type_id=application_type_id,
            defaults={'status': 'pending', 'section': section}
        )

        # Endi ApplicationItem ni saqlaymiz
        item = serializer.save(application=application, section=section)



class ApplicationItemAdminViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationItem.objects.select_related(
        'application__student', 'direction', 'section'
    ).prefetch_related('files', 'score')
    serializer_class = ApplicationItemAdminSerializer
    permission_classes = [permissions.IsAuthenticated]  # superuser yoki role tekshirish qo‘shing

    def get_queryset(self):
        user = self.request.user

        # Masalan, agar kichik admin bo‘lsa, faqat o‘zining yo‘nalishidagi formalarni ko‘rsin
        if user.role == 'kichik_admin':
            return self.queryset.filter(direction__in=user.directions.all())

        return self.queryset
    


class StudentApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return self.queryset.filter(student=self.request.user.student)

    def create(self, request, *args, **kwargs):
        # ❗️ Har doim terminalga chiqaradi
        print("─── RAW request.data:", request.data)
        print("─── RAW request.FILES:", request.FILES)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Bu faqat validatsiya o‘tgach keladi
        print("📦 VALIDATED POST:", self.request.POST)
        print("📦 VALIDATED FILES:", self.request.FILES)
        serializer.save(student=self.request.user.student)


class ApplicationCreateView(generics.CreateAPIView):
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student)