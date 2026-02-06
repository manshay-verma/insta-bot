from django.db import models

class Proxy(models.Model):
    host = models.CharField(max_length=255)
    port = models.IntegerField()
    protocol = models.CharField(max_length=10, default='http')
    country_code = models.CharField(max_length=2, null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"

    class Meta:
        verbose_name_plural = "Proxies"

class BotAccount(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('banned', 'Banned'),
        ('checkpoint', 'Checkpoint'),
    ]

    username = models.CharField(max_length=50, unique=True)
    password_encrypted = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    trust_score = models.DecimalField(max_digits=3, decimal_length=2, default=0.50)
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    last_login = models.DateTimeField(null=True, blank=True)
    cookies_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
