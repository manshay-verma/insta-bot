from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProxyViewSet, BotAccountViewSet, SessionViewSet

router = DefaultRouter()
router.register(r'proxies', ProxyViewSet, basename='proxy')
router.register(r'accounts', BotAccountViewSet, basename='account')
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]
