from django.contrib import admin

from .models import AppSetting, ExportJob


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ("theme", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("filename", "export_format", "status", "file_size_bytes", "created_at")
    list_filter = ("status", "export_format", "created_at")
    search_fields = ("filename", "file_path")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
