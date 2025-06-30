from django.db import models
from django.contrib.auth import get_user_model
from apps.models import Section, Direction, Faculty, Level

User = get_user_model()

class KomissiyaMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('dekan', 'Dekan'),
        ('kichik_admin', 'Kichik Admin'),
        ('azo', 'A\'zo'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='komissiya_member')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    faculty = models.ForeignKey(
        Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='komissiya_members'
    )
    direction = models.ForeignKey(
        Direction, on_delete=models.SET_NULL, null=True, blank=True, related_name='komissiya_members'
    )

    section = models.ForeignKey(
        Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='komissiya_members'
    )
    course = models.ForeignKey(
        Level, on_delete=models.SET_NULL, null=True, blank=True, related_name='komissiya_members'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    # level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)  # <-- Bu qo‘shilishi kerak


    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"
