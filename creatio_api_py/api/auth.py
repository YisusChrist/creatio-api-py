import json
import os
from typing import Any
from typing import Optional

from core_helpers.logs import logger
from requests.models import Response

from creatio_api_py.api.request_handler import make_request
from creatio_api_py.api.sessions import load_session_cookie
from creatio_api_py.api.sessions import store_session_cookie
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import log_and_print


def _oauth_authentication(
    api_instance: CreatioAPIInterface,
    client_id: str,
    client_secret: str,
    cache: bool,
    identity_service_url: Optional[str] = None,
) -> Response:
    """
    Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#11dde5c2-4a77-4248-b8a6-c75035faa5cc

    Authenticate using OAuth credentials.

    Args:
        api_instance (CreatioODataAPI): The API instance to use for authentication.
        client_id (str): The client ID for OAuth.
        client_secret (str): The client secret for OAuth.
        cache (bool): Whether to use cached OAuth tokens.
        identity_service_url (Optional[str], optional): The URL of the identity service.

    Returns:
        Response: The response from the authentication request.
    """
    api_instance.client_id, api_instance.client_secret = client_id, client_secret
    if cache and api_instance.oauth_file.exists():
        with open(api_instance.oauth_file, "r") as f:
            oauth_data: dict[str, str] = json.load(f)

        api_instance.oauth_token = oauth_data.get("access_token")
        return Response()  # Simulate successful response

    logger.info("No valid OAuth token found")
    data: dict[str, str] = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # By default, the identity service URL is constructed from the base URL
    # by adding the suffix "-is" to the subdomain.
    identity_service_url = identity_service_url or (
        str(api_instance.base_url)
        .rstrip("/")
        .replace(".creatio.com", "-is.creatio.com")
        + "/connect/token"
    )

    response: Response = api_instance.session.post(identity_service_url, data=data)
    response.raise_for_status()

    api_instance.oauth_token = response.json().get("access_token")

    with open(api_instance.oauth_file, "w") as f:
        json.dump(response.json(), f, indent=4)

    return response


def _session_authentication(
    api_instance: CreatioAPIInterface,
    username: str,
    password: str,
    cache: bool,
) -> Response:
    """
    Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#46f97170-d66d-4ed9-8941-08590bcdf444

    Authenticate using session-based credentials.

    Args:
        self (CreatioODataAPI): The API instance to use for authentication.
        username (str): The username for authentication.
        password (str): The password for authentication.
        cache (bool): Whether to use cached session cookies.

    Returns:
        Response: The response from the authentication request.
    """
    api_instance.username, api_instance.password = username, password
    # Attempt to load a cached session cookie for this username
    if cache and load_session_cookie(api_instance, username):
        message: str = f"Using cached session cookie for user {username}."
        logger.debug(message)
        if api_instance.debug:
            print(message)
        return Response()  # Simulate successful response

    logger.info("No valid session cookie found")
    # Clear the session cookies
    api_instance.session.cookies.clear()
    data: dict[str, str] = {"UserName": username, "UserPassword": password}

    response: Response = make_request(
        api_instance, "POST", "ServiceModel/AuthService.svc/Login", json=data
    )
    response_json: dict[str, Any] = response.json()
    if response_json.get("Exception"):
        error_message: str = response_json["Exception"]["Message"]
        logger.error(error_message)
        raise ValueError(error_message)

    # Extract the cookie from the response
    api_instance.session_cookies.update(response.cookies)
    store_session_cookie(api_instance, username)

    return response


class AuthenticationMixin:
    """
    Mixin class for authentication methods in Creatio API.
    Provides methods to authenticate using session-based or OAuth credentials.
    """

    def authenticate(
        self: CreatioAPIInterface,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        identity_service_url: Optional[str] = None,
        cache: bool = True,
    ) -> Response:
        """
        Authenticate and get a cookie.

        Args:
            self (CreatioODataAPI): The API instance to use for authentication.
            username (Optional[str], optional): The username to authenticate with.
            password (Optional[str], optional): The password to authenticate with.
            client_id (Optional[str], optional): The client ID for OAuth authentication.
            client_secret (Optional[str], optional): The client secret for OAuth authentication.
            identity_service_url (Optional[str], optional): The URL of the identity service for OAuth authentication.
            cache (bool, optional): Whether to use cached session cookies. Defaults to True.

        Raises:
            ValueError: If the username or password is empty or if the authentication fails.

        Returns:
            Response: The response from the authentication request.
        """
        username = username or os.getenv("CREATIO_USERNAME") or self.username
        password = password or os.getenv("CREATIO_PASSWORD") or self.password
        client_id = client_id or os.getenv("CREATIO_CLIENT_ID") or self.client_id
        client_secret = (
            client_secret or os.getenv("CREATIO_CLIENT_SECRET") or self.client_secret
        )

        if all([client_id, client_secret, username, password]):
            error_message: str = (
                "Cannot use both oauth credentials and username/password for authentication."
            )
            log_and_print(error_message, ValueError(error_message), self.debug)
            raise ValueError(error_message)

        if not any([username, password, client_id, client_secret]):
            error_message = "No credentials provided for authentication"
            log_and_print(error_message, ValueError(error_message), self.debug)
            raise ValueError(error_message)

        if client_id and client_secret:
            # Use OAuth authentication
            return _oauth_authentication(
                self,
                client_id,
                client_secret,
                cache,
                identity_service_url=identity_service_url,
            )
        elif username and password:
            # Use session-based authentication
            return _session_authentication(self, username, password, cache)

        error_message = "Invalid authentication method. Provide either username/password or client_id/client_secret."
        logger.error(error_message)
        raise ValueError(error_message)
