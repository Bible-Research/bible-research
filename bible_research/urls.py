from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('', RedirectView.as_view(url='/api/v1/docs/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/v1/', include('bible.urls')),
    path('api/v1/', include('annotations.urls')),
    path('api/token/', obtain_auth_token, name='api_token'),

    # API Schema and Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path(
        'api/v1/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    path(
        'api/v1/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]
