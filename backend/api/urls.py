from django.urls import path, include
from .views import BotStatusView, BotControlView, HealthCheckView, RateLimitStatusView

urlpatterns = [
    path('bots/status/', BotStatusView.as_view(), name='bot-status'),
    path('bots/control/', BotControlView.as_view(), name='bot-control'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('rate-limits/', RateLimitStatusView.as_view(), name='rate-limit-status'),
]
