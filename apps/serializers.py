from rest_framework import serializers
from .models import (
    Level, Section, Direction, Application, ApplicationFile,
    Score, CustomAdminUser
)


# --- 1. Student Login ---
class StudentLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField()


# --- 2. Section ---
class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name']


# --- 3. Direction (Section nomi bilan chiqishi uchun) ---
class DirectionSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)

    class Meta:
        model = Direction
        fields = ['id', 'name', 'require_file', 'min_score', 'max_score', 'section']


# --- 4. Section + Nested Directions (Frontendga ko‘rsatish uchun) ---
class DirectionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = ['id', 'name', 'require_file', 'min_score', 'max_score']


class SectionWithDirectionsSerializer(serializers.ModelSerializer):
    directions = DirectionMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'name', 'directions']


# --- 5. Application Fayllari ---
class ApplicationFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationFile
        fields = '__all__'


# --- 6. Application (ko‘rish uchun) ---
class ApplicationSerializer(serializers.ModelSerializer):
    files = serializers.PrimaryKeyRelatedField(
        queryset = ApplicationFile.objects.all(),
        many=True,
        required=False
    )
    direction = DirectionSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'direction', 'files']
        # read_only_fields = ['id', 'submitted_at', 'status', 'files']



# serializers.py
# serializers.py

class ApplicationFileInlineSerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=True)

    class Meta:
        model = ApplicationFile
        fields = ['section', 'file', 'comment']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    files = ApplicationFileInlineSerializer(many=True, write_only=True)  # ✅


    class Meta:
        model = Application
        fields = ['direction', 'files']

    def create(self, validated_data):
        files_data = validated_data.pop('files')
        application = Application.objects.create(
            student=self.context['request'].user.student,
            direction=validated_data['direction']
        )
        for file_data in files_data:
            ApplicationFile.objects.create(application=application, **file_data)
        return application



# --- 8. Score ---
class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = '__all__'


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
