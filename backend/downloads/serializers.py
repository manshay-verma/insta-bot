from rest_framework import serializers
from .models import Download, MediaFile, DownloadQueue


class MediaFileSerializer(serializers.ModelSerializer):
    """Serializer for MediaFile model."""

    class Meta:
        model = MediaFile
        fields = ['id', 'filename', 'content_type', 'file_size', 's3_url', 'created_at']
        read_only_fields = ['id', 'created_at']


class DownloadSerializer(serializers.ModelSerializer):
    """Serializer for Download model."""
    files = MediaFileSerializer(many=True, read_only=True)
    account_username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = Download
        fields = [
            'id', 'media_type', 'source_url', 's3_key', 'local_path',
            'file_size_bytes', 'status', 'error_message', 'account',
            'account_username', 'target_username', 'created_at',
            'downloaded_at', 'files'
        ]
        read_only_fields = ['id', 'created_at', 'downloaded_at', 'files']


class DownloadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating downloads."""

    class Meta:
        model = Download
        fields = ['source_url', 'media_type', 'account', 'target_username']


class DownloadQueueSerializer(serializers.ModelSerializer):
    """Serializer for DownloadQueue model."""
    account_username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = DownloadQueue
        fields = [
            'id', 'source_url', 'media_type', 'target_username',
            'priority', 'account', 'account_username', 'is_processed', 'created_at'
        ]
        read_only_fields = ['id', 'is_processed', 'created_at']


class BulkDownloadSerializer(serializers.Serializer):
    """Serializer for bulk download requests."""
    urls = serializers.ListField(
        child=serializers.URLField(),
        min_length=1,
        max_length=50
    )
    media_type = serializers.ChoiceField(
        choices=['image', 'video', 'reel', 'story', 'carousel', 'profile_pic'],
        required=False
    )
    account_id = serializers.IntegerField(required=False)
    target_username = serializers.CharField(max_length=50, required=False)
    priority = serializers.ChoiceField(choices=[1, 2, 3], default=2)


class DownloadStatusSerializer(serializers.Serializer):
    """Serializer for download status response."""
    download_id = serializers.IntegerField()
    status = serializers.CharField()
    progress_percent = serializers.IntegerField()
    file_size_bytes = serializers.IntegerField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
