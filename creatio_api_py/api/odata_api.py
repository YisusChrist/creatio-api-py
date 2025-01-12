import os
from functools import wraps
from typing import Any
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass
from requests import Response
from requests import Session
from requests import TooManyRedirects
from requests_cache import CachedSession

from .auth import authenticate
from .collections import add_to_collection
from .collections import delete_from_collection
from .collections import get_collection
from .collections import modify_collection
from .cookies import CookieManager
from .requests_utils import build_headers
from .requests_utils import make_request
from .session_manager import SessionManager


@dataclass(config={"arbitrary_types_allowed": True})
class CreatioODataAPI:
    """A class to interact with the Creatio OData API."""

    base_url: HttpUrl
    debug: bool = False
    cache: bool = False
    __cookie_manager: CookieManager = Field(init=False)
    __session: Session | CachedSession = Field(init=False)
    __api_calls: int = Field(default=0, init=False)
    __username: str = ""

    def __post_init__(self) -> None:
        """Initialize the session based on the cache setting."""
        self.session_manager = SessionManager(use_cache=self.cache)
        self.__session: Session | CachedSession = self.session_manager.session
        load_dotenv()
        # Load the encryption key from an environment variable
        encryption_key: str | None = os.getenv("SESSIONS_ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError(
                "Encryption key not found, please set the 'SESSIONS_ENCRYPTION_KEY' environment variable."
            )
        self.__cookie_manager = CookieManager(encryption_key)

    @property
    def api_calls(self) -> int:
        """Property to get the number of API calls performed."""
        return self.__api_calls

    @property
    def session_cookies(self) -> dict[str, Any]:
        """Property to get the session cookies."""
        return self.__session.cookies.get_dict()

    @property
    def session(self) -> Session | CachedSession:
        """Property to get the session."""
        return self.__session

    @property
    def username(self) -> str:
        """Property to get the username."""
        return self.__username

    @username.setter
    def username(self, username: str) -> None:
        """Property to set the username"""
        if not username:
            raise ValueError("Username cannot be empty")
        self.__username = username

    """
    def __init__(self, base_url: str, debug: bool = False, cache: bool = False) -> None:
        self.base_url: str = base_url.rstrip("/") + "/"
        self.debug: bool = debug
        self.session_manager = SessionManager(use_cache=cache)
        self.session: Session | CachedSession = self.session_manager.session
        load_dotenv()
        # Load the encryption key from an environment variable
        encryption_key: str | None = os.getenv("SESSIONS_ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError(
                "Encryption key not found, please set the 'SESSIONS_ENCRYPTION_KEY' environment variable."
            )
        self.cookie_manager = CookieManager(encryption_key)
        self.username: str = ""
    """

    def make_request(
        self, method: str, endpoint: str, **kwargs: dict[str, Any]
    ) -> Response:
        """Send an HTTP request using the session."""
        headers: dict[str, str] = build_headers(
            self.session_cookies,
            endpoint,
            method,
        )
        response: Response = make_request(
            self,
            self.session,
            self.debug,
            method,
            str(self.base_url),
            endpoint,
            headers,
            kwargs.get("data"),
            kwargs.get("params"),
        )

        self.__api_calls += 1

        return response

    def load_session_cookie(self, username: str) -> bool:
        """Load the session cookie for the given username."""
        url = str(self.base_url)
        cookies: dict[str, dict[str, Any]] = self.__cookie_manager.read_cookies()
        if url not in cookies or username not in cookies[url]:
            return False

        self.session.cookies.update(cookies[url][username])

        # TODO: Find a more reliable and efficient way to check if the session
        # cookie is still valid
        # Check if the session cookie is still valid
        try:
            response: Response = self.get_collection_data("Account/$count")
            # Check if the request was redirected to the login page
            return not response.history
        except TooManyRedirects:
            return False

    def store_session_cookie(self, username: str) -> None:
        """Store the session cookie for the given username."""
        url = str(self.base_url)
        all_cookies: dict[str, dict[str, Any]] = self.__cookie_manager.read_cookies()

        all_cookies.setdefault(url, {})
        all_cookies[url].setdefault(username, {})
        all_cookies[url][username] = self.session_cookies
        self.__cookie_manager.write_cookies(all_cookies)

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> Response:
        return authenticate(self, username, password)

    # @wraps(get_collection)
    def get_collection_data(
        self, collection: str, **kwargs: dict[str, Any]
    ) -> Response:
        return get_collection(self, collection, **kwargs)

    # @wraps(add_to_collection)
    def add_collection_data(self, collection: str, data: dict[str, Any]) -> Response:
        return add_to_collection(self, collection, data)

    # @wraps(modify_collection)
    def modify_collection_data(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> Response:
        return modify_collection(self, collection, record_id, data)

    # @wraps(delete_from_collection)
    def delete_collection_data(self, collection: str, record_id: str) -> Response:
        return delete_from_collection(self, collection, record_id)
