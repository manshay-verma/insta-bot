import hmac
import re
from types import SimpleNamespace

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class WorkerTokenAuthentication(BaseAuthentication):
    """Authenticate the trusted automation worker on its limited API surface."""

    allowed_paths = (
        (re.compile(r"^/api/v1/accounts/\d+/$"), frozenset({"GET"})),
        (
            re.compile(r"^/api/v1/accounts/\d+/update_cookies/$"),
            frozenset({"POST"}),
        ),
        (re.compile(r"^/api/v1/bots/control/$"), frozenset({"POST"})),
        (re.compile(r"^/api/v1/sessions/\d+/end/$"), frozenset({"POST"})),
        (re.compile(r"^/api/v1/analytics/actions/$"), frozenset({"POST"})),
        (re.compile(r"^/api/v1/health/$"), frozenset({"GET"})),
    )

    def authenticate(self, request):
        supplied = request.headers.get("X-Worker-Token")
        if supplied is None:
            return None

        configured = getattr(settings, "INSTABOT_WORKER_TOKEN", "")
        if not configured or not hmac.compare_digest(supplied, configured):
            raise AuthenticationFailed("Invalid worker credentials.")
        allowed_methods = next(
            (
                methods
                for pattern, methods in self.allowed_paths
                if pattern.fullmatch(request.path)
            ),
            None,
        )
        if allowed_methods is None:
            raise AuthenticationFailed("Worker credentials are not permitted for this endpoint.")
        if request.method not in allowed_methods:
            raise AuthenticationFailed("Worker credentials are not permitted for this method.")

        principal = SimpleNamespace(
            username="automation-worker",
            is_authenticated=True,
            is_anonymous=False,
            is_staff=False,
            is_superuser=False,
        )
        return principal, "worker"

    def authenticate_header(self, request):
        return "X-Worker-Token"
