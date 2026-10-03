from django.contrib import admin

from .models import BotAccount, Proxy, Session


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ("host", "port", "protocol", "country_code", "is_active", "failure_count", "created_at")
    list_filter = ("protocol", "is_active", "country_code")
    search_fields = ("host", "country_code")
    readonly_fields = ("created_at",)
    exclude = ("password",)


@admin.register(BotAccount)
class BotAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "status", "trust_score", "proxy", "last_login", "created_at")
    list_filter = ("status", "proxy")
    search_fields = ("username",)
    readonly_fields = ("created_at", "updated_at", "last_login")
    exclude = ("password_encrypted", "cookies_json")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "status", "started_at", "ended_at", "actions_count")
    list_filter = ("status", "started_at")
    search_fields = ("account__username",)
    readonly_fields = ("started_at", "ended_at")
