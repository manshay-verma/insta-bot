from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from django.utils import timezone

from .models import Download, MediaFile, DownloadQueue
from .serializers import (
    DownloadSerializer,
    DownloadCreateSerializer,
    MediaFileSerializer,
    DownloadQueueSerializer,
    BulkDownloadSerializer,
    DownloadStatusSerializer,
)
from api.openapi import (
    ApiErrorSchema,
    BulkQueueResponseSchema,
    QueueProcessResponseSchema,
)


@extend_schema_view(
    list=extend_schema(parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                         description="Exact status string filter; the view does not validate it against model choices."),
        OpenApiParameter("media_type", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                         description="Exact media_type string filter; the view does not validate it against model choices."),
        OpenApiParameter("account", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    ]),
    create=extend_schema(examples=[OpenApiExample(
        "Create download record",
        value={"source_url": "https://www.instagram.com/p/example/", "media_type": "image"},
        request_only=True,
    )]),
)
class DownloadViewSet(viewsets.ModelViewSet):
    """ViewSet for Download CRUD operations."""
    queryset = Download.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return DownloadCreateSerializer
        return DownloadSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        media_type = self.request.query_params.get('media_type')
        if media_type:
            queryset = queryset.filter(media_type=media_type)
        
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        return queryset

    @extend_schema(
        request=None,
        responses={200: DownloadStatusSerializer, 404: ApiErrorSchema},
        description="Progress is simplified: completed=100, downloading=50 (placeholder), other states=0.",
    )
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get download status with progress."""
        download = self.get_object()
        
        # Calculate progress (simplified)
        progress = 0
        if download.status == 'completed':
            progress = 100
        elif download.status == 'downloading':
            progress = 50  # Placeholder
        
        data = {
            'download_id': download.id,
            'status': download.status,
            'progress_percent': progress,
            'file_size_bytes': download.file_size_bytes,
            'error_message': download.error_message,
        }
        
        serializer = DownloadStatusSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        request=BulkDownloadSerializer,
        responses={201: BulkQueueResponseSchema, 400: ApiErrorSchema},
        description="Creates DownloadQueue rows only; it does not start a downloader task.",
        examples=[OpenApiExample(
            "Queue downloads",
            value={"urls": ["https://www.instagram.com/p/example/"], "media_type": "image", "priority": 2},
            request_only=True,
        )],
    )
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Queue multiple downloads at once."""
        serializer = BulkDownloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        urls = serializer.validated_data['urls']
        media_type = serializer.validated_data.get('media_type')
        account_id = serializer.validated_data.get('account_id')
        target_username = serializer.validated_data.get('target_username')
        priority = serializer.validated_data.get('priority', 2)
        
        queued_items = []
        for url in urls:
            queue_item = DownloadQueue.objects.create(
                source_url=url,
                media_type=media_type,
                target_username=target_username,
                priority=priority,
                account_id=account_id,
            )
            queued_items.append(queue_item.id)
        
        return Response({
            'message': f'Queued {len(queued_items)} downloads',
            'queue_ids': queued_items,
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(parameters=[
        OpenApiParameter("priority", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False,
                         description="Exact priority filter; values outside 1, 2, 3 are accepted by the query and normally match no rows."),
    ]),
    create=extend_schema(examples=[OpenApiExample(
        "Create download queue item",
        value={"source_url": "https://www.instagram.com/p/example/", "priority": 2},
        request_only=True,
    )]),
)
class DownloadQueueViewSet(viewsets.ModelViewSet):
    """ViewSet for DownloadQueue operations."""
    queryset = DownloadQueue.objects.filter(is_processed=False)
    serializer_class = DownloadQueueSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset

    @extend_schema(
        request=None,
        responses={200: QueueProcessResponseSchema, 400: ApiErrorSchema, 404: ApiErrorSchema},
        description="Creates a pending Download row and marks the queue row processed; it does not download media.",
    )
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Mark a queue item as processed and create download."""
        queue_item = self.get_object()
        
        if queue_item.is_processed:
            return Response(
                {'error': 'Already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create download record
        download = Download.objects.create(
            source_url=queue_item.source_url,
            media_type=queue_item.media_type or 'image',
            target_username=queue_item.target_username,
            account=queue_item.account,
            status='pending',
        )
        
        # Mark as processed
        queue_item.is_processed = True
        queue_item.save()
        
        return Response({
            'message': 'Download created',
            'download_id': download.id,
        })


@extend_schema_view(
    list=extend_schema(parameters=[
        OpenApiParameter("download", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
    ]),
)
class MediaFileViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for MediaFile (read-only)."""
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        download_id = self.request.query_params.get('download')
        if download_id:
            queryset = queryset.filter(download_id=download_id)
        return queryset


class DownloadHistoryView(APIView):
    """Get download history with filtering."""

    @extend_schema(
        parameters=[
            OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("limit", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False, default=50),
        ],
        responses={200: DownloadSerializer(many=True), 500: ApiErrorSchema},
    )
    def get(self, request):
        downloads = Download.objects.all()
        
        # Date filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            downloads = downloads.filter(created_at__date__gte=start_date)
        if end_date:
            downloads = downloads.filter(created_at__date__lte=end_date)
        
        # Limit results
        limit = int(request.query_params.get('limit', 50))
        downloads = downloads[:limit]
        
        serializer = DownloadSerializer(downloads, many=True)
        return Response(serializer.data)
