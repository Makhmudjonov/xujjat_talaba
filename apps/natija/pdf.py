from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO
import requests
from PIL import Image as PILImage
from django.shortcuts import get_object_or_404
from apps.models import Student, ApplicationItem

class ExportStudentPDF(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = get_object_or_404(Student, user=request.user)
        app_items = ApplicationItem.objects.filter(application__student=student).prefetch_related('files', 'direction', 'score')

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Student image
        image_data = None
        if student.image:
            try:
                response = requests.get(student.image.url)
                if response.status_code == 200:
                    img_temp = BytesIO(response.content)
                    pil_img = PILImage.open(img_temp)
                    pil_img.thumbnail((120, 120))
                    img_io = BytesIO()
                    pil_img.save(img_io, format="PNG")
                    img_io.seek(0)
                    image_data = Image(img_io, width=1.5 * inch, height=1.5 * inch)
            except:
                pass

        # Student Info
        student_info = [
            ["Shaxsiy ID", student.student_id_number],
            ["F.I.Sh.", student.full_name],
            ["Telefon", student.phone or ""],
            ["Jinsi", student.gender],
            ["Universitet", student.university],
            ["Fakultet", student.faculty.name if student.faculty else ""],
            ["Guruh", student.group],
            ["Bosqich", student.level.name if student.level else ""],
        ]
        student_table = Table(student_info, colWidths=[150, 250])
        student_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        if image_data:
            full_table = Table([[image_data, student_table]], colWidths=[120, 400])
        else:
            full_table = student_table

        elements.append(Paragraph("📌 <b>Talaba ma’lumotlari</b>", styles["Heading2"]))
        elements.append(full_table)
        elements.append(Spacer(1, 20))

        # Applications
        elements.append(Paragraph("📑 <b>Arizalar</b>", styles["Heading2"]))
        for idx, item in enumerate(app_items, start=1):
            direction_name = item.direction.name if item.direction else ""

            elements.append(Paragraph(f"<b>{idx}. {item.title}</b>", styles["Normal"]))

            # Umumiy qiymatlar
            score_value = item.score.value if hasattr(item, 'score') and item.score else "Mavjud emas"
            result_gpa = item.result_gpa.score if hasattr(item, 'result_gpa') else "Mavjud emas"
            result_test = item.result_test.score if hasattr(item, 'result_test') else "Mavjud emas"
            total_test = item.result_test.total if hasattr(item, 'result_test') else "Mavjud emas"
            correct_test = item.result_test.correct if hasattr(item, 'result_test') else "Mavjud emas"
            reviewer_comment = item.reviewer_comment or "Mavjud emas"
            student_comment = item.student_comment or "Mavjud emas"

            if direction_name == "Kitobxonlik madaniyati":
                item_data = [
                    ["Yo‘nalish", direction_name],
                    ["Test natija", item.test_result if item.test_result else "Mavjud emas"],
                    ["Test ball", result_test],
                    ["Jami savol", total_test],
                    ["To'gri javob", correct_test],
                    ["Baholovchi izohi", reviewer_comment],
                ]
            elif direction_name == "Talabaning akademik o‘zlashtirishi":
                item_data = [
                    ["Yo‘nalish", direction_name],
                    ["GPA", result_gpa if result_gpa else "Mavjud emas"],
                    ["Ball", result_gpa if result_gpa else "Mavjud emas"],
                    ["Talaba izohi", student_comment],
                    ["Baholovchi izohi", reviewer_comment],
                ]
            else:
                item_data = [
                    ["Yo‘nalish", direction_name],
                    ["Talaba izohi", student_comment],
                    ["Ball", score_value],
                    ["Baholovchi izohi", reviewer_comment],
                ]

            table = Table(item_data, colWidths=[150, 350])
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

        doc.build(elements)
        buffer.seek(0)

        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename="student_profile.pdf"',
        })
        