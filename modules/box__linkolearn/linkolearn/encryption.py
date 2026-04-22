import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


def derive_key_from_password(password: str, salt: bytes = None) -> bytes:
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()


def get_fernet(key: str) -> Fernet:
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_url(url: str, encryption_key: str) -> str:
    f = get_fernet(encryption_key)
    encrypted = f.encrypt(url.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_url(encrypted_url: str, encryption_key: str) -> str:
    try:
        f = get_fernet(encryption_key)
        encrypted = base64.urlsafe_b64decode(encrypted_url.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception:
        return encrypted_url
