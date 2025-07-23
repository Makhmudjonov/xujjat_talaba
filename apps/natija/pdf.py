from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from apps.models import ApplicationItem, Student
from django.shortcuts import get_object_or_404
import base64
import requests

class ExportStudentPDF(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_object_or_404(Student, user=request.user)

        # Application items
        app_items = ApplicationItem.objects.filter(application__student=student).prefetch_related('files', 'direction', 'score')

        # PDF initialization
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # 1. Student info
        elements.append(Paragraph("📌 <b>Student Ma’lumotlari</b>", styles["Heading2"]))
        student_data = [
            ["F.I.Sh.", student.full_name],
            ["Shaxsiy ID", student.student_id_number],
            ["Telefon", student.phone or ""],
            ["Jinsi", student.gender],
            ["Universitet", student.university],
            ["Fakultet", student.faculty.name if student.faculty else ""],
            ["Guruh", student.group],
            ["Bosqich", student.level.name if student.level else ""],
        ]
        student_table = Table(student_data, colWidths=[150, 350])
        student_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(student_table)
        elements.append(Spacer(1, 15))

        # 2. Application items table
        elements.append(Paragraph("📑 <b>Application Itemlari</b>", styles["Heading2"]))
        for item in app_items:
            elements.append(Spacer(1, 8))
            item_data = [
                ["Yo‘nalish", item.direction.name if item.direction else ""],
                ["Ball (GPA)", item.gpa_score or ""],
                ["Ball (Test)", item.test_result or ""],
                ["Talaba izohi", item.student_comment or ""],
                ["Baholovchi izohi", item.reviewer_comment or ""],
            ]
            item_table = Table(item_data, colWidths=[150, 350])
            item_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(item_table)

            # Fayllar ro‘yxati
            if item.files.exists():
                file_names = [f.file.name for f in item.files.all()]
                file_data = [["Fayllar:"]] + [[fname] for fname in file_names]
                file_table = Table(file_data, colWidths=[500])
                file_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                elements.append(file_table)

            elements.append(Spacer(1, 10))

        # 3. Rasm (optional)
        if student.image:
            try:
                image_url = student.image.url
                image_path = student.image.path
                elements.append(Spacer(1, 15))
                elements.append(Paragraph("🖼️ <b>Student rasmi:</b>", styles["Normal"]))
                elements.append(Image(image_path, width=100, height=100))
            except:
                pass

        doc.build(elements)
        buffer.seek(0)

        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename="student_profile.pdf"',
        })
