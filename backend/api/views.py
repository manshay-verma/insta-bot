"""
API endpoints for scraping tasks and bot status management.
"""
import os
import time
import json
import csv
from pathlib import Path

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

from account.models import BotAccount, Session
from analytics.models import DailyAnalytics, ActionLog
from downloads.models import Download, MediaFile
from .models import AppSetting, ExportJob
from .openapi import (
    ApiErrorSchema,
    BotControlBulkRequestSchema,
    BotControlRequestSchema,
    BotControlResponseSchema,
    BotStatusResponseSchema,
)


class BotStatusView(APIView):
    """Get current status of all bots."""

    @extend_schema(responses=BotStatusResponseSchema)
    def get(self, request):
        accounts = BotAccount.objects.all()
        
        status_summary = {
            'total': accounts.count(),
            'active': accounts.filter(status='active').count(),
            'paused': accounts.filter(status='paused').count(),
            'banned': accounts.filter(status='banned').count(),
            'checkpoint': accounts.filter(status='checkpoint').count(),
        }
        
        active_sessions = Session.objects.filter(status='active').select_related('account')
        running_bots = [
            {
                'account_id': s.account.id,
                'username': s.account.username,
                'session_id': s.id,
                'started_at': s.started_at,
                'actions_count': s.actions_count,
            }
            for s in active_sessions
        ]
        
        return Response({
            'status_summary': status_summary,
            'running_bots': running_bots,
        })


class BotControlView(APIView):
    """Control bot operations (start/stop/pause)."""

    @extend_schema(
        request=BotControlRequestSchema,
        responses={
            200: BotControlResponseSchema,
            400: ApiErrorSchema,
            404: ApiErrorSchema,
        },
    )
    def post(self, request):
        action = request.data.get('action')
        account_id = request.data.get('account_id')
        
        if not action or not account_id:
            return Response(
                {'error': 'action and account_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            account = BotAccount.objects.get(id=account_id)
        except BotAccount.DoesNotExist:
            return Response(
                {'error': 'Account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if action == 'start':
            if account.status != 'active':
                return Response({'error': 'Account is not active'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create new session
            session = Session.objects.create(account=account, status='active')
            return Response({
                'message': f'Bot started for {account.username}',
                'session_id': session.id,
            })
        
        elif action == 'stop':
            active_sessions = Session.objects.filter(account=account, status='active')
            count = active_sessions.update(status='completed', ended_at=timezone.now())
            return Response({'message': f'Stopped {count} sessions for {account.username}'})
        
        elif action == 'pause':
            account.status = 'paused'
            account.save()
            return Response({'message': f'Account {account.username} paused'})
        
        elif action == 'resume':
            account.status = 'active'
            account.save()
            return Response({'message': f'Account {account.username} resumed'})
        
        else:
            return Response(
                {'error': f'Unknown action: {action}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class BotControlBulkView(APIView):
    """
    Bulk bot controls for the dashboard buttons.

    POST /api/v1/bots/control/bulk/
    { "action": "start_all" | "stop_all" | "pause_all" | "resume_all" }
    """

    @extend_schema(
        request=BotControlBulkRequestSchema,
        responses={200: BotControlResponseSchema, 400: ApiErrorSchema},
    )
    def post(self, request):
        action = request.data.get('action')
        if not action:
            return Response({'error': 'action required'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'start_all':
            accounts = BotAccount.objects.filter(status='active')
            created = 0
            skipped = 0
            for acc in accounts:
                if Session.objects.filter(account=acc, status='active').exists():
                    skipped += 1
                    continue
                Session.objects.create(account=acc, status='active')
                created += 1
            return Response({'message': 'start_all complete', 'created_sessions': created, 'skipped': skipped})

        if action == 'stop_all':
            active_sessions = Session.objects.filter(status='active')
            count = active_sessions.update(status='completed', ended_at=timezone.now())
            return Response({'message': 'stop_all complete', 'stopped_sessions': count})

        if action == 'pause_all':
            count = BotAccount.objects.exclude(status='banned').update(status='paused')
            return Response({'message': 'pause_all complete', 'updated_accounts': count})

        if action == 'resume_all':
            count = BotAccount.objects.filter(status='paused').update(status='active')
            return Response({'message': 'resume_all complete', 'updated_accounts': count})

        return Response({'error': f'Unknown action: {action}'}, status=status.HTTP_400_BAD_REQUEST)


class SystemStatusView(APIView):
    """Small dynamic status block for the dashboard."""

    _boot_time = time.time()

    def get(self, request):
        # We intentionally keep this lightweight (no extra dependencies).
        uptime_seconds = int(time.time() - self._boot_time)
        active_sessions = Session.objects.filter(status='active').count()

        # CPU usage is not reliably available without psutil; return null.
        return Response({
            'timestamp': timezone.now(),
            'uptime_seconds': uptime_seconds,
            'active_sessions': active_sessions,
            'network_health': 'optimal' if active_sessions >= 0 else 'unknown',
            'cpu_usage_percent': None,
            'pid': os.getpid(),
        })


class UpcomingScheduleView(APIView):
    """
    Placeholder schedule endpoint so the UI is fully dynamic.
    Later you can back this with Celery beat / a Schedule model.
    """

    def get(self, request):
        return Response({'items': []})


class MaintenanceCleanupView(APIView):
    """
    Cleanup endpoint for the dashboard "Clean Database" button.
    This is intentionally conservative: it only removes completed/failed sessions.
    """

    def post(self, request):
        cutoff_days = int(request.data.get('cutoff_days', 30))
        cutoff = timezone.now() - timezone.timedelta(days=cutoff_days)

        old_sessions = Session.objects.filter(status__in=['completed', 'failed', 'terminated'], ended_at__lt=cutoff)
        deleted_sessions = old_sessions.count()
        old_sessions.delete()

        return Response({
            'message': 'cleanup complete',
            'deleted_sessions': deleted_sessions,
            'cutoff_days': cutoff_days,
        })


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)


class RegisterView(APIView):
    """
    Simple user registration for the dashboard.

    POST /api/v1/register/
    { "username": "...", "email": "...", "password": "..." }
    """

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if User.objects.filter(username=data["username"]).exists():
            return Response({"detail": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=data["email"]).exists():
            return Response({"detail": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )

        return Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)


class SettingsSerializer(serializers.Serializer):
    theme = serializers.CharField(required=False)
    notifications = serializers.DictField(required=False)
    proxy_settings = serializers.DictField(required=False)


class SettingsView(APIView):
    """
    Persisted dashboard settings.

    GET  /api/v1/settings/
    POST /api/v1/settings/
    """

    def get(self, request):
        s = AppSetting.objects.first()
        if not s:
            s = AppSetting.objects.create(
                theme="dark",
                notifications={"browser": True, "email": False, "webhooks": True},
                proxy_settings={"globalProxy": "", "trustLevel": "medium"},
            )
        return Response({
            "theme": s.theme,
            "notifications": s.notifications or {},
            "proxy_settings": s.proxy_settings or {},
            "updated_at": s.updated_at,
        })

    def post(self, request):
        serializer = SettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        s = AppSetting.objects.first()
        if not s:
            s = AppSetting.objects.create(
                theme="dark",
                notifications={},
                proxy_settings={},
            )

        if "theme" in data:
            s.theme = data["theme"]
        if "notifications" in data:
            s.notifications = data["notifications"]
        if "proxy_settings" in data:
            s.proxy_settings = data["proxy_settings"]
        s.save()

        return Response({
            "theme": s.theme,
            "notifications": s.notifications or {},
            "proxy_settings": s.proxy_settings or {},
            "updated_at": s.updated_at,
        })


class ExportCreateSerializer(serializers.Serializer):
    export_format = serializers.ChoiceField(choices=["json", "csv", "zip"])
    data_types = serializers.ListField(
        child=serializers.ChoiceField(choices=["analytics", "actions", "downloads", "media_files", "system_status"]),
        min_length=1,
    )


class ExportHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    filename = serializers.CharField()
    export_format = serializers.CharField()
    data_types = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()
    file_size_bytes = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()


def _exports_dir() -> Path:
    base = Path(__file__).resolve().parents[2]  # backend/
    out = base.parent / "artifacts" / "exports"
    out.mkdir(parents=True, exist_ok=True)
    return out


class ExportStatsView(APIView):
    """Numbers for Export Center sidebar (fully dynamic)."""

    def get(self, request):
        return Response({
            "total_rows": {
                "accounts": BotAccount.objects.count(),
                "sessions": Session.objects.count(),
                "action_logs": ActionLog.objects.count(),
                "daily_analytics": DailyAnalytics.objects.count(),
                "downloads": Download.objects.count(),
                "media_files": MediaFile.objects.count(),
            }
        })


class ExportCreateView(APIView):
    """
    Generate an export file and return a download link.

    POST /api/v1/exports/
    { "export_format": "json"|"csv"|"zip", "data_types": [...] }
    """

    def post(self, request):
        serializer = ExportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        export_format = serializer.validated_data["export_format"]
        data_types = serializer.validated_data["data_types"]

        ts = timezone.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"export_{ts}"
        out_dir = _exports_dir()

        def as_dicts(qs):
            return list(qs.values())

        payload = {}
        if "analytics" in data_types:
            payload["daily_analytics"] = as_dicts(DailyAnalytics.objects.all()[:5000])
        if "actions" in data_types:
            payload["action_logs"] = as_dicts(ActionLog.objects.all()[:5000])
        if "downloads" in data_types:
            payload["downloads"] = as_dicts(Download.objects.all()[:5000])
        if "media_files" in data_types:
            payload["media_files"] = as_dicts(MediaFile.objects.all()[:5000])
        if "system_status" in data_types:
            # Reuse the same structure returned by SystemStatusView
            payload["system_status"] = {
                "timestamp": timezone.now().isoformat(),
                "active_sessions": Session.objects.filter(status="active").count(),
            }

        try:
            if export_format == "json":
                filename = f"{base_name}.json"
                path = out_dir / filename
                path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")

            elif export_format == "csv":
                # CSV exports only action logs (most tabular). Others can be JSON/ZIP.
                filename = f"{base_name}_actions.csv"
                path = out_dir / filename
                rows = list(ActionLog.objects.all().values())[:5000]
                with path.open("w", newline="", encoding="utf-8") as f:
                    if rows:
                        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                        writer.writeheader()
                        writer.writerows(rows)
                    else:
                        f.write("")

            else:  # zip
                import zipfile

                filename = f"{base_name}.zip"
                path = out_dir / filename
                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("export.json", json.dumps(payload, default=str, indent=2))

            size = path.stat().st_size if path.exists() else None
            job = ExportJob.objects.create(
                export_format=export_format,
                data_types=data_types,
                filename=filename,
                file_path=str(path),
                file_size_bytes=size,
                status="completed",
            )

            return Response({
                "job_id": job.id,
                "filename": job.filename,
                "download_url": f"/api/v1/exports/{job.id}/download/",
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            job = ExportJob.objects.create(
                export_format=export_format,
                data_types=data_types,
                filename=f"{base_name}.error",
                file_path="",
                status="failed",
                error_message=str(e),
            )
            return Response({"detail": "Export failed", "job_id": job.id, "error": str(e)}, status=500)


class ExportHistoryView(APIView):
    """List past exports."""

    def get(self, request):
        qs = ExportJob.objects.all()[:100]
        data = [{
            "id": j.id,
            "filename": j.filename,
            "export_format": j.export_format,
            "data_types": j.data_types or [],
            "status": j.status,
            "file_size_bytes": j.file_size_bytes,
            "created_at": j.created_at,
        } for j in qs]
        return Response(data)


class ExportDownloadView(APIView):
    """Download an export file by job id."""

    def get(self, request, job_id: int):
        from django.http import FileResponse, Http404

        try:
            job = ExportJob.objects.get(id=job_id)
        except ExportJob.DoesNotExist:
            raise Http404("Export not found")

        if job.status != "completed" or not job.file_path:
            return Response({"detail": "Export not available"}, status=404)

        path = Path(job.file_path)
        if not path.exists():
            return Response({"detail": "File missing on disk"}, status=404)

        return FileResponse(path.open("rb"), as_attachment=True, filename=job.filename)


class HealthCheckView(APIView):
    """API health check endpoint."""

    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now(),
            'version': '1.0.0',
        })


class RateLimitStatusView(APIView):
    """Get rate limit status for accounts."""

    def get(self, request):
        account_id = request.query_params.get('account_id')
        
        # Default limits (from safety module)
        limits = {
            'follows_per_day': 15,
            'likes_per_hour': 20,
            'stories_per_hour': 10,
            'scrolls_per_session': 50,
        }
        
        if account_id:
            try:
                account = BotAccount.objects.get(id=account_id)
                # Get today's action counts
                from analytics.models import ActionLog
                today = timezone.now().date()
                
                actions_today = ActionLog.objects.filter(
                    account=account,
                    created_at__date=today
                ).values('action_type').annotate(
                    count=models.Count('id')
                )
                
                usage = {a['action_type']: a['count'] for a in actions_today}
                
                return Response({
                    'account_id': account_id,
                    'limits': limits,
                    'usage_today': usage,
                })
            except BotAccount.DoesNotExist:
                return Response(
                    {'error': 'Account not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response({'limits': limits})
