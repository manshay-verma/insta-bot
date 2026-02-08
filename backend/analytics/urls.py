from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DailyAnalyticsViewSet,
    ActionLogViewSet,
    UserBehaviorViewSet,
    DashboardView,
    AccountStatsView,
)

router = DefaultRouter()
router.register(r'daily', DailyAnalyticsViewSet, basename='daily-analytics')
router.register(r'actions', ActionLogViewSet, basename='action-log')
router.register(r'behaviors', UserBehaviorViewSet, basename='user-behavior')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/<int:account_id>/stats/', AccountStatsView.as_view(), name='account-stats'),
]
