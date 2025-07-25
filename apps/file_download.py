# apps/views.py yoki boshqa tegishli views fayliga qo‘ying
# views.py
from django.http import FileResponse, Http404
from django.conf import settings
import os
from urllib.parse import unquote

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def download_file(request, path):
    decoded_path = unquote(path)  # <<< bu MUHIM
    file_path = os.path.join(settings.MEDIA_ROOT, decoded_path)

    if not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(open(file_path, 'rb'), as_attachment=True)

