from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from apps.models import (
    Application, ApplicationItem, Score, Faculty, Level, Student, Direction, Section
)
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
        self._user = user
        self._komissiya = komissiya

        return {
            'access': str(refresh.access_token),
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


class ScoreSerializer(serializers.ModelSerializer):
    MIN_VALUE = 0
    MAX_VALUE = 10

    class Meta:
        model = Score
        fields = ["id", "item", "value", "note", "scored_at"]
        read_only_fields = ["id", "item", "scored_at"]
        ref_name = "KomissiyaScore"

    def validate_value(self, value):
        if not (self.MIN_VALUE <= value <= self.MAX_VALUE):
            raise serializers.ValidationError(
                f"Ball {self.MIN_VALUE}–{self.MAX_VALUE} oralig‘ida bo‘lishi kerak."
            )
        return value

    def validate(self, data):
        item = self.context.get("item")
        if Score.objects.filter(item=item).exists():
            raise serializers.ValidationError("Bu forma allaqachon baholangan.")
        return data

    def create(self, validated_data):
        item = self.context.get("item")
        reviewer = self.context["request"].user
        return Score.objects.create(
            item=item,
            reviewer=reviewer,
            **validated_data
        )


class ApplicationItemSerializer(serializers.ModelSerializer):
    direction_name = serializers.CharField(source="direction.name", read_only=True)
    section_name = serializers.CharField(source="section.name", read_only=True)
    score = ScoreSerializer(read_only=True)

    class Meta:
        model = ApplicationItem
        fields = ["id", "direction", "direction_name", "section", "section_name", "comment", "score"]
