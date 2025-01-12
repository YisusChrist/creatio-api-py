from pathlib import Path
from typing import Any
from rich import print

from creatio_api_py.encryption import EncryptedCookieManager


class CookieManager:
    def __init__(
        self, encryption_key: str, cookies_file: Path = Path(".creatio_sessions.bin")
    ) -> None:
        self.encryption_manager = EncryptedCookieManager(encryption_key.encode())
        self.cookies_file: Path = cookies_file

    def read_cookies(self) -> dict[str, dict[str, Any]]:
        """
        Read and decrypt the encrypted cookies file.

        Returns:
            dict: The decrypted cookies data, or an empty dictionary if the file
                does not exist or decryption fails.
        """
        if not self.cookies_file.exists():
            return {}

        try:
            encrypted_data: bytes = self.cookies_file.read_bytes()
            data = self.encryption_manager.decrypt(encrypted_data)
            print("Stored cookies:", data)
            return data

        except Exception:
            return {}

    def write_cookies(self, data: dict[str, Any]) -> None:
        encrypted_data: bytes = self.encryption_manager.encrypt(data)
        self.cookies_file.write_bytes(encrypted_data)
