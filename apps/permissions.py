from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStudentAndOwnerOrReadOnlyPending(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Faqat studentlar uchun
        if not hasattr(user, 'student'):
            return False

        # Faqat o‘z arizasi
        if obj.student != user.student:
            return False

        # GET/HEAD/OPTIONS
        if request.method in SAFE_METHODS:
            return True

        # PATCH/PUT faqat pending bo‘lsa
        return obj.status == 'pending'


class IsDirectionReviewerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        # Komissiya a'zosi emas
        if not hasattr(user, 'customadminuser'):
            return False

        # GET/HEAD/OPTIONS hammasiga ruxsat
        if request.method in SAFE_METHODS:
            return obj.direction in user.customadminuser.directions.all()

        # PUT/PATCH/DELETE ruxsat — agar admin o‘z direksiyasiga tegishli bo‘lsa
        return obj.direction in user.customadminuser.directions.all()


class IsSectionReviewerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if not hasattr(user, 'customadminuser'):
            return False

        # Faqat o‘ziga tegishli seksiyalar
        allowed_sections = user.customadminuser.sections.all()
        return obj.direction.section in allowed_sections


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and request.user.is_staff
        )
