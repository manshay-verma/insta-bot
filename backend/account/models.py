from django.db import models
from django.utils import timezone


class Proxy(models.Model):
    """Proxy configuration for bot accounts."""
    PROTOCOL_CHOICES = [
        ('http', 'HTTP'),
        ('https', 'HTTPS'),
        ('socks5', 'SOCKS5'),
    ]

    host = models.CharField(max_length=255)
    port = models.IntegerField()
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICES, default='http')
    username = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=2, null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"

    class Meta:
        verbose_name_plural = "Proxies"


class BotAccount(models.Model):
    """Instagram bot account model."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('banned', 'Banned'),
        ('checkpoint', 'Checkpoint'),
        ('inactive', 'Inactive'),
    ]

    username = models.CharField(max_length=50, unique=True)
    password_encrypted = models.TextField(help_text="Encrypted password")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    trust_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.50)
    proxy = models.ForeignKey(
        Proxy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounts'
    )
    cookies_json = models.JSONField(null=True, blank=True, help_text="Session cookies")
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.status})"

    class Meta:
        ordering = ['-created_at']


class Session(models.Model):
    """Bot session tracking."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('terminated', 'Terminated'),
    ]

    account = models.ForeignKey(
        BotAccount,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    actions_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Session {self.id} - {self.account.username}"

    @property
    def duration(self):
        """Calculate session duration."""
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at

    class Meta:
        ordering = ['-started_at']
