"""Encryption module for encrypting and decrypting cookies."""

import json
from typing import Any
from pathlib import Path

from cryptography.fernet import Fernet


def _create_encryption_key() -> str:
    """Creates an encryption key."""
    key: str = Fernet.generate_key().decode()
    print(f"Generated new key: {key}")
    choice: str = input("Do you want to save the key? (y/n): ").strip().lower()
    if choice == "y":
        env_file_path: Path = Path(".env").resolve()
        write_mode: str = "w" if not env_file_path.exists() else "a"
        
        with open(env_file_path, write_mode) as env_file:
            env_file.write(f'SESSIONS_ENCRYPTION_KEY="{key}"\n')
            
        print(f"Key saved to {env_file_path}")
                    
    return key


class EncryptedCookieManager:
    def __init__(self, key: str | None) -> None:
        if not key:
            print("Encryption key is not set in the environment.")
            choice: str = input("Do you want to generate a new key? (y/n): ").strip().lower()
            if choice != "y":
                raise ValueError("Encryption key is required for encryption/decryption.")

            key = _create_encryption_key()
        
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
