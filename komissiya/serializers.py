from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from apps.models import Application, Faculty, Level, Score, Student
from .models import KomissiyaMember
from django.contrib.auth import get_user_model

User = get_user_model()

class KomissiyaLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    komissiya = serializers.SerializerMethodField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Login yoki parol noto‘g‘ri")

        try:
            komissiya = KomissiyaMember.objects.get(user=user)
        except KomissiyaMember.DoesNotExist:
            raise serializers.ValidationError("Komissiya a'zosi emas")

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        # Saqlaymiz, keyin SerializerMethodField ishlatamiz
        self._user = user
        self._komissiya = komissiya
        self._access = access
        self._refresh = str(refresh)

        return {
            'access': access,
            'refresh': str(refresh),
        }

    def get_user(self, obj):
        user = getattr(self, '_user', None)
        if not user:
            return None
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
        }

    def get_komissiya(self, obj):
        komissiya = getattr(self, '_komissiya', None)
        if not komissiya:
            return None
        return {
            'role': komissiya.role,
            'faculty': komissiya.faculty.name if komissiya.faculty else None,
            'direction': komissiya.direction.name if komissiya.direction else None,
            'section': komissiya.section.name if komissiya.section else None,
            'course': komissiya.course.name if komissiya.course else None,
        }



class ApplicationSerializer(serializers.ModelSerializer):
    score = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ["id", "direction", "comment", "status", "score"]

    def get_score(self, obj):
        score = obj.scores.first()
        return score.value if score else None


class ScoreSerializer(serializers.ModelSerializer):
    MIN_VALUE = 0
    MAX_VALUE = 10

    class Meta:
        model = Score
        fields = ["id", "application", "value", "note", "scored_at"]
        read_only_fields = ["id", "application", "scored_at"]
        ref_name = "KomissiyaScore"

    def validate_value(self, value):
        if not (self.MIN_VALUE <= value <= self.MAX_VALUE):
            raise serializers.ValidationError(
                f"Ball {self.MIN_VALUE}–{self.MAX_VALUE} oralig‘ida bo‘lishi kerak."
            )
        return value

    def validate(self, data):
        application = self.context.get("application")
        if Score.objects.filter(application=application).exists():
            raise serializers.ValidationError("Bu ariza allaqachon baholangan.")
        return data

    def create(self, validated_data):
        application = self.context.get("application")
        reviewer = self.context["request"].user
        return Score.objects.create(
            application=application,
            reviewer=reviewer,
            **validated_data
        )


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'code', 'name']


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name', 'code']


class StudentSerializer(serializers.ModelSerializer):
    faculty = FacultySerializer()
    level = LevelSerializer()

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'faculty', 'level', 'group', 'email', 'phone']
