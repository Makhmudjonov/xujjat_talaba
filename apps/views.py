# apps/views.py
from datetime import datetime
from django.utils import timezone
import json
import random
from django.forms import ValidationError
import requests

from django.utils.timezone import now

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
    Answer, ApplicationItem, ApplicationType, Faculty, Level, Question, Student, ContractInfo, GPARecord,
    Section, Direction, Application, ApplicationFile, Score, CustomAdminUser, Test, TestSession, Option
)
from .serializers import (
    AdminLoginSerializer, AdminUserSerializer, AnswerSubmitSerializer, ApplicationDetailSerializer, ApplicationFullSerializer, ApplicationItemAdminSerializer, ApplicationItemSerializer, ApplicationTypeSerializer, QuestionSerializer, QuizUploadSerializer, RandomizedQuestionSerializer, ScoreCreateSerializer, StartTestSerializer, StudentAccountSerializer, StudentLoginSerializer, LevelSerializer, DirectionWithApplicationSerializer,
    ApplicationCreateSerializer, DirectionSerializer, ApplicationSerializer,
    ApplicationFileSerializer, ScoreSerializer, SubmitMultipleApplicationsSerializer, TestResultSerializer, TestSerializer
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

        return qs.order_by('section__name', 'name')

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
                            item     = app_item,
                            file     = upload,
                            section_id = f.get("section"),
                            comment  = f.get("comment", "")
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





#TEST SAVOLLARI UCHUN VIEW

class StartTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["test_id"],
        properties={"test_id": openapi.Schema(type=openapi.TYPE_INTEGER)}
    ))
    def post(self, request):
        test_id = request.data.get("test_id")
        test = get_object_or_404(Test, id=test_id)

        try:
            student = request.user.student
        except Exception as e:
            return Response({"detail": f"Student topilmadi: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Kurs bo‘yicha tekshiruv
        if not test.levels.filter(id=student.level_id).exists():
            return Response({"detail": "Bu test sizning kursingiz uchun emas."},
                            status=status.HTTP_403_FORBIDDEN)

        # 🛑 Avvalgi session borligini tekshirish
        existing_session = TestSession.objects.filter(test=test, student=student).first()
        if existing_session:
            first_q = existing_session.questions.first()
            first_data = RandomizedQuestionSerializer(first_q).data if first_q else None
            return Response({
                "detail": "Siz bu testni allaqachon boshlagansiz.",
                "session_id": existing_session.id,
                "duration": test.time_limit,
                "first_question": first_data,
                "total_questions": existing_session.questions.count(),
                "resume": True
            })

        # Test vaqti boshlanishidan oldin bo‘lsa
        if test.start_time and now() < test.start_time:
            return Response({"detail": f"Test {test.start_time.strftime('%Y-%m-%d %H:%M')} dan keyin boshlanadi."},
                            status=status.HTTP_403_FORBIDDEN)

        # Yangi test session va random savollar
        questions = list(test.questions.all())
        random.shuffle(questions)
        selected = questions[:test.question_count]

        session = TestSession.objects.create(student=student, test=test)
        session.questions.set(selected)

        first_q = selected[0] if selected else None
        first_data = RandomizedQuestionSerializer(first_q).data if first_q else None

        return Response({
            "session_id": session.id,
            "duration": test.time_limit,
            "first_question": first_data,
            "total_questions": len(selected),
            "resume": False
        })







class GetNextQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Keyingi savolni olish",
        manual_parameters=[
            openapi.Parameter('session_id', openapi.IN_PATH,
                              description="Test session ID", type=openapi.TYPE_INTEGER)
        ],
        responses={200: RandomizedQuestionSerializer()}
    )
    def get(self, request, session_id):
        session = get_object_or_404(TestSession, id=session_id, student=request.user.student)

        # ✅ Vaqt tugaganini tekshir
        if session.finished_at is None:
            end_time = session.started_at + timezone.timedelta(minutes=session.test.time_limit)
            if timezone.now() >= end_time:
                self.finish_session(session)
                return Response({"detail": "Test vaqti tugadi. Yakunlandi."}, status=200)

        # ❓ Javob berilgan savollar
        answered_ids = session.answers.values_list("question_id", flat=True)

        # 🎯 Keyingi savolni random tanlash
        question = (session.questions
                    .exclude(id__in=answered_ids)
                    .order_by('?')
                    .first())

        if not question:
            self.finish_session(session)
            return Response({"detail": "Test yakunlangan"}, status=200)

        return Response(RandomizedQuestionSerializer(question).data)

    def finish_session(self, session):
        answers = session.answers.all()
        correct = answers.filter(is_correct=True).count()
        total = session.questions.count()

        session.finished_at = timezone.now()
        session.correct_answers = correct
        session.total_questions = total
        session.score = round((correct / total) * 100, 2) if total else 0
        session.save()



class SubmitAnswerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Savolga javob yuborish",
        manual_parameters=[
            openapi.Parameter('session_id', openapi.IN_PATH, description="Test session ID", type=openapi.TYPE_INTEGER)
        ],
        request_body=AnswerSubmitSerializer,
        responses={200: openapi.Response("Success", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)}
        ))}
    )
    def post(self, request, session_id):
        session = get_object_or_404(TestSession, id=session_id, student=request.user.student)

        # ✅ Vaqt tugaganini tekshir
        end_time = session.started_at + timezone.timedelta(minutes=session.test.time_limit)
        if timezone.now() >= end_time or session.finished_at is not None:
            return Response(
                {"detail": "Test vaqti tugagan. Javob yuborib bo‘lmaydi."},
                status=status.HTTP_403_FORBIDDEN
            )

        ser = AnswerSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        question = get_object_or_404(Question, id=ser.validated_data["question_id"])
        selected_option = get_object_or_404(Option, id=ser.validated_data["selected_option_id"])

        # 🔁 Avvalgi javobni tekshirib, qayta yozishni oldini olamiz (agar kerak bo‘lsa)
        if Answer.objects.filter(session=session, question=question).exists():
            return Response(
                {"detail": "Bu savolga allaqachon javob berilgan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        Answer.objects.create(
            session=session,
            question=question,
            selected_option=selected_option,
            is_correct=selected_option.is_correct
        )

        return Response({"detail": "Javob qabul qilindi"})


class FinishTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Testni yakunlash va natijani olish",
        manual_parameters=[
            openapi.Parameter('session_id', openapi.IN_PATH, description="Test session ID", type=openapi.TYPE_INTEGER)
        ],
        responses={200: TestResultSerializer()}
    )
    def post(self, request, session_id):
        session = get_object_or_404(TestSession, id=session_id, student=request.user.student)
        answers = session.answers.all()
        correct = answers.filter(is_correct=True).count()
        total = session.questions.count()

        # 🛡️ Noldan bo‘linishni oldini olish
        if total == 0:
            score = 0
        else:
            score = round((correct / total) * 100, 2)

        session.finished_at = timezone.now()
        session.score = score
        session.correct_answers = correct
        session.total_questions = total
        session.save()

        return Response(TestResultSerializer(session).data)
    



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
            if not first_line.startswith("#"):
                errors.append({"line": first_ln, "detail": "Savol '# ' bilan boshlanishi kerak"})
                continue

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

