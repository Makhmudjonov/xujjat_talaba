# komissiya/views.py
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from requests import request
from rest_framework.pagination import PageNumberPagination

from apps.models import Application, Level, Score
from apps.serializers import ApplicationSerializer
from komissiya.models import KomissiyaMember
from .serializers import KomissiyaLoginSerializer, ScoreSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .permissions import IsKomissiyaMember  # → pastda

from rest_framework.generics import CreateAPIView



class KomissiyaLoginAPIView(APIView):
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Komissiya a'zosi uchun JWT login",
        request_body=KomissiyaLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login muvaffaqiyatli",
                examples={
                    "application/json": {
                        "access": "jwt_access_token",
                        "refresh": "jwt_refresh_token",
                        "user": {
                            "id": 1,
                            "username": "komissiya_user",
                            "full_name": "Komissiya A'zosi"
                        },
                        "role": "dekan",
                        "faculty": "Tibbiyot",
                        "direction": "Pediatriya",
                        "section": "1-bo‘lim",
                        "course": "3-kurs",
                        "level": "Bakalavr"
                    }
                }
            ),
            400: "Login yoki komissiya a'zosi emas"
        }
    )
    def post(self, request):
        serializer = KomissiyaLoginSerializer(data=request.data)
        if serializer.is_valid():
            # self._user va self._komissiya serializer ichida saqlangan
            user = serializer._user
            komissiya = serializer._komissiya

            # course va level uchun nomlarini olish
            course_name = komissiya.course.name if komissiya.course else None
            # Agar sizda alohida level maydon bo'lsa, uni shu tarzda oling:
            level_name = getattr(komissiya, 'level', None)
            if level_name:
                # Agar level ForeignKey bo'lsa, name ni olish kerak
                if hasattr(level_name, 'name'):
                    level_name = level_name.name
            else:
                level_name = None

            return Response({
                'access': serializer.validated_data['access'],
                'refresh': serializer.validated_data['refresh'],
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name(),
                },
                'role': komissiya.role,
                'faculty': komissiya.faculty.name if komissiya.faculty else None,
                'direction': komissiya.direction.name if komissiya.direction else None,
                'section': komissiya.section.name if komissiya.section else None,
                'course': course_name,
                'level': level_name,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class KomissiyaApplicationView(ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


    @swagger_auto_schema(
        operation_description="Komissiya a'zosining ko‘rishi mumkin bo‘lgan arizalar",
        responses={200: ApplicationSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        try:
            komissiya = KomissiyaMember.objects.get(user=user)
        except KomissiyaMember.DoesNotExist:
            return Application.objects.none()

        queryset = Application.objects.all()

        if komissiya.direction:
            queryset = queryset.filter(direction=komissiya.direction)
        if komissiya.section:
            queryset = queryset.filter(student__section=komissiya.section)
        if komissiya.faculty:
            queryset = queryset.filter(student__faculty=komissiya.faculty)
        if komissiya.course:
            try:
                level = Level.objects.get(name=komissiya.course)
                queryset = queryset.filter(student__level=level)
            except Level.DoesNotExist:
                queryset = queryset.none()

        return queryset
    

class ApplicationScoreCreateAPIView(CreateAPIView):
    queryset = Score.objects.all()
    serializer_class = ScoreSerializer
    permission_classes = [IsAuthenticated, IsKomissiyaMember]

    @swagger_auto_schema(
        operation_description="Arizaga ball qo‘yish (0–100)",
        request_body=ScoreSerializer,
        responses={201: ScoreSerializer}
    )
    def post(self, request, *args, **kwargs):
        app_id = kwargs["pk"]
        application = get_object_or_404(Application, pk=app_id)

        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "application": application}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

class ApplicationDetailAPIView(RetrieveAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Application.objects.all()