from django.contrib import admin

from .models import ActionLog, DailyAnalytics, UserBehavior


@admin.register(DailyAnalytics)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("date", "account", "follows_count", "unfollows_count", "likes_count", "comments_count", "downloads_count")
    list_filter = ("date",)
    search_fields = ("account__username",)
    date_hierarchy = "date"


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "action_type", "target_username", "success", "session")
    list_filter = ("action_type", "success", "created_at")
    search_fields = ("account__username", "target_username", "target_url", "error_message")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    list_display = ("recorded_at", "account", "behavior_type")
    list_filter = ("behavior_type", "recorded_at")
    search_fields = ("account__username", "behavior_type")
    readonly_fields = ("recorded_at",)
    date_hierarchy = "recorded_at"
