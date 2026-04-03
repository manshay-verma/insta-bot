"""
Password encryption utility for bot accounts.
Uses Fernet symmetric encryption for secure password storage.
"""
from cryptography.fernet import Fernet
import base64
import hashlib
import os


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
