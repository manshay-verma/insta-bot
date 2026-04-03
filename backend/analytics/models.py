from django.db import models
from django.utils import timezone


class DailyAnalytics(models.Model):
    """Daily aggregated analytics per account."""
    date = models.DateField()
    account = models.ForeignKey(
        'account.BotAccount',
        on_delete=models.CASCADE,
        related_name='daily_analytics'
    )
    follows_count = models.IntegerField(default=0)
    unfollows_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    downloads_count = models.IntegerField(default=0)
    profiles_explored = models.IntegerField(default=0)
    stories_viewed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['date', 'account']
        ordering = ['-date']
        verbose_name_plural = "Daily Analytics"

    def __str__(self):
        return f"{self.account.username} - {self.date}"


class ActionLog(models.Model):
    """Log of individual bot actions."""
    ACTION_TYPES = [
        ('follow', 'Follow'),
        ('unfollow', 'Unfollow'),
        ('like', 'Like'),
        ('unlike', 'Unlike'),
        ('comment', 'Comment'),
        ('view_story', 'View Story'),
        ('download', 'Download'),
        ('scrape_profile', 'Scrape Profile'),
        ('scrape_posts', 'Scrape Posts'),
    ]

    account = models.ForeignKey(
        'account.BotAccount',
        on_delete=models.CASCADE,
        related_name='action_logs'
    )
    session = models.ForeignKey(
        'account.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    target_username = models.CharField(max_length=50, null=True, blank=True)
    target_url = models.TextField(null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account', 'action_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.action_type} by {self.account.username}"


class UserBehavior(models.Model):
    """Track user behavioral patterns for ML training."""
    account = models.ForeignKey(
        'account.BotAccount',
        on_delete=models.CASCADE,
        related_name='behaviors'
    )
    behavior_type = models.CharField(max_length=50)
    data = models.JSONField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.behavior_type} - {self.account.username}"
