from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from datetime import datetime
import requests
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny


from .models import ContractInfo, Level, Student, Faculty, GPARecord
from .serializers import ApplicationCreateSerializer, LevelSerializer, SectionWithDirectionsSerializer, StudentLoginSerializer
from .utils import get_tokens_for_student

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import (
    Section, Direction, Application, ApplicationFile, Score, CustomAdminUser
)
from .serializers import (
    DirectionSerializer, ApplicationSerializer,
    ApplicationFileSerializer, ScoreSerializer, CustomAdminUserSerializer
)
from .permissions import (
    IsStudentAndOwnerOrReadOnlyPending,
    IsDirectionReviewerOrReadOnly
)


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
                        "full_name": "XOSHIMOV XOSHIM",
                        "token": {
                            "access": "access_token_here",
                            "refresh": "refresh_token_here"
                        }
                    }
                }
            ),
            401: "Login yoki parol noto‘g‘ri"
        }
    )
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        login = serializer.validated_data['login']
        password = serializer.validated_data['password']

        # 1. HEMIS login
        auth_resp = requests.post(
            "https://student.tma.uz/rest/v1/auth/login",
            json={"login": login, "password": password},
            headers={"accept": "application/json"}
        )

        if auth_resp.status_code != 200:
            return Response({"error": "Login yoki parol noto‘g‘ri"}, status=401)

        token = auth_resp.json()['data']['token']

        # 2. Profil ma'lumotlarini olish
        me_resp = requests.get(
            "https://student.tma.uz/rest/v1/account/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        if me_resp.status_code != 200:
            return Response({"error": "Profilni olishda xatolik"}, status=400)

        data = me_resp.json()['data']

        # Fakultet saqlash
        faculty_data = data["faculty"]
        faculty, _ = Faculty.objects.get_or_create(
            hemis_id=faculty_data["id"],
            defaults={"name": faculty_data["name"], "code": faculty_data["code"]}
        )

        # Bosqich (level) saqlash
        level_data = data["level"]  # {"code": "4", "name": "4-bosqich"}
        level_obj, _ = Level.objects.get_or_create(
            code=level_data["code"],
            defaults={"name": level_data["name"]}
        )

        # Studentni yaratish yoki yangilash
        student, _ = Student.objects.update_or_create(
            student_id_number=data["student_id_number"],
            defaults={
                "full_name": data["full_name"],
                "short_name": data.get("short_name"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "image": data.get("image"),
                "gender": data["gender"]["name"],
                "birth_date": datetime.fromtimestamp(data["birth_date"]).date(),
                "address": data.get("address", ""),
                "university": data.get("university"),
                "faculty": faculty,
                "group": data["group"]["name"],
                "level": level_obj
            }
        )

        # GPA ma'lumotlarini olish
        gpa_resp = requests.get(
            "https://student.tma.uz/rest/v1/education/gpa-list",
            headers={"Authorization": f"Bearer {token}"}
        )

        if gpa_resp.status_code == 200:
            for item in gpa_resp.json().get('data', []):
                GPARecord.objects.update_or_create(
                    student=student,
                    education_year=item['educationYear']['name'],
                    level=item['level']['name'],
                    defaults={
                        "gpa": item["gpa"],
                        "credit_sum": float(item["credit_sum"]),
                        "subjects": item["subjects"],
                        "debt_subjects": item["debt_subjects"],
                        "can_transfer": item["can_transfer"],
                        "method": item["method"],
                        "created_at": datetime.fromtimestamp(item["created_at"]),
                    }
                )

        # Kontrakt ma’lumotlari
        contract_resp = requests.get(
            "https://student.tma.uz/rest/v1/student/contract",
            headers={"Authorization": f"Bearer {token}"}
        )

        if contract_resp.status_code == 200:
            contract_data = contract_resp.json().get("data", {})
            if contract_data:
                ContractInfo.objects.update_or_create(
                    student=student,
                    defaults={
                        "contract_number": contract_data["contractNumber"],
                        "contract_date": datetime.strptime(contract_data["contractDate"], "%d.%m.%Y").date(),
                        "edu_organization": contract_data["eduOrganization"],
                        "edu_speciality": contract_data["eduSpeciality"],
                        "edu_period": contract_data["eduPeriod"],
                        "edu_year": contract_data["eduYear"],
                        "edu_type": contract_data["eduType"],
                        "edu_form": contract_data["eduForm"],
                        "edu_course": contract_data["eduCourse"],
                        "contract_type": contract_data["eduContractType"],
                        "pdf_link": contract_data["pdfLink"],
                        "contract_sum": contract_data["eduContractSum"],
                        "gpa": contract_data["gpa"],
                        "debit": contract_data.get("debit"),
                        "credit": contract_data.get("credit")
                    }
                )

        # Django user (faqat JWT uchun)
        user, created = User.objects.get_or_create(username=student.student_id_number)
        if created:
            user.set_unusable_password()
            user.save()

        jwt = get_tokens_for_student(user)

        return Response({
            "student_id": student.id,
            "full_name": student.full_name,
            "token": jwt
        }, status=200)





# class SectionViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Section.objects.all()
#     serializer_class = SectionSerializer
#     permission_classes = [permissions.IsAuthenticated]

class DirectionViewSet(viewsets.ModelViewSet):
    queryset = Direction.objects.select_related('section').all()
    serializer_class = DirectionSerializer
    permission_classes = [permissions.IsAuthenticated]



class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.select_related('student', 'direction').all()

    def get_permissions(self):
        # Create, update, delete uchun custom permission
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStudentAndOwnerOrReadOnlyPending()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationSerializer

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student)


class ApplicationFileViewSet(viewsets.ModelViewSet):
    queryset = ApplicationFile.objects.all()
    serializer_class = ApplicationFileSerializer
    parser_classesc = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.select_related('application', 'reviewer').all()
    serializer_class = ScoreSerializer
    permission_classes = [permissions.IsAuthenticated]  # yoki faqat adminlar uchun custom ruxsat

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
        """Bo‘limlar va yo‘nalishlarni nested holda qaytaradi"""
        sections = Section.objects.prefetch_related('directions').all()
        serializer = SectionWithDirectionsSerializer(sections, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Student application jo‘natadi"""
        serializer = ApplicationCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Ariza jo‘natildi"}, status=status.HTTP_201_CREATED)