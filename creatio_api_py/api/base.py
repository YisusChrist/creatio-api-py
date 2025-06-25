"""API module for the Creatio OData API."""

import os
from pathlib import Path
from typing import Any
from typing import Optional

import requests
import requests_cache
from dotenv import load_dotenv
from pydantic import Field
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass
from rich import print  # pylint: disable=redefined-builtin

from creatio_api_py.api.auth import authenticate
from creatio_api_py.api.operations.collections import add_to_collection
from creatio_api_py.api.operations.collections import delete_from_collection
from creatio_api_py.api.operations.collections import get_collection_data
from creatio_api_py.api.operations.collections import modify_collection
from creatio_api_py.api.operations.files import download_file
from creatio_api_py.api.operations.files import upload_file
from creatio_api_py.api.request_handler import make_request
from creatio_api_py.encryption import EncryptedCookieManager
from creatio_api_py.logs import logger


@dataclass(config={"arbitrary_types_allowed": True})
class CreatioODataAPI:
    """A class to interact with the Creatio OData API."""

    base_url: HttpUrl
    debug: bool = False
    cache: bool = False
    cookies_file: Path = Path(".creatio_sessions.bin")
    oauth_file: Path = Path("oauth.json")
    __api_calls: int = Field(default=0, init=False)
    __session: requests.Session | requests_cache.CachedSession = Field(init=False)
    __username: str = Field(default="", init=False)
    __password: str = Field(default="", init=False)
    __encryption_manager: EncryptedCookieManager = Field(init=False)
    __oauth_token: Optional[str] = Field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize the session based on the cache setting."""
        if self.cache:
            cached_backend = requests_cache.SQLiteCache(
                db_path="creatio_cache", use_cache_dir=True
            )
            self.__session = requests_cache.CachedSession(
                backend=cached_backend, expire_after=3600
            )
        else:
            self.__session = requests.Session()

        message: str = (
            f"Session initialized with cache={self.cache} and base_url={self.base_url}."
        )
        logger.debug(message)
        if self.debug:
            print(f"[bold green]{message}[/]")

        self._load_env()
        # Load the encryption key from an environment variable
        encryption_key: str | None = os.getenv("SESSIONS_ENCRYPTION_KEY")
        self.__encryption_manager = EncryptedCookieManager(encryption_key)

    @property
    def api_calls(self) -> int:
        """Property to get the number of API calls performed."""
        return self.__api_calls

    @api_calls.setter
    def api_calls(self, value: int) -> None:
        """Property to set the number of API calls performed."""
        if value < 0:
            raise ValueError("API calls cannot be negative")
        self.__api_calls = value

    @property
    def session_cookies(self) -> dict[str, Any]:
        """Property to get the session cookies."""
        return self.__session.cookies.get_dict()

    @property
    def session(self) -> requests.Session | requests_cache.CachedSession:
        """Property to get the session."""
        return self.__session

    @property
    def username(self) -> str:
        """Property to get the username."""
        return self.__username

    @username.setter
    def username(self, value: str) -> None:
        """Property to set the username"""
        if not value:
            raise ValueError("Username cannot be empty")
        self.__username = value

    @property
    def password(self) -> str:
        """Property to get the password."""
        return self.__password

    @password.setter
    def password(self, value: str) -> None:
        """Property to set the password"""
        if not value:
            raise ValueError("Password cannot be empty")
        self.__password = value

    @property
    def encryption_manager(self) -> EncryptedCookieManager:
        """Property to get the encryption manager."""
        return self.__encryption_manager

    @property
    def oauth_token(self) -> Optional[str]:
        """Property to get the OAuth token."""
        return self.__oauth_token

    @oauth_token.setter
    def oauth_token(self, value: Optional[str]) -> None:
        """Property to set the OAuth token."""
        if not value:
            raise ValueError("OAuth token cannot be empty")
        self.__oauth_token = value

    def _load_env(self) -> None:
        """Load the environment variables from the .env file."""
        env_vars_loaded: bool = load_dotenv(".env")
        if env_vars_loaded:
            logger.info("Environment variables loaded successfully")
        else:
            logger.warning("Environment variables could not be loaded")

    def make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.models.Response:
        return make_request(self, method, endpoint, headers=headers, **kwargs)

    def authenticate(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        identity_service_url: Optional[str] = None,
        cache: bool = True,
    ) -> requests.models.Response:
        return authenticate(
            self,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            identity_service_url=identity_service_url,
            cache=cache,
        )

    def get_collection_data(
        self, collection: str, **kwargs: Any
    ) -> requests.models.Response:
        return get_collection_data(self, collection, **kwargs)

    def add_collection_data(
        self, collection: str, data: dict[str, Any]
    ) -> requests.models.Response:
        return add_to_collection(self, collection, data)

    def modify_collection_data(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> requests.models.Response:
        return modify_collection(self, collection, record_id, data)

    def delete_collection_data(
        self, collection: str, record_id: str
    ) -> requests.models.Response:
        return delete_from_collection(self, collection, record_id)

    def download_file(
        self, collection: str, file_id: str, path: str | Path = Path.cwd()
    ) -> requests.models.Response:
        return download_file(self, collection, file_id, path)

    def upload_file(
        self, collection: str, entity_id: str, file_path: str | Path
    ) -> requests.models.Response:
        return upload_file(self, collection, entity_id, file_path)
