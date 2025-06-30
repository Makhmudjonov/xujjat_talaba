from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from simple_history.models import HistoricalRecords
from django.contrib.auth import get_user_model

User = get_user_model()


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
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)


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
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="applications")
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name="applications")
    submitted_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


    class Meta:
        unique_together = ('student', 'direction')  # faqat bitta ariza per direction

    def __str__(self):
        return f"{self.student.full_name if self.student else '---'} - {self.direction.name if self.direction else '---'}"



class ApplicationFile(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to="applications/")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='application_files')
    comment = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.application} - {self.section.name}"


class Score(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="scores")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="scores")
    reviewer = models.ForeignKey("CustomAdminUser", on_delete=models.SET_NULL, null=True)
    value = models.FloatField()
    note = models.TextField(blank=True)
    scored_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('application', 'section')

    def __str__(self):
        return f"{self.application} - {self.section.name} - {self.value} ball"


class CustomAdminUser(AbstractUser):
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

