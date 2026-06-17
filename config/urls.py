from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.static import serve
import os

def serve_media(request, path, document_root=None):
    """
    Serve PDF files inline (so browser displays them instead of downloading).
    Serve all other media files normally.
    """
    fullpath = os.path.join(document_root, path)

    # Security check — prevent path traversal
    if not os.path.exists(fullpath):
        raise Http404("File not found")

    ext = os.path.splitext(fullpath)[1].lower()

    if ext == '.pdf':
        response = FileResponse(
            open(fullpath, 'rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = (
            f'inline; filename="{os.path.basename(fullpath)}"'
        )
        return response

    # All non-PDF files (mp3, webm, images etc.) served normally
    return serve(request, path, document_root=document_root)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('interview.urls')),
    re_path(
        r'^media/(?P<path>.*)$',
        serve_media,
        {'document_root': settings.MEDIA_ROOT}
    ),
]