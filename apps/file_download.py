# apps/views.py yoki boshqa tegishli views fayliga qo‘ying
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
import os

def download_file(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    return HttpResponseNotFound("Fayl topilmadi.")
