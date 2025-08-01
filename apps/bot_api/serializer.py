from rest_framework import serializers
from apps.models import Student, Application, ApplicationItem, Direction, ApplicationFile

class ApplicationFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationFile
        fields = ['id', 'file', 'section', 'comment', 'uploaded_at']


class DirectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direction
        fields = ['id', 'name', 'type']


class ApplicationItemSerializer(serializers.ModelSerializer):
    files = ApplicationFileSerializer(many=True, read_only=True, source='files')

    class Meta:
        model = ApplicationItem
        fields = [
            'id',
            'direction',
            'title',
            'student_comment',
            'reviewer_comment',
            'file',
            'gpa',
            'gpa_score',
            'test_result',
            'status',
            'files',
        ]


class ApplicationFullDataSerializer(serializers.ModelSerializer):
    items = ApplicationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Application  # ✅ bu yerda model Application bo'lishi kerak
        fields = ['id',  'submitted_at', 'status', 'items']




class StudentInfoSerializer(serializers.ModelSerializer):
    applications = ApplicationFullDataSerializer(source='applications', many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'student_id_number', 'applications']