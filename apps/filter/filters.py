# filters.py
import django_filters
from apps.models import Application, ApplicationItem, ApplicationType, Faculty, Student, GPARecord, University

class StudentFilter(django_filters.FilterSet):
    gender = django_filters.CharFilter(field_name="gender", lookup_expr='iexact')
    university = django_filters.CharFilter(field_name="university", lookup_expr='icontains')
    full_name = django_filters.CharFilter(field_name="full_name", lookup_expr='icontains')
    faculty = django_filters.NumberFilter(field_name="faculty__id")
    level = django_filters.NumberFilter(field_name="level__id")

    class Meta:
        model = Student
        fields = ['gender', 'university', 'faculty', 'level']


class GPARecordFilter(django_filters.FilterSet):
    gpa_range = django_filters.ChoiceFilter(
        method='filter_gpa_range',
        choices=[
            ('1-2', '1–2'),
            ('2-3', '2–3'),
            ('3-4', '3–4'),
            ('4+', '4+'),
        ]
    )

    def filter_gpa_range(self, queryset, name, value):
        if value == '1-2':
            return queryset.filter(gpa__gte=1, gpa__lt=2)
        elif value == '2-3':
            return queryset.filter(gpa__gte=2, gpa__lt=3)
        elif value == '3-4':
            return queryset.filter(gpa__gte=3, gpa__lt=4)
        elif value == '4+':
            return queryset.filter(gpa__gte=4)
        return queryset

    class Meta:
        model = GPARecord
        fields = ['gpa_range']

class ApplicationTypeFilter(django_filters.FilterSet):
    access_type = django_filters.ChoiceFilter(choices=ApplicationType.ACCESS_CHOICES)
    min_gpa = django_filters.NumberFilter(field_name="min_gpa", lookup_expr='gte')
    level_id = django_filters.NumberFilter(method='filter_level')

    def filter_level(self, queryset, name, value):
        return queryset.filter(allowed_levels__id=value)

    class Meta:
        model = ApplicationType
        fields = ['access_type', 'min_gpa']



class ApplicationFilter(django_filters.FilterSet):
    application_type = django_filters.NumberFilter(field_name='application_type__id')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    section = django_filters.NumberFilter(field_name='section__id')

    class Meta:
        model = Application
        fields = ['application_type', 'status', 'section']

class ApplicationItemFilter(django_filters.FilterSet):
    direction = django_filters.NumberFilter(field_name='direction__id')
    gpa_min = django_filters.NumberFilter(field_name='gpa', lookup_expr='gte')
    gpa_max = django_filters.NumberFilter(field_name='gpa', lookup_expr='lte')
    test_min = django_filters.NumberFilter(field_name='test_result', lookup_expr='gte')
    test_max = django_filters.NumberFilter(field_name='test_result', lookup_expr='lte')

    class Meta:
        model = ApplicationItem
        fields = ['direction', 'gpa_min', 'gpa_max', 'test_min', 'test_max']


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from apps.models import Student, Level

@api_view(["GET"])
@permission_classes([IsAdminUser])
def global_student_filter_faculty(request):
    user = request.user
    faculty = Faculty.objects.filter(student__isnull=False, user=user).distinct().values("id", "name")
    return Response({
        "facultys": list(faculty)
    })

@api_view(["GET"])
@permission_classes([IsAdminUser])
def global_student_filter_level(request):
    levels = Level.objects.filter(student__isnull=False).distinct().values("id", "name")
    return Response({
        "levels": list(levels)
    })

@api_view(["GET"])
@permission_classes([IsAdminUser])
def global_student_filter_university(request):
    universitys = University.objects.filter(student__isnull=False).distinct().values("id", "name")
    return Response({
        "universitys": list(universitys)
    })

