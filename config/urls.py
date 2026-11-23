from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic.base import RedirectView
from accounts.views import landing_view

def healthz_view(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('healthz/', healthz_view, name='healthz'),
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.svg', permanent=True)),
    path('', landing_view, name='landing'),
    path('accounts/', include('accounts.urls')),
    path('', include('interviews.urls')),
    path('', include('analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
