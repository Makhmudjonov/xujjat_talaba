# komissiya/permissions.py
from rest_framework.permissions import BasePermission
from komissiya.models import KomissiyaMember

class IsKomissiyaMember(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
               KomissiyaMember.objects.filter(user=request.user).exists()
