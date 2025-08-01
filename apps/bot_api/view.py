from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.models import Student, TestSession
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes

@api_view(['GET'])
@permission_classes([AllowAny])
def student_full_info(request, student_id_number):
    try:
        student = Student.objects.get(student_id_number=student_id_number)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    data = {
        "id": student.id,
        "full_name": student.full_name,
        "student_id_number": student.student_id_number,
        "university": student.university if student.university else None,
        "faculty": student.faculty.name if student.faculty else None,
        "speciality": student.specialty.name if student.specialty else None,
        "level": student.level.name if student.level else None,
        "group": student.group if student.group else None,
        "toifa": student.toifa if student.toifa else "Yo‘q",
        "applications": []
    }

    for app in student.applications.all():
        app_data = {
            "id": app.id,
            "application_type": app.application_type.name if app.application_type else None,
            "created_at": app.submitted_at,
            "items": []
        }

        for item in app.items.all():
            # Agar score mavjud bo'lmasa, xatolik chiqmasligi uchun tekshiramiz
            score = None
            if hasattr(item, 'score'):
                score = getattr(item.score, 'value', None)

            total_score = 0
            if score:
                total_score += score
            if item.gpa:
                total_score += item.gpa
            if item.test_result:
                total_score += item.test_result

            if item.direction.name == 'Talabaning akademik o‘zlashtirishi':
                item_data = {
                    "id": item.id,
                    "title": item.title,
                    "student_comment": item.student_comment,
                    "reviewer_comment": item.reviewer_comment,
                    "file": item.file.url if item.file else None,
                    "gpa": student.gpa,
                    "gpa_score": item.gpa_score,
                    "test_result": item.test_result,
                    "status": item.status,
                    "total_score": total_score
                }
            elif item.direction.name == 'Kitobxonlik madaniyati':
                test = TestSession.objects.filter(student=student).first()
                item_data = {
                    "id": item.id,
                    "title": item.title,
                    "student_comment": item.student_comment,
                    "reviewer_comment": item.reviewer_comment,
                    "file": item.file.url if item.file else None,
                    "gpa": item.gpa,
                    "gpa_score": item.gpa_score,
                    "test_result": test.score,
                    "status": item.status,
                    "total_score": total_score
                }
            else:
                item_data = {
                    "id": item.id,
                    "direction": item.direction.name,
                    "title": item.title,
                    "student_comment": item.student_comment,
                    "reviewer_comment": item.reviewer_comment,
                    "file": item.file.url if item.file else None,
                    "gpa": item.gpa,
                    "gpa_score": item.gpa_score,
                    "test_result": item.test_result,
                    "status": item.status,
                    "total_score": total_score
                }
            app_data["items"].append(item_data)

        data["applications"].append(app_data)

    return Response(data)