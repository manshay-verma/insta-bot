"""
Bot Execution API

Endpoints to trigger actual Instagram automation tasks.
This is the critical link between Backend → Orchestrator → Automation.
"""

import asyncio
import logging
import sys
from pathlib import Path
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from django.utils import timezone

from account.models import BotAccount, Session
from analytics.models import ActionLog

# Add orchestrator to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class BotExecuteSerializer(serializers.Serializer):
    """Serializer for bot execution requests."""
    account_id = serializers.IntegerField(required=True)
    action = serializers.ChoiceField(
        choices=[
            ('like', 'Like Posts'),
            ('follow', 'Follow Users'),
            ('unfollow', 'Unfollow Users'),
            ('scrape_profile', 'Scrape Profile'),
            ('view_stories', 'View Stories'),
            ('download', 'Download Media'),
            ('comment', 'Comment on Post'),
        ],
        required=True
    )
    targets = serializers.ListField(
        child=serializers.CharField(),
        required=True,
        help_text="List of usernames or URLs to act on"
    )
    options = serializers.DictField(required=False, default=dict)


class BotExecuteView(APIView):
    """
    Execute Instagram automation tasks.
    
    POST /api/v1/bot/execute/
    {
        "account_id": 1,
        "action": "like",
        "targets": ["https://instagram.com/p/xyz"]
    }
    
    This endpoint:
    1. Validates the request
    2. Checks account status
    3. Triggers the orchestrator
    4. Logs the action to database
    5. Returns result
    """
    
    def post(self, request):
        serializer = BotExecuteSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        account_id = data['account_id']
        action = data['action']
        targets = data['targets']
        options = data.get('options', {})
        
        # Validate account
        try:
            account = BotAccount.objects.get(id=account_id)
        except BotAccount.DoesNotExist:
            return Response(
                {'error': f'Account {account_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if account.status != 'active':
            return Response(
                {'error': f'Account is not active (status: {account.status})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Execute automation
        try:
            result = self._execute_action(account, action, targets, options)
            
            # Log action to database
            for target in targets[:len(result.get('processed', []))]:
                ActionLog.objects.create(
                    account=account,
                    action_type=action,
                    target_username=target if not target.startswith('http') else None,
                    target_url=target if target.startswith('http') else None,
                    success=result['success'],
                    metadata=options
                )
            
            return Response({
                'success': result['success'],
                'message': result.get('message', 'Action completed'),
                'items_processed': result.get('items_processed', 0),
                'errors': result.get('errors', []),
            })
            
        except Exception as e:
            logger.exception(f"Bot execution failed: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _execute_action(self, account, action, targets, options):
        """Execute action using orchestrator (sync wrapper)."""
        try:
            from orchestrator import UnifiedWorker, AdapterType, TaskType
            
            # Map action to TaskType
            action_map = {
                'like': TaskType.LIKE_POSTS,
                'follow': TaskType.FOLLOW_USERS,
                'unfollow': TaskType.UNFOLLOW_USERS,
                'scrape_profile': TaskType.SCRAPE_PROFILE,
                'view_stories': TaskType.VIEW_STORIES,
                'download': TaskType.BULK_DOWNLOAD,
                'comment': TaskType.COMMENT,
            }
            
            task_type = action_map.get(action)
            if not task_type:
                return {'success': False, 'errors': [f'Unknown action: {action}']}
            
            # Determine adapter
            adapter_type = AdapterType.PLAYWRIGHT
            if action == 'download':
                adapter_type = AdapterType.DOWNLOADER
            
            # Run async execution
            result = asyncio.run(self._async_execute(
                account.id, adapter_type, task_type, targets, options
            ))
            
            return result
            
        except ImportError as e:
            logger.error(f"Orchestrator import failed: {e}")
            return {
                'success': False,
                'errors': [f'Orchestrator not available: {e}'],
                'items_processed': 0
            }
    
    async def _async_execute(self, account_id, adapter_type, task_type, targets, options):
        """Async execution wrapper."""
        from orchestrator import UnifiedWorker
        
        worker = UnifiedWorker(account_id=account_id)
        
        try:
            await worker.start_session()
            result = await worker.execute(adapter_type, task_type, targets, **options)
            
            return {
                'success': result.success,
                'items_processed': result.items_processed,
                'errors': result.errors,
                'processed': targets[:result.items_processed],
            }
        finally:
            await worker.cleanup()
            await worker.stop_session()


class BotExecuteAsyncView(APIView):
    """
    Queue automation task for async execution (requires Celery).
    
    POST /api/v1/bot/execute/async/
    
    Returns task_id for tracking.
    """
    
    def post(self, request):
        serializer = BotExecuteSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Check if Celery is available
        try:
            from .tasks import execute_bot_task
            task = execute_bot_task.delay(
                account_id=data['account_id'],
                action=data['action'],
                targets=data['targets'],
                options=data.get('options', {})
            )
            return Response({
                'task_id': task.id,
                'status': 'queued',
                'message': 'Task queued for execution'
            })
        except ImportError:
            return Response(
                {'error': 'Async execution not available. Celery not configured.'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )


class TaskStatusView(APIView):
    """Check status of async task."""
    
    def get(self, request, task_id):
        try:
            from celery.result import AsyncResult
            result = AsyncResult(task_id)
            
            return Response({
                'task_id': task_id,
                'status': result.status,
                'result': result.result if result.ready() else None,
            })
        except ImportError:
            return Response(
                {'error': 'Celery not configured'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
