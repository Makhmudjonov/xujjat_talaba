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

class University(models.Model):
    name = models.CharField(max_length=255)

    history = HistoricalRecords()

    def __str__(self):
        return self.name
    
class Faculty(models.Model):
    hemis_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, null=True, blank=True)

    history = HistoricalRecords()

    # class Meta:
    #     unique_together = ('hemis_id', 'name')

    def __str__(self):
        return f"{self.name} ({self.hemis_id})"


    
class Universitya(models.Model):
    name = models.CharField(max_length=255)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Level(models.Model):
    """Bakalavr 1‑kurs / Magistr 2‑kurs va hokazo."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    history = HistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kurs / Bosqich"
        verbose_name_plural = "Kurs / Bosqichlar"


# ---------------------------
# STUDENT & ACADEMIC DATA
# ---------------------------
class Student(models.Model):
    toifa = models.BooleanField(default=False)
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
    university1 = models.ForeignKey(University, null=True, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    history = HistoricalRecords()


    @property
    def gpa(self):
        latest = self.gpa_records.order_by('-created_at').first()
        return latest.gpa if latest else None
    
    def get_latest_gpa(self):
        latest = self.gpa_records.order_by("-education_year").first()
        return latest.gpa if latest else None

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

    history = HistoricalRecords()

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
    gpa = models.FloatField(null=True)
    debit = models.BigIntegerField(null=True, blank=True)
    credit = models.BigIntegerField(null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.student.full_name} - {self.contract_number}"


# ---------------------------
# COMPETITION STRUCTURE
# ---------------------------
class Section(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Direction(models.Model):
    DIRECTION_TYPE_CHOICES = [
        ("file", "File"),
        ("test", "Test"),
        ("gpa", "GPA"),
        ("toifa", "Reestr"),
    ]

    section = models.ForeignKey("Section", on_delete=models.CASCADE, related_name="directions")
    name = models.CharField(max_length=255)
    direction_type = models.CharField(max_length=10, choices=DIRECTION_TYPE_CHOICES, default="file")
    require_file = models.BooleanField(default=True)  # faqat `file` uchun
    test = models.ForeignKey("Test", null=True, blank=True, on_delete=models.SET_NULL)
    min_score = models.FloatField(default=0)
    max_score = models.FloatField(default=10)
    type = models.CharField(max_length=10, choices=DIRECTION_TYPE_CHOICES, default='file')

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.section.name} / {self.name}"

    def get_score(self, obj):
        student = self.context.get("student")
        if not student:
            return None

        item = ApplicationItem.objects.filter(
            direction=obj,
            application__student=student
        ).first()

        if item and item.score_set.exists():
            return item.score_set.first().value
        return None


# ---------------------------
# APPLICATION & EVALUATION
# ---------------------------
class ApplicationType(models.Model):
    ACCESS_CHOICES = [
        ('universal', 'Hamma talabalar uchun'),
        ('min_gpa', 'GPA talab'),
        ('special_list', 'Faqat maxsus ro‘yxatdagi talabalar'),
        ('maxsus', 'Ijtimoiy ximoya reestridagi talabalar'),
    ]

    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='application_types/', blank=True, null=True)

    min_gpa = models.FloatField(blank=True, null=True)
    allowed_levels = models.ManyToManyField(Level, blank=True)
    access_type = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='universal')

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    def is_active(self):
        now = timezone.now()
        if not self.start_time and not self.end_time:
            return True
        if self.start_time and not self.end_time:
            return self.start_time <= now
        if not self.start_time and self.end_time:
            return now <= self.end_time
        return self.start_time <= now <= self.end_time

    @property
    def maxsus(self):
        return self.access_type in ['maxsus']

    def __str__(self):
        return self.name


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
    # direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='applications')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='applications')
    comment = models.TextField(blank=True, null=True)
    status    = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)  # yoki shunga o‘xshash
    application_type = models.ForeignKey(ApplicationType, on_delete=models.CASCADE, related_name='applications')

    history = HistoricalRecords()


    # class Meta:
    #     unique_together = ('student', 'application_type')  # ✅ faqat 1 marta topshiradi



def application_file_upload_path(instance, filename):
    # Determine section safely
    section = None
    try:
        section = instance.section
    except Exception:
        pass

    if not section and getattr(instance, 'section_id', None):
        from .models import Section
        try:
            section = Section.objects.get(pk=instance.section_id)
        except Section.DoesNotExist:
            section = None

    # ✅ Aslida application bu yerda item orqali olinadi
    application = getattr(instance, 'item', None)
    student = application.application.student if application else None

    if student:
        full_name_slug = student.full_name.replace(" ", "_").replace(".", "").lower()
        student_id = student.student_id_number
    else:
        full_name_slug = "unknown_user"
        student_id = "unknown"

    section_name_slug = section.name.replace(" ", "_").lower() if section else ""

    base, ext = os.path.splitext(filename)
    new_filename = f"{student_id}-{base}{ext}"

    return os.path.join(
        'applications',
        full_name_slug,
        section_name_slug,
        new_filename
    )

class ApplicationItem(models.Model):
    application      = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='items')
    direction        = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='application_items')
    title            = models.CharField(max_length=255)
    student_comment  = models.TextField(blank=True, null=True)
    reviewer_comment = models.TextField(blank=True, null=True)
    file             = models.FileField(upload_to='application_items/', blank=True, null=True)
    gpa              = models.FloatField(blank=True, null=True)
    gpa_score = models.FloatField(blank=True, null=True)
    test_result      = models.FloatField(blank=True, null=True)  # or IntegerField if needed
    status = models.BooleanField(default=False)

    history = HistoricalRecords()
    
    class Meta:
        unique_together = ('application', 'direction')

class ApplicationFile(models.Model):
    item = models.ForeignKey(ApplicationItem, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=application_file_upload_path, max_length=255)  # ✅ Fayl yuklash yo‘li
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='application_files')
    comment = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # application_item = models.ForeignKey(
    #     ApplicationItem, on_delete=models.CASCADE, related_name="application_files"
    # )

    history = HistoricalRecords()

    def __str__(self):
        return f"File for  - {self.section.name}"


class Score(models.Model):
    item = models.OneToOneField(ApplicationItem, on_delete=models.CASCADE, related_name='score')
    reviewer = models.ForeignKey("CustomAdminUser", on_delete=models.SET_NULL, null=True)
    value = models.FloatField()
    note = models.TextField(blank=True)
    scored_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['item'], name='unique_score_per_application_item')
        ]

    def __str__(self):
        return f"Application #{self.item.application.id} - {self.value} ball"

class Roles:
    STUDENT = "student"
    ADMIN = "admin"
    DEKAN = "dekan"
    KICHIK_ADMIN = "kichik_admin"

    CHOICES = (
        (STUDENT, "Student"),
        (ADMIN, "Admin"),
        (DEKAN, "Dekan"),
        (KICHIK_ADMIN, "Kichik Admin"),
    )

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
    can_score = models.BooleanField(default=True, help_text="Agar true bo‘lsa, admin baho qo‘yishi mumkin.")
    university1 = models.ForeignKey(University, null=True, on_delete=models.CASCADE)
    full_name = models.CharField(blank=True, null=True)
    

    limit_by_course = models.BooleanField(default=False)
    allow_all_students = models.BooleanField(default=False)

    history = HistoricalRecords()

    USERNAME_FIELD = 'username'

    # users/models.py (yoki qayerda bo‘lsa)
    def has_access_to(self, direction):
        if self.allow_all_students:
            return True

        return (
            self.directions.filter(id=direction.id).exists()
            or self.sections.filter(id=direction.section_id).exists()
     )




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




class SpecialApplicationStudent(models.Model):
    """
    Aynan shu ApplicationType uchun ariza berishi mumkin bo‘lgan talaba
    (HEMIS ID bo‘yicha).
    """

    history = HistoricalRecords()

    application_type = models.ForeignKey(
        ApplicationType,
        on_delete=models.CASCADE,
        related_name='special_students'
    )
    hemis_id = models.CharField(max_length=20)

    # Agar Student obyekti bazada bo‘lsa, bog‘lab qo‘yish qulay bo‘ladi
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text="Opsional: Student modeli bilan bog‘lash"
    )

    class Meta:
        unique_together = ('application_type', 'hemis_id')
        verbose_name = "Maxsus talaba"
        verbose_name_plural = "Maxsus talabalar"

    def __str__(self):
        return f"{self.hemis_id} → {self.application_type}"
    

#TEST SINOVLARI UCHUN MODELLAR
# models.py

class Test(models.Model):
    title = models.CharField(max_length=255)
    question_count = models.IntegerField(default=25)
    time_limit = models.IntegerField(help_text="daqiqada")  # Masalan, 30 daqiqa
    levels = models.ManyToManyField(Level, related_name="tests")   # 🆕
    start_time = models.DateTimeField(null=True, blank=True)  # 🆕 Yangi qo‘shildi
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.title


class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    correct_option = models.CharField(max_length=1)  # "A", "B", "C", "D"

    history = HistoricalRecords()
    

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=1)  # "A", "B", "C", "D"
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    history = HistoricalRecords()

class TestSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    correct_answers = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField(null=True, blank=True)
    questions = models.ManyToManyField(Question, blank=True)
    current_question_index = models.IntegerField(default=0,)  # New field to track progress

    history = HistoricalRecords()

    def is_expired(self):
        if self.finished_at:
            return False
        end_time = self.started_at + timezone.timedelta(minutes=self.test.time_limit)
        return timezone.now() >= end_time
    
    def finish_and_score(self):
        if not self.finished_at:
            self.finished_at = timezone.now()

        total = self.questions.count()
        correct = self.answers.filter(is_correct=True).count()

        self.correct_answers = correct
        self.total_questions = total
        self.score = round((correct / total) * 100, 2) if total else 0
        self.save()
    

    class Meta:
        unique_together = ("student", "test")  #🚨 Bu yerda cheklov


class Answer(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE)
    is_correct = models.BooleanField()

    history = HistoricalRecords()


class OdobAxloqStudent(models.Model):
    sabab = models.CharField(max_length=500)
    hemis_id = models.CharField(max_length=20)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.hemis_id} ({self.sabab})"
