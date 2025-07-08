import json
import random
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist


from komissiya.serializers import StudentSerializer
from .models import (
    ApplicationItem, ApplicationType, Level, Question, Section, Direction, Application, ApplicationFile,
    Score, CustomAdminUser, Student, GPARecord, Test, TestSession, Option
)

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate


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
    file_url = serializers.SerializerMethodField(read_only=True)
    application_id = serializers.SerializerMethodField(read_only=True)
    application_title = serializers.SerializerMethodField(read_only=True)
    

    class Meta:
        model = ApplicationFile
        fields = [
            'id',
            'file',
            'file_url',
            'comment',
            'section',
            'application_id',      # ✅ qo‘shildi
            'application_title',   # ✅ qo‘shildi
        ]
        extra_kwargs = {
            'file': {'required': False, 'allow_null': True},
            'comment': {'required': False, 'allow_blank': True},
            'section': {'required': False, 'allow_null': True},
        }

    def get_file_url(self, obj):
        request = self.context.get('request')  # bu yerda request kerak
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


    def get_application_id(self, obj):
        return obj.item.application.id if obj.item and obj.item.application else None

    def get_application_title(self, obj):
        return obj.item.application.application_type.name if obj.item and obj.item.application else None



class ScoreSerializer(serializers.ModelSerializer):

    def validate(self, data):
        user = self.context["request"].user
        item = data["item"]

        if not hasattr(user, "has_access_to") or not user.has_access_to(item):
            raise serializers.ValidationError("Siz bu arizani baholash huquqiga ega emassiz.")

        if Score.objects.filter(item=item).exists():
            raise serializers.ValidationError("Bu arizaga allaqachon baho qo‘yilgan.")

        if item.application.status != "pending":
            raise serializers.ValidationError("Faqat pending holatdagi arizalarga baho qo‘yish mumkin.")

        return data

    class Meta:
        model = Score
        fields = ['id', 'value', 'note', 'scored_at']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name']

class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = "__all__"
        ref_name = "AppScore"  # yoki 'ScoreInApp'

class SectionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Section
        fields = ["id", "name"]


class DirectionSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    gpa = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    test_result = serializers.SerializerMethodField()

    class Meta:
        model = Direction
        fields = [
            'id', 'name', 'type', 'require_file',
            'gpa', 'score', 'test_result',
            'min_score', 'max_score', 'section'
        ]

    def get_type(self, obj):
        if obj.test:
            return "test"
        return "score"

    def get_gpa(self, obj):
        student = self.context.get("student")
        if obj.name.lower().startswith("gpa") or "gpa" in obj.name.lower():
            return student.gpa if student else None
        return None

    def get_score(self, obj):
        student = self.context.get("student")
        if not student:
            return None

        # Bu yerda ApplicationItem modeliga to‘g‘ridan to‘g‘ri murojaat qilinadi
        item = ApplicationItem.objects.filter(
            direction=obj,
            application__student=student
        ).first()

        if item and item.score_set.exists():
            return item.score_set.first().value
        return None

    def get_test_result(self, obj):
        student = self.context.get("student")
        if obj.test and student:
            session = TestSession.objects.filter(student=student, test=obj.test).first()
            return session.score if session else None
        return None

class ApplicationItemSerializer(serializers.ModelSerializer):
    files = ApplicationFileSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicationItem
        fields = [
            "id", "application", "direction", "title", "student_comment",
            "reviewer_comment", "file", "gpa", "test_result", "files"
        ]


    def create(self, validated_data):
        gpa = validated_data.pop("gpa", None)
        test_result = validated_data.pop("test_result", None)

        direction = validated_data.get("direction")

        if direction:
            if hasattr(direction, "type"):
                if direction.type == "gpa":
                    validated_data["gpa"] = gpa
                elif direction.type == "test":
                    validated_data["test_result"] = test_result
            else:
                validated_data["gpa"] = gpa
                validated_data["test_result"] = test_result

        return super().create(validated_data)


class ApplicationSerializer(serializers.ModelSerializer):
    items = ApplicationItemSerializer(many=True)

    class Meta:
        model = Application
        fields = ['id', 'student', 'application_type', 'submitted_at', 'status', 'comment', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")

        application = Application.objects.create(**validated_data)

        for item_data in items_data:
            files_data = item_data.pop("files", [])
            item = ApplicationItem.objects.create(application=application, **item_data)

            for file in files_data:
                ApplicationFile.objects.create(item=item, comment=file.get("comment", ""), section_id=file["section"])

        return application


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


class ApplicationTypeSerializer(serializers.ModelSerializer):
    can_apply = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    student_gpa = serializers.SerializerMethodField()
    student_level = serializers.SerializerMethodField()
    allowed_levels = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = ApplicationType
        fields = [
            'id', 'name', 'subtitle', 'image', 'min_gpa',
            'access_type', 'allowed_levels',
            'can_apply', 'reason', 'student_gpa', 'student_level'
        ]

    def get_student_gpa(self, obj):
        student = self.context.get('student')
        return float(student.gpa or 0)

    def get_student_level(self, obj):
        student = self.context.get('student')
        # Bu sizning modelga bog‘liq, agar `student.level.name` bo‘lsa:
        return student.level.name if student.level else None

    def get_can_apply(self, obj):
        student = self.context.get('student')
        return self._check_eligibility(student, obj)[0]

    def get_reason(self, obj):
        student = self.context.get('student')
        return self._check_eligibility(student, obj)[1]

    def _check_eligibility(self, student, appl_type):
        gpa = float(student.gpa or 0)
        if appl_type.min_gpa and gpa < appl_type.min_gpa:
            return False, f"GPA talab qilinadi: {appl_type.min_gpa} dan yuqori"

        if appl_type.access_type == 'universal':
            return True, None

        elif appl_type.access_type == 'min_gpa':
            return True, None

        elif appl_type.access_type == 'disabled_only':
            if not student.is_disabled:
                return False, "Faqat nogiron talabalar uchun"

        elif appl_type.access_type == 'special_list':
            if not appl_type.special_students.filter(student=student).exists():
                return False, "Faqat maxsus ro‘yxatdagi talabalar uchun"

        return True, None


class ApplicationItemAdminSerializer(serializers.ModelSerializer):
    direction = DirectionSerializer()
    section = SectionSerializer()
    files = ApplicationFileSerializer(many=True, read_only=True)
    score = ScoreSerializer(read_only=True)
    student = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationItem
        fields = ['id', 'student', 'direction', 'section', 'files', 'score']

    def get_student(self, obj):
        return StudentSerializer(obj.application.student).data


class ApplicationFileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationFile
        fields = ['file', 'comment', 'section']

class ApplicationItemCreateSerializer(serializers.ModelSerializer):
    files = ApplicationFileCreateSerializer(many=True, required=False)
    direction = serializers.PrimaryKeyRelatedField(queryset=Direction.objects.all())

    class Meta:
        model = ApplicationItem
        fields = ['direction', 'student_comment', 'files']
        ref_name = 'AppItemCreate'  # Qo‘shildi

    def validate(self, data):
        direction = data.get('direction')
        files = data.get('files', [])

        # EHTIYOT SHAKLI: direction instance ekanligini tekshiramiz
        if isinstance(direction, Direction):
            if direction.require_file and not files:
                raise serializers.ValidationError({
                    'files': 'Ushbu yo‘nalish uchun fayl yuklash majburiy.'
                })
        return data




class ApplicationCreateSerializer(serializers.ModelSerializer):
    items = ApplicationItemCreateSerializer(many=True)

    class Meta:
        model = Application
        fields = ['application_type', 'comment', 'items']

    def create(self, validated_data):
        request = self.context["request"]
        student = request.user.student
        admin_user = request.user

        items_data = validated_data.pop("items")
        application = Application.objects.create(student=student, **validated_data)

        for idx, item_data in enumerate(items_data):
            files_data = item_data.pop("files", [])
            gpa = item_data.pop("gpa", None)
            test_result = item_data.pop("test_result", None)

            direction = item_data["direction"]
            item = ApplicationItem.objects.create(
                application=application,
                title=direction.name,
                **item_data
            )

            # score
            score_value = gpa if gpa is not None else test_result
            if score_value is not None:
                Score.objects.create(item=item, reviewer=admin_user, value=score_value)

            # Fayl olish: `files_0_0`, `files_1_0`, ...
            for f_idx in range(5):
                file_key = f"files_{idx}_{f_idx}"
                uploaded_file = request.FILES.get(file_key)
                if uploaded_file:
                    ApplicationFile.objects.create(
                        item=item,
                        file=uploaded_file,
                        comment="",
                        section=files_data[f_idx]["section"] if f_idx < len(files_data) else None,
                    )


        return application
    

class ApplicationFileShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationFile
        fields = ("id", "file", "comment", "section")


class ApplicationItemFullSerializer(serializers.ModelSerializer):
    direction_name = serializers.CharField(source="direction.name", read_only=True)
    score          = ScoreSerializer(read_only=True)          # all fields
    files          = ApplicationFileShortSerializer(many=True, read_only=True)

    class Meta:
        model  = ApplicationItem
        fields = (
            "id",
            "direction_name",
            "student_comment",
            "reviewer_comment",
            "score",
            "files",
        )

class StudentShortSerializer(serializers.ModelSerializer):
    faculty = serializers.CharField(source="faculty.name")
    level = serializers.CharField(source="level.name")

    class Meta:
        model = Student
        fields = ("id", "full_name", "student_id", "faculty", "level")



class ScoreShortSerializer(serializers.ModelSerializer):
    reviewer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Score
        fields = ("id", "value", "note", "reviewer_name", "scored_at")

class ScoreCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ("item", "value", "note")

    def validate(self, data):
        if Score.objects.filter(item=data["item"]).exists():
            raise serializers.ValidationError("Bu arizaga allaqachon baho qo‘yilgan.")
        if data["item"].application.status != "pending":
            raise serializers.ValidationError("Faqat pending holatdagi arizalarga baho qo‘yish mumkin.")
        return data

    def create(self, validated_data):
        request = self.context["request"]
        
        # reviewer validated_data ichida bo‘lsa, olib tashlaymiz
        validated_data.pop("reviewer", None)

        return Score.objects.create(
            reviewer=request.user,
            **validated_data
        )

    


class ApplicationStudentSerializer(serializers.ModelSerializer):
    gpa_records = GPARecordSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ["id", "full_name", "student_id_number", "faculty", "level", "gpa_records"]

    # def get_latest_gpa(self, obj):
    #     record = obj.gpa_records.order_by("-updated_at").first()
    #     return float(record.gpa) if record else None


class ApplicationFullSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    student = ApplicationStudentSerializer(read_only=True)
    application_type_name = serializers.CharField(source="application_type.title", read_only=True)

    class Meta:
        model = Application
        fields = ("id", "status", "comment", "submitted_at", "application_type_name", "student", "items")

    def get_items(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        items = obj.items.all()

        if user and user.directions.exists():
            items = items.filter(direction__in=user.directions.all())

        return ApplicationItemFullSerializer(items, many=True, context=self.context).data



class AdminUserSerializer(serializers.ModelSerializer):
    sections = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    directions = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    faculties = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    levels = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = CustomAdminUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'sections', 'directions', 'faculties', 'levels',
            'limit_by_course', 'allow_all_students'
        ]


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    # ↓ qo‘shimcha: foydalanuvchi obyektini va JWT’ni qaytaramiz
    def validate(self, attrs):
        user = authenticate(
            username=attrs["username"],
            password=attrs["password"]
        )
        if user is None:
            raise serializers.ValidationError("Login yoki parol noto‘g‘ri")

        # faqat admin turidagi foydalanuvchilar kirsin
        if user.role not in ("admin", "dekan", "kichik_admin"):
            raise serializers.ValidationError("Bu foydalanuvchi admin emas")

        refresh = RefreshToken.for_user(user)
        attrs["user"]    = user
        attrs["access"]  = str(refresh.access_token)
        attrs["refresh"] = str(refresh)
        return attrs
    



class ApplicationDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    student = ApplicationStudentSerializer(read_only=True)
    application_type_name = serializers.CharField(source="application_type.title", read_only=True)

    class Meta:
        model = Application
        fields = ("id", "status", "comment", "submitted_at", "application_type_name", "student", "items")

    def get_items(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        items = obj.items.all()

        # Faqat adminlar uchun direction bo‘yicha filterlash
        if user and user.role in ["dekan", "admin", "kichik_admin"] and user.directions.exists():
            items = items.filter(direction__in=user.directions.all())

        return ApplicationItemFullSerializer(items, many=True, context=self.context).data



#TEST SAVOLLARI UCHUN SERIALIZER

class StartTestSerializer(serializers.Serializer):
    test_id = serializers.IntegerField()

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "label", "text"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'options']

    def get_options(self, obj):
        return [{"id": opt.id, "text": opt.text} for opt in obj.answeroption_set.all()]

class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.IntegerField()

class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSession
        fields = [
            'id',
            'started_at',
            'finished_at',
            'score',
            'correct_answers',
            'total_questions',
        ]


class QuizUploadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    levels = serializers.CharField()            # JSON array satr ko‘rinishida keladi
    file = serializers.FileField()

    def validate_levels(self, value: str):
        try:
            level_ids = json.loads(value)       # "[1,2]" → [1, 2]
            assert isinstance(level_ids, list)
        except Exception:
            raise serializers.ValidationError("levels must be JSON array, masalan: [1,2]")
        missing = [pk for pk in level_ids if not Level.objects.filter(id=pk).exists()]
        if missing:
            raise serializers.ValidationError(f"Level ID topilmadi: {missing}")
        return level_ids

class TestSerializer(serializers.ModelSerializer):
    total_questions = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            "id", "title", "start_time", "question_count",
            "total_questions", "time_limit", "created_at",
            "status", "result"
        ]

    def get_total_questions(self, obj):
        return obj.questions.count()

    def get_status(self, obj):
        request = self.context.get("request")
        student = getattr(request.user, "student", None)
        if not student:
            return "unknown"

        has_session = obj.testsession_set.filter(student=student).exists()
        return "ishlangan" if has_session else "ishlanmagan"

    def get_result(self, obj):
        request = self.context.get("request")
        student = getattr(request.user, "student", None)
        if not student:
            return None

        session = obj.testsession_set.filter(student=student).first()
        if session and session.score is not None:
            return {
                "score": session.score,
                "correct": session.correct_answers,
                "total": session.total_questions
            }
        return None



class RandomizedQuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model  = Question
        fields = ("id", "text", "options")

    def get_options(self, obj):
        opts = list(obj.options.all())          # related_name="options"
        random.shuffle(opts)                    # variantlar aralashadi
        return OptionSerializer(opts, many=True).data
    
