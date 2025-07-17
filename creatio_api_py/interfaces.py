# interfaces.py
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Protocol

import requests
import requests_cache
from pydantic import HttpUrl
from requests import Response

from creatio_api_py.encryption import EncryptedCookieManager


class CreatioAPIInterface(Protocol):
    # --- Attributes ---
    base_url: HttpUrl
    debug: bool
    cache: bool
    cookies_file: Path
    oauth_file: Path

    # --- Properties ---

    @property
    def api_calls(self) -> int: ...
    @api_calls.setter
    def api_calls(self, value: int) -> None: ...

    @property
    def session_cookies(self) -> dict[str, Any]: ...

    @property
    def session(self) -> requests.Session | requests_cache.CachedSession: ...

    @property
    def username(self) -> str: ...
    @username.setter
    def username(self, value: str) -> None: ...

    @property
    def password(self) -> str: ...
    @password.setter
    def password(self, value: str) -> None: ...

    @property
    def encryption_manager(self) -> EncryptedCookieManager: ...

    @property
    def oauth_token(self) -> Optional[str]: ...
    @oauth_token.setter
    def oauth_token(self, value: Optional[str]) -> None: ...

    @property
    def client_id(self) -> Optional[str]: ...
    @client_id.setter
    def client_id(self, value: Optional[str]) -> None: ...

    @property
    def client_secret(self) -> Optional[str]: ...
    @client_secret.setter
    def client_secret(self, value: Optional[str]) -> None: ...

    # --- Methods from CollectionOperationsMixin ---
    def get_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        params: Optional[dict[str, str | int]] = None,
        record_id: Optional[str] = None,
        only_count: Optional[bool] = None,
        count: Optional[bool] = None,
        skip: Optional[int] = None,
        top: Optional[int] = None,
        select: Optional[str | list[str]] = None,
        expand: Optional[str | list[str]] = None,
        value: Optional[str] = None,
        order_by: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> Response: ...
    def add_collection_data(
        self, collection: str, data: dict[str, Any]
    ) -> Response: ...
    def delete_collection_data(self, collection: str, record_id: str) -> Response: ...

    # --- Methods from FileOperationsMixin ---
    def download_file(
        self,
        collection: str,
        file_id: str,
        path: str | Path,
    ) -> Response: ...
    def upload_file(
        self,
        collection: str,
        entity_id: str,
        file_path: str | Path,
    ) -> Response: ...

    # --- Methods from AuthenticationMixin ---
    def authenticate(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        identity_service_url: Optional[str] = None,
        cache: bool = True,
    ) -> Response: ...
