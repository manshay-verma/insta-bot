from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DownloadViewSet,
    DownloadQueueViewSet,
    MediaFileViewSet,
    DownloadHistoryView,
)

router = DefaultRouter()
router.register(r'downloads', DownloadViewSet, basename='download')
router.register(r'queue', DownloadQueueViewSet, basename='download-queue')
router.register(r'files', MediaFileViewSet, basename='media-file')

urlpatterns = [
    path('', include(router.urls)),
    path('history/', DownloadHistoryView.as_view(), name='download-history'),
]
