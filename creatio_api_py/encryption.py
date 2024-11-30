"""Encryption module for encrypting and decrypting cookies."""

import json
from typing import Any

from cryptography.fernet import Fernet


class EncryptedCookieManager:
    def __init__(self, key: bytes) -> None:
        self.fernet = Fernet(key)

    def encrypt(self, data: dict[str, Any]) -> bytes:
        """Encrypts a dictionary."""
        return self.fernet.encrypt(json.dumps(data).encode())

    def decrypt(self, encrypted_data: bytes) -> dict[str, Any]:
        """Decrypts the encrypted data."""
        sessions: dict[str, Any] = json.loads(
            self.fernet.decrypt(encrypted_data).decode()
        )
        return sessions
