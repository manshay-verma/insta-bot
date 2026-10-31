import re
from urllib.parse import urlsplit


_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def normalize_instagram_profile_target(target):
    if not isinstance(target, str) or not target.strip():
        raise ValueError("Target must not be empty.")

    value = target.strip()
    if "://" in value:
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Profile URL is malformed.") from exc

        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Profile URL must use HTTP or HTTPS.")
        if hostname not in {"instagram.com", "www.instagram.com"}:
            raise ValueError("Profile URL must belong to instagram.com.")
        if parsed.username is not None or parsed.password is not None or port is not None:
            raise ValueError("Profile URL cannot contain credentials or a port.")
        if parsed.fragment:
            raise ValueError("Profile URL cannot contain a fragment.")

        path = parsed.path[1:] if parsed.path.startswith("/") else ""
        if path.endswith("/"):
            path = path[:-1]
        if "/" in path:
            raise ValueError("Profile URL must point to a single profile.")
        value = path

    if (
        not _USERNAME_PATTERN.fullmatch(value)
        or value.startswith(".")
        or value.endswith(".")
        or ".." in value
    ):
        raise ValueError("Target must be a valid Instagram username or profile URL.")

    return value
