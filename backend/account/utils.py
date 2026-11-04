"""
Password encryption utility for bot accounts.
Uses Fernet symmetric encryption for secure password storage.
"""
from cryptography.fernet import Fernet
import base64
import hashlib
import os
import time


def get_encryption_key():
    """Get or generate encryption key from environment or settings."""
    # In production, this should come from environment variable
    secret = os.environ.get('DJANGO_SECRET_KEY', 'default-secret-key-change-in-production')
    # Derive a 32-byte key from the secret
    key = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_password(plain_password: str) -> str:
    """Encrypt a password for storage."""
    key = get_encryption_key()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(plain_password.encode())
    return encrypted.decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored password."""
    key = get_encryption_key()
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_password.encode())
    return decrypted.decode()


def verify_password(plain_password: str, encrypted_password: str) -> bool:
    """Verify a password against its encrypted version."""
    try:
        decrypted = decrypt_password(encrypted_password)
        return plain_password == decrypted
    except Exception:
        return False


def get_cookie_encryption_key() -> bytes:
    secret = (
        os.environ.get('INSTABOT_COOKIE_ENCRYPTION_KEY')
        or os.environ.get('DJANGO_SECRET_KEY')
        or 'default-secret-key-change-in-production'
    )
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def encrypt_cookie_data(cookie_data) -> str:
    import json
    payload = json.dumps(cookie_data, separators=(',', ':'), ensure_ascii=True).encode()
    return Fernet(get_cookie_encryption_key()).encrypt(payload).decode()


def decrypt_cookie_data(encrypted_data: str):
    import json
    payload = Fernet(get_cookie_encryption_key()).decrypt(encrypted_data.encode())
    return json.loads(payload.decode())


def normalize_and_validate_cookies(cookie_data):
    import json

    if isinstance(cookie_data, dict) and isinstance(cookie_data.get("cookies"), list):
        cookies = cookie_data["cookies"]
    elif isinstance(cookie_data, list):
        cookies = cookie_data
    else:
        return None

    normalized = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            return None
        if not cookie.get("name") or not isinstance(cookie.get("value"), (str, int, float)):
            return None
        domain = str(cookie.get("domain", "")).lower()
        if domain not in ("instagram.com", ".instagram.com") and not domain.endswith(".instagram.com"):
            return None
        expires = cookie.get("expires")
        if isinstance(expires, (int, float)) and expires > 0 and expires <= time.time():
            return None
        normalized.append(dict(cookie))

    cookie_names = {cookie["name"] for cookie in normalized}
    if not normalized or "sessionid" not in cookie_names or "csrftoken" not in cookie_names:
        return None
    return normalized
