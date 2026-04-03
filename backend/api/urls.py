from django.urls import path, include
from .views import BotStatusView, BotControlView, HealthCheckView, RateLimitStatusView
from .bot_execute import BotExecuteView, BotExecuteAsyncView, TaskStatusView

urlpatterns = [
    path('bots/status/', BotStatusView.as_view(), name='bot-status'),
    path('bots/control/', BotControlView.as_view(), name='bot-control'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('rate-limits/', RateLimitStatusView.as_view(), name='rate-limit-status'),
    
    # Bot execution endpoints (trigger actual automation)
    path('bot/execute/', BotExecuteView.as_view(), name='bot-execute'),
    path('bot/execute/async/', BotExecuteAsyncView.as_view(), name='bot-execute-async'),
    path('bot/task/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
]
