from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from core import settings
from simple_history.models import HistoricalRecords
# from django.contrib.auth import get_user_model
import os

# User = get_user_model()


# ---------------------------
# CORE REFERENCE MODELS
# ---------------------------
class Faculty(models.Model):
    hemis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Level(models.Model):
    """Bakalavr 1‑kurs / Magistr 2‑kurs va hokazo."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kurs / Bosqich"
        verbose_name_plural = "Kurs / Bosqichlar"


# ---------------------------
# STUDENT & ACADEMIC DATA
# ---------------------------
class Student(models.Model):
    student_id_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    birth_date = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    university = models.CharField(max_length=255)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)


    def __str__(self):
        return self.full_name


class GPARecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='gpa_records')
    education_year = models.CharField(max_length=20)
    level = models.CharField(max_length=50)
    gpa = models.CharField(max_length=10)
    credit_sum = models.FloatField()
    subjects = models.IntegerField()
    debt_subjects = models.IntegerField()
    can_transfer = models.BooleanField(default=False)
    method = models.CharField(max_length=50)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.student.full_name} - {self.education_year} ({self.level})"


class ContractInfo(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='contract_info')
    contract_number = models.CharField(max_length=100)
    contract_date = models.DateField()
    edu_organization = models.CharField(max_length=255)
    edu_speciality = models.CharField(max_length=255)
    edu_period = models.IntegerField()
    edu_year = models.CharField(max_length=100)
    edu_type = models.CharField(max_length=100)
    edu_form = models.CharField(max_length=100)
    edu_course = models.CharField(max_length=50)
    contract_type = models.CharField(max_length=100)
    pdf_link = models.URLField()
    contract_sum = models.BigIntegerField()
    gpa = models.FloatField()
    debit = models.BigIntegerField(null=True, blank=True)
    credit = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.contract_number}"


# ---------------------------
# COMPETITION STRUCTURE
# ---------------------------
class Section(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Direction(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="directions")
    name = models.CharField(max_length=255)
    require_file = models.BooleanField(default=True)
    min_score = models.FloatField(default=0)
    max_score = models.FloatField(default=10)

    def __str__(self):
        return f"{self.section.name} / {self.name}"


# ---------------------------
# APPLICATION & EVALUATION
# ---------------------------
class Application(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_REVIEWED = 'reviewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    student   = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='applications')
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='applications')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='applications')
    comment = models.TextField(blank=True, null=True)
    status    = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)  # yoki shunga o‘xshash


    class Meta:
        unique_together = ('student', 'direction')   # <- 1 yo‘nalish‑1 student



def application_file_upload_path(instance, filename):
    # Bu funksiya avvalgi javobda berilgan kodga o'xshash bo'ladi
    full_name_slug = instance.application.student.full_name.replace(" ", "_").replace(".", "").lower()
    section_name_slug = instance.section.name.replace(" ", "_").lower()
    direction_name_slug = instance.application.direction.name.replace(" ", "_").lower()
    student_id_number = instance.application.student.student_id_number

    base, ext = os.path.splitext(filename)
    new_filename = f"{student_id_number}-{base}{ext}"

    return os.path.join(
        'applications',
        full_name_slug,
        section_name_slug,
        direction_name_slug,
        new_filename
    )

# ... (modellar) ...

class ApplicationFile(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=application_file_upload_path) # <-- Shu yerda o'zgartirish
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='application_files')
    comment = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.application} - {self.section.name}"


class Score(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="scores")
    reviewer = models.ForeignKey("CustomAdminUser", on_delete=models.SET_NULL, null=True)
    value = models.FloatField()
    note = models.TextField(blank=True)
    scored_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['application'], name='unique_score_per_application')
        ]

    def __str__(self):
        return f"Application #{self.application.id} - {self.value} ball"


class CustomAdminUser(AbstractUser):

    ROLE_CHOICES = (
        ("student", "Student"),
        ("admin", "Admin"),
        ("dekan", "Dekan"),
        ("kichik_admin", "Kichik Admin"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    sections = models.ManyToManyField(Section, blank=True, related_name='admins')
    directions = models.ManyToManyField(Direction, blank=True, related_name='admins')
    faculties = models.ManyToManyField(Faculty, blank=True, related_name='admins')
    levels = models.ManyToManyField(Level, blank=True, related_name='admins')

    limit_by_course = models.BooleanField(default=False)
    allow_all_students = models.BooleanField(default=False)

    # ✅ Override groups va user_permissions uchun related_name beramiz
    groups = models.ManyToManyField(
        Group,
        related_name='custom_admin_user_set',
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_admin_user_set',
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
    )

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

