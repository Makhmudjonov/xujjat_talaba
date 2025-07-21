from rest_framework import viewsets, permissions
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.models import Student
from apps.serializers import StudentsGpaSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class AdminStudentListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Student.objects.all().prefetch_related('gpa_records')
    serializer_class = StudentsGpaSerializer
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Adminlar uchun barcha studentlar va ularning GPA baholari",
        tags=["Admin - Studentlar"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
