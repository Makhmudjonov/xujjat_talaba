# apps/views.py yoki boshqa tegishli views fayliga qo‘ying
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
import os
from urllib.parse import unquote

def download_file(request, path):
    decoded_path = unquote(path)  # bu yer muhim
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    return HttpResponseNotFound("Fayl topilmadi.")
