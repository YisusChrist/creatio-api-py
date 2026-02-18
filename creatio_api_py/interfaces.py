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
    session_file: Path
    username: str
    password: str
    client_id: str
    client_secret: str
    oauth_token: Optional[str]
    api_calls: int

    # --- Properties ---
    @property
    def session_cookies(self) -> dict[str, Any]: ...
    @property
    def session(self) -> requests.Session | requests_cache.CachedSession: ...
    @property
    def encryption_manager(self) -> EncryptedCookieManager: ...

    # --- Methods from CollectionOperationsMixin ---
    def get_collection_data(
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
        property: Optional[str] = None,
    ) -> Response: ...
    def add_collection_data(
        self, collection: str, data: dict[str, Any]
    ) -> Response: ...
    def modify_collection_data(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> Response: ...
    def delete_collection_data(self, collection: str, record_id: str) -> Response: ...
    def put_field_collection_data(
        self, collection: str, record_id: str, property: str, data: str
    ) -> Response: ...
    def delete_field_collection_data(
        self, collection: str, record_id: str, property: str
    ) -> Response: ...

    # --- Methods from FileOperationsMixin ---
    def download_file(
        self, collection: str, file_id: str, path: str | Path
    ) -> Response: ...
    def upload_file(
        self, collection: str, entity_id: str, file_path: str | Path
    ) -> Response: ...
    
    # --- Methods from DashboardOperationsMixin ---
    def export_dashboard(
        self,
        dashboard_id: str,
        dashboard_name: str,
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
