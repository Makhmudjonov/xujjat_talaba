from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import FileResponse, Http404
from django.conf import settings
from urllib.parse import unquote
import os
import unicodedata

@api_view(['GET'])
@permission_classes([AllowAny])
def download_file(request, path):
    # URL'dan dekodlash
    decoded_path = unquote(path)
    normalized_path = unicodedata.normalize("NFC", decoded_path)

    # To‘liq fayl yo‘li
    file_path = os.path.join(settings.MEDIA_ROOT, normalized_path)

    # Fayl mavjudligini tekshirish
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Faylni yuborish va fayl nomini headerga qo‘shish
    response = FileResponse(open(file_path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(normalized_path)}"'
    return response
