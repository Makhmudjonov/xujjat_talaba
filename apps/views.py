# apps/views.py
from datetime import datetime
from django.utils import timezone
import json
import random
from django.forms import ValidationError
import requests

from rest_framework.decorators import action

from django.utils.timezone import now
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import RetrieveModelMixin

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.dateparse import parse_date
from django.core.exceptions import PermissionDenied

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.authentication import TokenAuthentication



from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets, permissions, generics,parsers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.pagenation import CustomPagination

from .models import (
    Answer, ApplicationItem, ApplicationType, Faculty, Level, OdobAxloqStudent, Question, Student, ContractInfo, GPARecord,
    Section, Direction, Application, ApplicationFile, Score, CustomAdminUser, Test, TestSession, Option, University
)
from .serializers import (
    AdminLoginSerializer, AdminUserSerializer, AnswerSubmitSerializer, ApplicationDetailSerializer, ApplicationFullSerializer, ApplicationItemAdminSerializer, ApplicationItemSerializer, ApplicationTypeSerializer, CustomAdminUserSerializer, QuestionSerializer, QuizUploadSerializer, RandomizedQuestionSerializer, ScoreCreateSerializer, StartTestSerializer, StudentAccountSerializer, StudentLoginSerializer, LevelSerializer, DirectionWithApplicationSerializer,
    ApplicationCreateSerializer, DirectionSerializer, ApplicationSerializer,
    ApplicationFileSerializer, ScoreSerializer, SubmitMultipleApplicationsSerializer, TestDictSerializer, TestResultSerializer, TestResumeSerializer, TestSerializer
)
from .permissions import (
    IsStudentAndOwnerOrReadOnlyPending,
    IsDirectionReviewerOrReadOnly,)

from rest_framework.permissions import IsAdminUser

from .utils import get_tokens_for_student
import logging


User = get_user_model()  # faqat bir marta

# Set up logging
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
#  STUDENT LOGIN
# ────────────────────────────────────────────────────────────

UNIVERSITY_API_CONFIG = {
    "tma": {
        "base_url": "https://student.tma.uz/rest/v1",
    },
    "sampi": {
        "base_url": "https://student.tashpmi.uz/rest/v1",
    },
    "stom": {
        "base_url": "https://student.tsdi.uz/rest/v1",
    },
}



class StudentLoginAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["login", "password", "university"],
            properties={
                "login": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "university": openapi.Schema(type=openapi.TYPE_STRING, enum=["tma", "urdu", "qfdu"]),
            },
        ),
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
        login = request.data.get("login")
        password = request.data.get("password")
        university = request.data.get("university")

        if not login or not password or not university:
            return Response({"detail": "Ma'lumotlar to‘liq emas"}, status=400)

        config = UNIVERSITY_API_CONFIG.get(university)
        if not config:
            return Response({"detail": "Noto‘g‘ri universitet tanlandi"}, status=400)

        base_url = config["base_url"]

        # 1. Login qilish
        try:
            auth_r = requests.post(
                f"{base_url}/auth/login",
                json={"login": login, "password": password},
                headers={"accept": "application/json"},
                timeout=15,
            )
        except Exception:
            return Response({"detail": "HEMIS bilan bog‘lanib bo‘lmadi"}, 502)

        if auth_r.status_code != 200:
            return Response({"detail": "Login yoki parol noto‘g‘ri"}, 401)

        hemis_token = auth_r.json()["data"]["token"]

        # 2. Profil olish
        me_r = requests.get(
            f"{base_url}/account/me",
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
                    defaults={"first_name": d["full_name"], "role": "student"},
                )

                univer, _ = University.objects.get_or_create(
                    name=d["university"]
                )
                
                if created:
                    user.set_unusable_password()
                    user.save()

                faculty, _ = Faculty.objects.get_or_create(
                    # hemis_id=d["faculty"]["id"],
                    defaults={"name": d["faculty"]["name"], "code": d["faculty"]["code"]},
                )

                

                level, _ = Level.objects.get_or_create(
                    code=d["level"]["code"],
                    defaults={"name": d["level"]["name"]},
                )

                student, _ = Student.objects.get_or_create(
                    user=user,
                    defaults={"student_id_number": d["student_id_number"]},
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
                student.university = d['university']  # tanlangan nom saqlanadi
                student.university1 = univer  # tanlangan nom saqlanadi
                student.faculty = faculty
                student.group = d["group"]["name"]
                student.level = level
                student.save()

                # GPA list
                gpa_r = requests.get(
                    f"{base_url}/education/gpa-list",
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

                # Contract info
                c_r = requests.get(
                    f"{base_url}/student/contract",
                    headers={"Authorization": f"Bearer {hemis_token}"},
                    timeout=15,
                )
                if c_r.status_code == 200 and c_r.json().get("data"):
                    cd = c_r.json()["data"]
                    ContractInfo.objects.update_or_create(
                        student=student,
                        defaults={
                            "contract_number": cd["contractNumber"],
                            "contract_date": datetime.strptime(cd["contractDate"], "%d.%m.%Y").date(),
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

        app_item = serializer.save(application=application, section=section)

        # Fayllarni JSON formatda olish
        files_json = self.request.data.get('files')
        if files_json:
            try:
                import json
                files_data = json.loads(files_json)
            except Exception:
                files_data = []

            for j, file_meta in enumerate(files_data):
                upload = self.request.FILES.get(f"files_{i}_{j}")
                if upload:
                    ApplicationFile.objects.create(
                        item=app_item,
                        file=upload,
                        section_id=file_meta.get('section'),
                        comment=file_meta.get('comment', '')
                    )


    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        student = getattr(request.user, 'student', None)

        if instance.application.student != student:
            return Response({"detail": "Bu yo'nalishni taxrirlashga ruxsat yo'q."},
                            status=status.HTTP_403_FORBIDDEN)

        comment = request.data.get('student_comment')
        if comment is not None:
            instance.student_comment = comment
            instance.save()
            return Response(self.get_serializer(instance).data)

        return Response({"detail": "Hech qanday o'zgarish kiritilmagan."},
                        status=status.HTTP_400_BAD_REQUEST)


class StudentApplicationTypeListAPIView(APIView):
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

    
class ApplicationItemViewSet(viewsets.ModelViewSet):
    queryset = ApplicationItem.objects.all()
    serializer_class = ApplicationItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

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
    serializer_class = DirectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Direction.objects.all().order_by("id")


    def get_queryset(self):
        qs = Direction.objects.select_related("section", "test").all()
        user = self.request.user
        student = getattr(user, 'student', None)
        app_type_id = self.request.query_params.get("application_type_id")

        if student and app_type_id:
            applied_dirs = ApplicationItem.objects.filter(
                application__student=student,
                application__application_type_id=app_type_id
            ).values_list('direction_id', flat=True)
            qs = qs.exclude(id__in=applied_dirs)

        return qs.order_by("id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['student'] = getattr(self.request.user, 'student', None)
        return context

    
class StudentApplicationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]
    
    

    # ... list() o‘zgarishsiz ...

    def create(self, request):
        student = getattr(request.user, 'student', None)
        if not student:
            return Response({"detail": "Talaba topilmadi."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- boshlang‘ich tekshiruvlar (o‘zgarishsiz) ---
        data = request.data

        try:
            app_type_id = int(data.get("application_type"))
            app_type = get_object_or_404(ApplicationType, id=app_type_id)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid application_type."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            items = json.loads(data.get("items", "[]"))
        except json.JSONDecodeError:
            return Response({"detail": "Items noto‘g‘ri formatda."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(items, list) or not items:
            return Response({"detail": "Kamida bitta yo‘nalish bo‘lishi kerak."},
                            status=status.HTTP_400_BAD_REQUEST)

        # --- duplikat tekshiruv (o‘zgarishsiz) ---
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

        # --------------- ASOSIY QISM ---------------
        with transaction.atomic():
            first_dir = get_object_or_404(Direction, id=items[0]["direction"])
            application = Application.objects.create(
                student   = student,
                application_type = app_type,
                comment   = data.get("comment", ""),
                section   = first_dir.section,
            )

            for i, it in enumerate(items):
                dir_obj = get_object_or_404(Direction, id=it["direction"])

                # string → float xavfsiz konvert (qiymat yo‘q bo‘lsa None qoladi)
                gpa_val         = it.get("gpa")
                test_result_val = it.get("test_result")

                gpa_float         = float(gpa_val)         if gpa_val         not in [None, ""] else None
                test_result_float = float(test_result_val) if test_result_val not in [None, ""] else None

                # --- ApplicationItem ni gpa / test_result bilan yaratamiz ---
                app_item = ApplicationItem.objects.create(
                    application      = application,
                    title            = dir_obj.name,
                    direction        = dir_obj,
                    student_comment  = it.get("student_comment", ""),
                    gpa              = gpa_float,
                    test_result      = test_result_float,
                )

                # --- Fayl (agar bo‘lsa) ---
                for j, f in enumerate(it.get("files", [])):
                    upload = request.FILES.get(f"files_{i}_{j}")
                    if upload:
                        ApplicationFile.objects.create(
                            item=app_item,
                            file=upload,
                            section_id=f.get("section"),
                            comment=f.get("comment", "")
                        )


                # --- Score jadvali (ixtiyoriy) ---
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

        # Faqat comment yangilash
        student_comment = request.data.get("student_comment", "")
        app_item.student_comment = student_comment
        app_item.save()

        # Fayllar listi JSON bo‘lishi kerak: [{"section": 1, "comment": "xujjat"}, ...]
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

        if user.university1:
            qs = qs.filter(student__university1=user.university1)

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
            # "user": {
            #     "id":        user.id,
            #     "username":  user.username,
            #     "full_name": user.get_full_name(),
            # },
            # "role": user.role,
            # # Many‑to‑many maydonlar – string ro‘yxatga aylantiramiz
            # "faculties":  [f.name       for f in user.faculties.all()],
            # "sections":   [s.name       for s in user.sections.all()],
            # "directions": [d.name       for d in user.directions.all()],
            # "levels":     [l.name       for l in user.levels.all()],
            # "allow_all_students": user.allow_all_students,
            # "limit_by_course":    user.limit_by_course,
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





#TEST SAVOLLARI UCHUN VIEW

class StartTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test_id = serializer.validated_data['test_id']
        test = get_object_or_404(Test, id=test_id)

        try:
            student = request.user.student
        except AttributeError:
            logger.error(f"No student profile for user {request.user.username}")
            return Response({"detail": "Talaba topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # Odob-axloq ro‘yxatidan tekshirish
        record = OdobAxloqStudent.objects.filter(hemis_id=student.student_id_number).first()
        if record:
            logger.warning(f"Student {student.student_id_number} blocked due to: {record.sabab}")
            return Response({"detail": f"{record.sabab}"}, status=status.HTTP_403_FORBIDDEN)

        if not test.levels.filter(id=student.level_id).exists():
            return Response({"detail": "Bu test sizning kursingiz uchun emas."},
                            status=status.HTTP_403_FORBIDDEN)

        existing_session = TestSession.objects.filter(test=test, student=student, finished_at__isnull=True).first()
        if existing_session:
            logger.info(f"Resuming existing session {existing_session.id} for student {student.id}")
            return Response(TestResumeSerializer(existing_session, context={'request': request}).data)

        if test.start_time and timezone.now() < test.start_time:
            return Response({"detail": f"Test {test.start_time.strftime('%Y-%m-%d %H:%M')} dan keyin boshlanadi."},
                            status=status.HTTP_400_BAD_REQUEST)

        questions = list(test.questions.all())
        if len(questions) < test.question_count:
            logger.error(f"Not enough questions for test {test_id}. Available: {len(questions)}, Required: {test.question_count}")
            return Response({"detail": "Testda yetarlicha savol mavjud emas."}, status=status.HTTP_400_BAD_REQUEST)

        random.shuffle(questions)
        selected = questions[:test.question_count]

        session = TestSession.objects.create(
            student=student,
            test=test,
            current_question_index=0
        )
        session.questions.set(selected)
        logger.info(f"Created new session {session.id} with {len(selected)} questions for student {student.id}")

        first_question = selected[0] if selected else None
        remaining_seconds = test.time_limit * 60

        return Response({
            "session_id": session.id,
            "duration": test.time_limit,
            "first_question": RandomizedQuestionSerializer(first_question).data if first_question else None,
            "total_questions": len(selected),
            "resume": False,
            "current_index": 1,
            "remaining_seconds": remaining_seconds
        })

class TestResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            student = request.user.student
        except AttributeError:
            logger.error(f"No student profile for user {request.user.username}")
            return Response({"detail": "Talaba hisobi topilmadi"}, status=status.HTTP_403_FORBIDDEN)

        try:
            session = TestSession.objects.get(id=session_id, student=student, finished_at__isnull=True)
        except TestSession.DoesNotExist:
            logger.error(f"No TestSession found for session_id={session_id}, student={student.id}")
            return Response(
                {"detail": "No TestSession matches the given query. Session may be completed or invalid."},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.is_expired():
            session.finished_at = timezone.now()
            session.save()
            logger.info(f"Session {session_id} expired for student {student.id}")
            return Response({"detail": "Sessiya muddati tugagan"}, status=status.HTTP_400_BAD_REQUEST)

        questions = list(session.questions.all())
        answered_ids = session.answers.values_list('question_id', flat=True)
        unanswered_questions = [q for q in questions if q.id not in answered_ids]

        if not unanswered_questions:
            session.finished_at = timezone.now()
            correct = session.answers.filter(is_correct=True).count()
            total = len(questions)
            session.correct_answers = correct
            session.total_questions = total
            session.score = round((correct / total) * 100, 2) if total else 0
            session.save()
            logger.info(f"Session {session_id} completed: {correct}/{total} correct")
            return Response({"detail": "Test yakunlangan"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure current_question_index points to the next unanswered question
        session.current_question_index = len(answered_ids)
        session.save()

        current_question = unanswered_questions[0] if unanswered_questions else None
        response_data = {
            "id": session.id,
            "total_questions": len(questions),
            "current_question": RandomizedQuestionSerializer(current_question).data if current_question else None,
            "remaining_seconds": session.remaining_seconds(),
            "current_index": session.current_question_index + 1
        }
        logger.info(f"Resumed session {session_id} with current_index={session.current_question_index + 1}, unanswered={len(unanswered_questions)}")
        return Response(response_data, status=status.HTTP_200_OK)


class TestResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            student = request.user.student
        except AttributeError:
            logger.error(f"No student profile for user {request.user.username}")
            return Response({"detail": "Talaba hisobi topilmadi"}, status=status.HTTP_403_FORBIDDEN)

        try:
            session = TestSession.objects.get(id=session_id, student=student, finished_at__isnull=True)
        except TestSession.DoesNotExist:
            logger.error(f"No TestSession found for session_id={session_id}, student={student.id}")
            return Response(
                {"detail": "No TestSession matches the given query. Session may be completed or invalid."},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.is_expired():
            session.finished_at = timezone.now()
            session.save()
            logger.info(f"Session {session_id} expired for student {student.id}")
            return Response({"detail": "Sessiya muddati tugagan"}, status=status.HTTP_400_BAD_REQUEST)

        questions = list(session.questions.all())
        answered_ids = session.answers.values_list('question_id', flat=True)
        unanswered_questions = [q for q in questions if q.id not in answered_ids]

        if not unanswered_questions:
            session.finished_at = timezone.now()
            correct = session.answers.filter(is_correct=True).count()
            total = len(questions)
            session.correct_answers = correct
            session.total_questions = total
            session.score = round((correct / total) * 100, 2) if total else 0
            session.save()
            logger.info(f"Session {session_id} completed: no unanswered questions")
            return Response({"detail": "Test yakunlangan"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure current_question_index points to an unanswered question
        if session.current_question_index >= len(questions) or questions[session.current_question_index].id in answered_ids:
            session.current_question_index = len(answered_ids)
            session.save()

        current_question = unanswered_questions[0] if unanswered_questions else None
        serializer = TestResumeSerializer(session, context={'request': request})
        logger.info(f"Resumed session {session_id} with current_index={session.current_question_index + 1}, unanswered={len(unanswered_questions)}")
        return Response(serializer.data, status=status.HTTP_200_OK)

class SubmitAnswerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        serializer = AnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = TestSession.objects.get(id=session_id, student=request.user.student, finished_at__isnull=True)
        except TestSession.DoesNotExist:
            logger.error(f"No TestSession found for session_id={session_id}, student={request.user.student.id}")
            return Response({"detail": "No TestSession matches the given query."}, status=status.HTTP_404_NOT_FOUND)

        if session.is_expired():
            session.finished_at = timezone.now()
            session.save()
            logger.info(f"Session {session_id} expired during answer submission")
            return Response({"detail": "Test vaqti tugadi. Yakunlandi."}, status=status.HTTP_400_BAD_REQUEST)

        question_id = serializer.validated_data['question_id']
        selected_option_id = serializer.validated_data['selected_option_id']

        questions = list(session.questions.all())
        if question_id not in [q.id for q in questions]:
            logger.error(f"Question {question_id} not in session {session_id} questions")
            return Response({"detail": "Bu savol ushbu sessiyaga tegishli emas."}, status=status.HTTP_400_BAD_REQUEST)

        if Answer.objects.filter(session=session, question_id=question_id).exists():
            logger.warning(f"Duplicate answer attempt for question {question_id} in session {session_id}")
            return Response({"detail": "Bu savolga allaqachon javob berilgan"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = Question.objects.get(id=question_id, test=session.test)
            selected_option = Option.objects.get(id=selected_option_id, question=question)
        except Question.DoesNotExist:
            logger.error(f"Question {question_id} does not exist for test {session.test.id}")
            return Response({"detail": "Savol topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        except Option.DoesNotExist:
            logger.error(f"Option {selected_option_id} does not exist for question {question_id}")
            return Response({"detail": "Variant topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        is_correct = selected_option.is_correct
        Answer.objects.create(
            session=session,
            question=question,
            selected_option=selected_option,
            is_correct=is_correct
        )
        logger.info(f"Answer recorded for question {question_id} in session {session_id}. Total answers: {session.answers.count()}")

        # Update current_question_index
        answered_ids = session.answers.values_list('question_id', flat=True)
        session.current_question_index = len(answered_ids)
        session.save()

        return Response({"detail": "Javob qabul qilindi"}, status=status.HTTP_200_OK)

class FinishTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = TestSession.objects.get(id=session_id, student=request.user.student, finished_at__isnull=True)
        except TestSession.DoesNotExist:
            logger.error(f"No TestSession found for session_id={session_id}, student={request.user.student.id}")
            return Response({"detail": "No TestSession matches the given query."}, status=status.HTTP_404_NOT_FOUND)

        questions = list(session.questions.all())
        answered_ids = session.answers.values_list('question_id', flat=True)
        if len(answered_ids) < len(questions):
            logger.warning(f"Session {session_id} finished with {len(answered_ids)}/{len(questions)} answers")

        session.finished_at = timezone.now()
        correct = session.answers.filter(is_correct=True).count()
        total = len(questions)
        session.correct_answers = correct
        session.total_questions = total
        session.score = round((correct / total) * 100, 2) if total else 0
        session.save()
        logger.info(f"Session {session_id} finished: {correct}/{total} correct, score={session.score}%")

        return Response({
            "correct_answers": correct,
            "total_questions": total,
            "score": session.score
        })


class QuizUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]        # yoki IsAdminUser
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    # ----- Swagger hujjati -----
    @swagger_auto_schema(
        operation_summary="TXT test faylini yuklash (Level bo‘yicha)",
        manual_parameters=[
            openapi.Parameter("title",  openapi.IN_FORM, required=True, type=openapi.TYPE_STRING,
                              description="Test nomi"),
            openapi.Parameter("levels", openapi.IN_FORM, required=True, type=openapi.TYPE_STRING,
                              description="Level ID lar JSON array ko‘rinishida: [1,2]"),
            openapi.Parameter("file",   openapi.IN_FORM, required=True, type=openapi.TYPE_FILE,
                              format="binary", description="Shablonli TXT fayl"),
        ],
        responses={
            200: openapi.Response("OK", examples={"application/json": {"imported": 25, "test_id": 7}}),
            400: openapi.Response("Xatolar", examples={"application/json": {
                "errors": [{"line": 4, "detail": "Variant '+' bilan boshlanishi kerak"}]}})
        },
    )
    def post(self, request):
        ser = QuizUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        title      = ser.validated_data["title"]
        level_ids  = ser.validated_data["levels"]     # allaqachon list
        txt_lines  = ser.validated_data["file"].read().decode("utf-8").splitlines()

        # --- Test yaratish ---
        test = Test.objects.create(
            title=title,
            question_count=0,
            time_limit=30,
            created_at=datetime.now()
        )
        test.levels.set(level_ids)

        # --- Faylni bloklarga ajratish va tekshirish ---
        errors, blocks, buf = [], [], []
        for idx, raw in enumerate(txt_lines, start=1):
            line = raw.strip()
            if not line:
                if buf:
                    blocks.append(buf)
                    buf = []
                continue
            buf.append((idx, line))
        if buf:
            blocks.append(buf)

        parsed = []
        for block in blocks:
            first_ln, first_line = block[0]
            # if not first_line.startswith("#"):
            #     errors.append({"line": first_ln, "detail": "Savol '# ' bilan boshlanishi kerak"})
            #     continue

            q_text = first_line[1:].strip()
            opts, has_plus = [], False
            for ln, opt in block[1:]:
                if not (opt.startswith("+") or opt.startswith("-")):
                    errors.append({"line": ln, "detail": "Variant '+' yoki '-' bilan boshlanishi kerak"})
                    break
                text = opt[1:].strip()
                is_correct = opt.startswith("+")
                has_plus |= is_correct
                opts.append((text, is_correct))
            else:
                if not has_plus:
                    errors.append({"line": first_ln, "detail": "Kamida bitta + javob bo‘lishi shart"})
                else:
                    parsed.append((q_text, opts))

        if errors:
            test.delete()
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # --- DB ga import ---
        with transaction.atomic():
            for q_text, opts in parsed:
                q = Question.objects.create(test=test, text=q_text)
                Option.objects.bulk_create(
                    [Option(question=q, text=t, is_correct=flag) for t, flag in opts]
                )

        test.question_count = len(parsed)
        test.save()

        return Response({"imported": len(parsed), "test_id": test.id}, status=status.HTTP_200_OK)
    

class TestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Test.objects.all().order_by('-created_at')
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {"request": self.request}

    def list(self, request, *args, **kwargs):
        try:
            student = request.user.student
        except AttributeError:
            logger.error(f"No student profile for user {request.user.username}")
            return Response({"detail": "Talaba hisobi topilmadi"}, status=status.HTTP_403_FORBIDDEN)

        # Odob-axloq ro‘yxatidan tekshirish
        record = OdobAxloqStudent.objects.filter(hemis_id=student.student_id_number).first()
        if record:
            logger.warning(f"Student {student.student_id_number} blocked due to: {record.sabab}")
            return Response({"detail": f"{record.sabab}"}, status=status.HTTP_403_FORBIDDEN)

        tests = self.get_queryset().filter(levels=student.level_id)
        serializer = self.get_serializer(tests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

class AdminAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'dekan', 'kichik_admin']:
            return Response({"detail": "Siz admin emassiz"}, status=403)

        serializer = CustomAdminUserSerializer(user)
        return Response(serializer.data)
    

# views.py
class ApplicationFileUpdateAPIView(generics.UpdateAPIView):
    serializer_class = ApplicationFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = ApplicationFile.objects.select_related('item__application__student__user').filter(
            pk=self.kwargs['pk']
        ).first()
        if not obj:
            raise NotFound("Bunday fayl topilmadi.")
        if obj.item.application.student.user != self.request.user:
            raise PermissionDenied("Siz bu faylga o‘zgartirish kiritish huquqiga ega emassiz.")
        return obj
    

class GetNextQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = TestSession.objects.get(id=session_id, student=request.user.student, finished_at__isnull=True)
        except TestSession.DoesNotExist:
            logger.error(f"No TestSession found for session_id={session_id}, student={request.user.student.id}")
            return Response({"detail": "No TestSession matches the given query."}, status=status.HTTP_404_NOT_FOUND)

        if session.is_expired():
            session.finished_at = timezone.now()
            session.save()
            logger.info(f"Session {session_id} expired during next question request")
            return Response({"detail": "Test vaqti tugadi. Yakunlandi."}, status=status.HTTP_400_BAD_REQUEST)

        questions = list(session.questions.all())
        answered_ids = session.answers.values_list('question_id', flat=True)
        unanswered_questions = [q for q in questions if q.id not in answered_ids]

        if not unanswered_questions:
            session.finished_at = timezone.now()
            correct = session.answers.filter(is_correct=True).count()
            total = len(questions)
            session.correct_answers = correct
            session.total_questions = total
            session.score = round((correct / total) * 100, 2) if total else 0
            session.save()
            logger.info(f"Session {session_id} completed: {correct}/{total} correct")
            return Response({"detail": "Test yakunlangan"}, status=status.HTTP_400_BAD_REQUEST)

        # Set current_question_index
        session.current_question_index = len(answered_ids)
        question = unanswered_questions[0]
        session.save()
        logger.info(f"Next question {question.id} served for session {session_id}, current_index={session.current_question_index + 1}")

        return Response(RandomizedQuestionSerializer(question).data)