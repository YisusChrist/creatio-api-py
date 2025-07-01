# interfaces.py
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Protocol

from pydantic import HttpUrl
from requests import Response
from requests import Session

from creatio_api_py.encryption import EncryptedCookieManager


class CreatioAPIInterface(Protocol):
    # --- Attributes ---
    base_url: HttpUrl
    debug: bool
    username: str
    password: str

    cookies_file: Path
    oauth_file: Path

    session: Session
    session_cookies: dict[str, Any]
    oauth_token: Optional[str]
    encryption_manager: EncryptedCookieManager
    api_calls: int

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
