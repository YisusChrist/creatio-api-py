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

from creatio_api_py.api.auth import AuthenticationMixin
from creatio_api_py.api.operations.collections import CollectionOperationsMixin
from creatio_api_py.api.operations.files import FileOperationsMixin
from creatio_api_py.encryption import EncryptedCookieManager
from creatio_api_py.logs import logger


@dataclass(config={"arbitrary_types_allowed": True})
class CreatioODataAPI(
    AuthenticationMixin, CollectionOperationsMixin, FileOperationsMixin
):
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
    __client_id: str = Field(default="", init=False)
    __client_secret: str = Field(default="", init=False)

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
        
    @property
    def client_id(self) -> str:
        """Property to get the client ID."""
        return self.__client_id
    
    @client_id.setter
    def client_id(self, value: str) -> None:
        """Property to set the client ID."""
        if not value:
            raise ValueError("Client ID cannot be empty")
        self.__client_id = value
        
    @property
    def client_secret(self) -> str:
        """Property to get the client secret."""
        return self.__client_secret
    
    @client_secret.setter
    def client_secret(self, value: str) -> None:
        """Property to set the client secret."""
        if not value:
            raise ValueError("Client secret cannot be empty")
        self.__client_secret = value

    def _load_env(self) -> None:
        """Load the environment variables from the .env file."""
        env_vars_loaded: bool = load_dotenv(".env")
        if env_vars_loaded:
            logger.info("Environment variables loaded successfully")
        else:
            logger.warning("Environment variables could not be loaded")
