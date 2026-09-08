"""Interfaces module to interact with the API Protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

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
    oauth_token: str | None
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
        params: dict[str, str | int] | None = None,
        record_id: str | None = None,
        only_count: bool | None = None,
        count: bool | None = None,
        skip: int | None = None,
        top: int | None = None,
        select: str | list[str] | None = None,
        expand: str | list[str] | None = None,
        value: str | None = None,
        order_by: str | None = None,
        filter: str | None = None,
        property: str | None = None,
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
    def import_excel_file(
        self,
        entity_schema_name: str,
        entity_schema_uid: str,
        file_path: str | Path,
        custom_column_mapping: dict[str, Any] | None = None,
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
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        identity_service_url: str | None = None,
        cache: bool = True,
    ) -> Response: ...
