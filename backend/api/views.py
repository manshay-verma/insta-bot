"""
API endpoints for scraping tasks and bot status management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import models

from account.models import BotAccount, Session


class BotStatusView(APIView):
    """Get current status of all bots."""

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
