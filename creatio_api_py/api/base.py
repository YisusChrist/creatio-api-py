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
from pydantic import field_validator
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

    # Public fields
    base_url: HttpUrl
    debug: bool = False
    cache: bool = False
    cookies_file: Path = Path(".creatio_sessions.bin")
    oauth_file: Path = Path("oauth.json")

    # Public fields with validation
    api_calls: int = Field(default=0, init=False)
    username: str = Field(default="", init=False)
    password: str = Field(default="", init=False)
    client_id: str = Field(default="", init=False)
    client_secret: str = Field(default="", init=False)
    oauth_token: Optional[str] = Field(default="", init=False)

    # Internal fields
    _session: requests.Session | requests_cache.CachedSession = Field(init=False)
    _encryption_manager: EncryptedCookieManager = Field(init=False)

    def __post_init__(self) -> None:
        """Initialize the session based on the cache setting."""
        if self.cache:
            cached_backend = requests_cache.SQLiteCache(
                db_path="creatio_cache", use_cache_dir=True
            )
            self._session = requests_cache.CachedSession(
                backend=cached_backend, expire_after=3600
            )
        else:
            self._session = requests.Session()

        message: str = (
            f"Session initialized with cache={self.cache} and base_url={self.base_url}."
        )
        logger.debug(message)
        if self.debug:
            print(f"[bold green]{message}[/]")

        self._load_env()
        # Load the encryption key from an environment variable
        encryption_key: str | None = os.getenv("SESSIONS_ENCRYPTION_KEY")
        self._encryption_manager = EncryptedCookieManager(encryption_key)

    @property
    def session(self) -> requests.Session | requests_cache.CachedSession:
        """Property to get the session."""
        return self._session

    @property
    def session_cookies(self) -> dict[str, Any]:
        """Property to get the session cookies."""
        return self.session.cookies.get_dict()

    @property
    def encryption_manager(self) -> EncryptedCookieManager:
        """Property to get the encryption manager."""
        return self._encryption_manager

    @field_validator("username", "password", "client_id", "client_secret", mode="after")
    @classmethod
    def _non_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be empty")
        return v

    @field_validator("oauth_token", mode="after")
    @classmethod
    def _non_empty_token(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("OAuth token cannot be empty if provided")
        return value

    @field_validator("api_calls", mode="after")
    @classmethod
    def _validate_api_calls(cls, v: int) -> int:
        if v < 0:
            raise ValueError("api_calls cannot be negative")
        return v

    def _load_env(self) -> None:
        """Load the environment variables from the .env file."""
        env_vars_loaded: bool = load_dotenv(".env")
        if env_vars_loaded:
            logger.info("Environment variables loaded successfully")
        else:
            logger.warning("Environment variables could not be loaded")
