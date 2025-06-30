from rest_framework import serializers
from .models import (
    Level, Section, Direction, Application, ApplicationFile,
    Score, CustomAdminUser, Student, GPARecord
)


# --- 1. Student Login ---
class StudentLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField()






# --- 4. Section + Nested Directions (Frontendga ko‘rsatish uchun) ---
class DirectionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = ['id', 'name', 'require_file', 'min_score', 'max_score']



# --- 5. Application Fayllari ---
class ApplicationFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationFile
        fields = ['id', 'file_url', 'comment', 'section']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name']

class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = "__all__"
        ref_name = "AppScore"  # yoki 'ScoreInApp'

class DirectionSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)

    class Meta:
        model = Direction
        fields = ['id', 'name', 'require_file', 'min_score', 'max_score', 'section']

class ApplicationSerializer(serializers.ModelSerializer):
    direction = DirectionSerializer(read_only=True)
    scores = ScoreSerializer(many=True, read_only=True)  # OneToOne munosabat bo'lsa ishlaydi
    
    files = ApplicationFileSerializer(many=True, read_only=True)
    comment = serializers.CharField()  # Agar modelda mavjud bo'lsa

    class Meta:
        model = Application
        fields = ['id', 'student', 'direction', 'submitted_at', 'status', 'comment', 'scores', 'files']

class ApplicationNestedSerializer(serializers.ModelSerializer):
    files = ApplicationFileSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'status', 'comment', 'files']


class DirectionWithApplicationSerializer(DirectionSerializer):
    application = serializers.SerializerMethodField()

    class Meta(DirectionSerializer.Meta):
        fields = DirectionSerializer.Meta.fields + ['application']

    def get_application(self, obj):
        user = self.context['request'].user
        student = getattr(user, 'student', None)
        if not student:
            return None
        app = Application.objects.filter(direction=obj, student=student).first()
        if app:
            return ApplicationNestedSerializer(app, context=self.context).data
        return None


# serializers.py
# serializers.py

class ApplicationFileInlineSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = ApplicationFile
        fields = ['section', 'comment']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'direction', 'submitted_at', 'status']
        read_only_fields = ['id', 'submitted_at', 'status']



# --- 9. Admin foydalanuvchi ---
class CustomAdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomAdminUser
        fields = '__all__'


# --- 10. Level ---
class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = "__all__"


class SubmitMultipleApplicationsSerializer(serializers.Serializer):
    """
    Frontenddan keladigan POST ma'lumotlari uchun serializer.
    applications_data — JSON string ko‘rinishida bo‘ladi,
    unda arizalar ro‘yxati joylashgan.
    Fayllar esa alohida `request.FILES` orqali olinadi.
    """
    applications_data = serializers.CharField(
        help_text='JSON string representing a list of applications with direction_id, comment, and file_key.'
    )

class SingleApplicationSerializer(serializers.Serializer):
    direction_id = serializers.IntegerField()
    comment      = serializers.CharField(required=False, allow_blank=True)
    file_key     = serializers.CharField(required=False, allow_blank=True)


class GPARecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GPARecord
        fields = [
            "education_year", "level", "gpa", "credit_sum",
            "subjects", "debt_subjects", "can_transfer", "method", "created_at"
        ]

class StudentAccountSerializer(serializers.ModelSerializer):
    gpa_records = GPARecordSerializer(many=True, read_only=True)
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    level_name = serializers.CharField(source='level.name', read_only=True)

    class Meta:
        model = Student
        fields = [
            "student_id_number", "full_name", "short_name", "email", "phone",
            "image", "gender", "birth_date", "address", "university", "faculty_name",
            "group", "level_name", "gpa_records"
        ]