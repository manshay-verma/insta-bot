from django.db import models
from django.utils import timezone


class Download(models.Model):
    """Track media downloads."""
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('reel', 'Reel'),
        ('story', 'Story'),
        ('carousel', 'Carousel'),
        ('profile_pic', 'Profile Picture'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    source_url = models.TextField()
    s3_key = models.TextField(null=True, blank=True)
    local_path = models.TextField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    account = models.ForeignKey(
        'account.BotAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='downloads'
    )
    target_username = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['media_type']),
        ]

    def __str__(self):
        return f"{self.media_type} - {self.status}"


class MediaFile(models.Model):
    """Reference to downloaded media files."""
    download = models.ForeignKey(
        Download,
        on_delete=models.CASCADE,
        related_name='files'
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    s3_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class DownloadQueue(models.Model):
    """Queue for pending downloads."""
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Normal'),
        (3, 'High'),
    ]

    source_url = models.TextField()
    media_type = models.CharField(max_length=20, null=True, blank=True)
    target_username = models.CharField(max_length=50, null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    account = models.ForeignKey(
        'account.BotAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f"Queue: {self.source_url[:50]}..."
