from django.urls import path, include
from .views import (
    BotStatusView,
    BotControlView,
    BotControlBulkView,
    RegisterView,
    SettingsView,
    HealthCheckView,
    RateLimitStatusView,
    SystemStatusView,
    UpcomingScheduleView,
    MaintenanceCleanupView,
    ExportCreateView,
    ExportHistoryView,
    ExportDownloadView,
    ExportStatsView,
)
from .bot_execute import (
    BotExecuteView,
    BotExecuteAsyncView,
    TaskStatusView,
    JobCancelView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('bots/status/', BotStatusView.as_view(), name='bot-status'),
    path('bots/control/', BotControlView.as_view(), name='bot-control'),
    path('bots/control/bulk/', BotControlBulkView.as_view(), name='bot-control-bulk'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('rate-limits/', RateLimitStatusView.as_view(), name='rate-limit-status'),
    path('system/status/', SystemStatusView.as_view(), name='system-status'),
    path('schedule/upcoming/', UpcomingScheduleView.as_view(), name='schedule-upcoming'),
    path('maintenance/cleanup/', MaintenanceCleanupView.as_view(), name='maintenance-cleanup'),
    path('exports/', ExportCreateView.as_view(), name='exports-create'),
    path('exports/history/', ExportHistoryView.as_view(), name='exports-history'),
    path('exports/stats/', ExportStatsView.as_view(), name='exports-stats'),
    path('exports/<int:job_id>/download/', ExportDownloadView.as_view(), name='exports-download'),
    
    # Bot execution endpoints (trigger actual automation)
    path('bot/execute/', BotExecuteView.as_view(), name='bot-execute'),
    path('bot/execute/async/', BotExecuteAsyncView.as_view(), name='bot-execute-async'),
    path('bot/task/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
    path('bot/jobs/<uuid:job_id>/', TaskStatusView.as_view(), name='automation-job-status'),
    path('bot/jobs/<uuid:job_id>/cancel/', JobCancelView.as_view(), name='automation-job-cancel'),
]
