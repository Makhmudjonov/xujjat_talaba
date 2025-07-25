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
    # 1. URL encodingdan chiqarish
    decoded_path = unquote(path)

    # 2. Unicode normalization (o‘, ’ kabi belgilar muammosiz bo‘ladi)
    normalized_path = unicodedata.normalize("NFC", decoded_path)

    # 3. To‘liq fayl yo‘lini hosil qilish
    file_path = os.path.join(settings.MEDIA_ROOT, normalized_path)

    # 4. Fayl mavjudligini tekshirish
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # 5. Faylni yuborish
    return FileResponse(open(file_path, 'rb'), as_attachment=True)
