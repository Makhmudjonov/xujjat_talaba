from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import FileResponse, Http404
from django.conf import settings
from urllib.parse import unquote
import os

@api_view(['GET'])
@permission_classes([AllowAny])
def download_file(request, path):
    decoded_path = unquote(path)  # URLdagi %20, %E2%80... ni oddiy matnga aylantiradi
    file_path = os.path.join(settings.MEDIA_ROOT, decoded_path)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(open(file_path, 'rb'), as_attachment=True)
