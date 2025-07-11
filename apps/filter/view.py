# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg
from apps.models import Student, GPARecord, Application, ApplicationType, ApplicationItem

class PublicStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {}

        # 1. Student gender, university, faculty, level
        stats["students"] = {
            "total": Student.objects.count(),
            "by_gender": list(Student.objects.values("gender").annotate(count=Count("id"))),
            "by_university": list(Student.objects.values("university").annotate(count=Count("id"))),
            "by_faculty": list(Student.objects.values("faculty__name").annotate(count=Count("id"))),
            "by_level": list(Student.objects.values("level__name").annotate(count=Count("id"))),
        }

        # 2. GPA interval bo‘yicha taqsimot
        gpa_ranges = {'1-2': 0, '2-3': 0, '3-4': 0, '4+': 0}
        gpa_data = GPARecord.objects.values('student_id').annotate(avg_gpa=Avg('gpa'))
        for item in gpa_data:
            try:
                gpa = float(item['avg_gpa'])
                if 1 <= gpa < 2:
                    gpa_ranges['1-2'] += 1
                elif 2 <= gpa < 3:
                    gpa_ranges['2-3'] += 1
                elif 3 <= gpa < 4:
                    gpa_ranges['3-4'] += 1
                elif gpa >= 4:
                    gpa_ranges['4+'] += 1
            except:
                continue
        stats["gpa_distribution"] = gpa_ranges

        # 3. ApplicationType bo‘yicha arizalar soni
        stats["application_types"] = list(
            Application.objects.values("application_type__name").annotate(count=Count("id"))
        )

        # 4. ApplicationItem: GPA / test_result statistikasi
        stats["application_items"] = {
            "with_gpa": ApplicationItem.objects.exclude(gpa__isnull=True).count(),
            "with_test_result": ApplicationItem.objects.exclude(test_result__isnull=True).count(),
            "avg_gpa": round(ApplicationItem.objects.aggregate(avg=Avg("gpa"))["avg"] or 0, 2),
            "avg_test_result": round(ApplicationItem.objects.aggregate(avg=Avg("test_result"))["avg"] or 0, 2),
        }

        return Response(stats)

class FacultyStudentStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Student.objects
            .values('faculty__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Fakultetsizlar nomini aniqlab qo‘shish
        result = []
        for item in data:
            faculty_name = item['faculty__name'] or "Noma'lum fakultet"
            result.append({"faculty": faculty_name, "count": item['count']})

        return Response(result)
    
    
class GPAStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gpa_data = (
            GPARecord.objects
            .values('student_id')
            .annotate(avg_gpa=Avg('gpa'))
        )

        ranges = {
            '1-2': 0,
            '2-3': 0,
            '3-4': 0,
            '4+': 0,
        }

        for item in gpa_data:
            try:
                gpa = float(item['avg_gpa'])
                if 1 <= gpa < 2:
                    ranges['1-2'] += 1
                elif 2 <= gpa < 3:
                    ranges['2-3'] += 1
                elif 3 <= gpa < 4:
                    ranges['3-4'] += 1
                elif gpa >= 4:
                    ranges['4+'] += 1
            except:
                continue

        return Response(ranges)
    

class ApplicationTypeStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            ApplicationType.objects
            .annotate(application_count=Count('applications'))
            .values('key', 'name', 'application_count')
            .order_by('-application_count')
        )
        return Response(list(data))
    
class StudentGenderStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Student.objects
            .values('gender')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        result = [
            {"gender": item['gender'] or "Noma'lum", "count": item['count']}
            for item in data
        ]
        return Response(result)
    
class UniversityStudentStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Student.objects
            .values('university')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        result = [
            {"university": item['university'] or "Noma'lum universitet", "count": item['count']}
            for item in data
        ]
        return Response(result)