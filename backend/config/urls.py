"""
URL configuration for InstaBot backend.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 routes
    path('api/v1/', include('api.urls')),
    path('api/v1/', include('account.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/downloads/', include('downloads.urls')),
]
