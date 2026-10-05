from django.contrib import admin

from .models import Download, DownloadQueue, MediaFile


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ("created_at", "media_type", "status", "target_username", "account", "file_size_bytes")
    list_filter = ("status", "media_type", "created_at")
    search_fields = ("source_url", "target_username", "account__username", "s3_key")
    readonly_fields = ("created_at", "downloaded_at")
    date_hierarchy = "created_at"


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("filename", "download", "content_type", "file_size", "created_at")
    search_fields = ("filename", "download__source_url")
    readonly_fields = ("created_at",)


@admin.register(DownloadQueue)
class DownloadQueueAdmin(admin.ModelAdmin):
    list_display = ("id", "target_username", "media_type", "priority", "is_processed", "created_at")
    list_filter = ("is_processed", "priority", "media_type", "created_at")
    search_fields = ("source_url", "target_username", "account__username")
    readonly_fields = ("created_at",)
