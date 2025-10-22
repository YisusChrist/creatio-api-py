"""Tests for the Auth module."""

from typing import Any
from typing import Optional
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest
from pydantic import HttpUrl
from requests import Response
from requests.exceptions import SSLError

from creatio_api_py.api.auth import AuthenticationMixin


class DummyAPI(AuthenticationMixin):
    def __init__(self) -> None:
        self.session = MagicMock()
        self.oauth_file = MagicMock()
        self.base_url = "https://davissamac.creatio.com"
        self.oauth_token = None
        self.session_cookies: dict[str, Any] = {}
        self.username = None
        self.password = None
        self.debug = False


@pytest.fixture
def api() -> DummyAPI:
    return DummyAPI()


def mock_response(
    json_data: Optional[dict[str, Any]] = None, status_code: int = 200
) -> MagicMock:
    mock_resp = MagicMock(spec=Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}
    return mock_resp


@patch("creatio_api_py.api.auth.make_request")
@patch("creatio_api_py.api.auth.store_session_cookie")
@patch("creatio_api_py.api.auth.load_session_cookie", return_value=False)
def test_session_authentication_without_cache(api: DummyAPI) -> None:
    # Test the authentication method without using cache
    mock_request.return_value = mock_response({"Code": 0})
    resp = api.authenticate(username="user", password="pass", cache=False)
    assert mock_request.called
    assert isinstance(resp, MagicMock)


@patch("creatio_api_py.api.auth.load_session_cookie", return_value=True)
def test_session_authentication_with_cache(api: DummyAPI) -> None:
    # Test the authentication method using cache
    response: Response = api.authenticate(cache=True)
    # No response expected when using cache
    assert isinstance(response, Response)


def test_authentication_wrong_url(api: DummyAPI) -> None:
    with pytest.raises(SSLError) as e:
        # Test the authentication method with invalid credentials
        api.base_url = HttpUrl("https://invalid_url.creatio.com")
        api.authenticate()
    assert "host=\\'invalid_url.creatio.com\\', port=443)" in str(e)


def test_authentication_missing_credentials(api: DummyAPI) -> None:
    with pytest.raises(ValueError, match="No credentials provided"):
        # Test the authentication method with empty credentials
        api.authenticate()


def test_session_authentication_invalid_credentials(api: DummyAPI) -> None:
    with pytest.raises(ValueError) as e:
        # Test the authentication method with invalid credentials
        api.authenticate(username="invalid_user", password="invalid_pass")
    assert "Authentication error" in str(e.value)


def test_authentication_conflicting_credentials(api: DummyAPI) -> None:
    with pytest.raises(
        ValueError, match="Cannot use both oauth credentials and username/password"
    ):
        api.authenticate(
            username="user", password="pass", client_id="id", client_secret="secret"
        )


@patch(
    "creatio_api_py.api.auth.open",
    new_callable=mock_open,
    read_data='{"access_token": "cached-token"}',
)
def test_oauth_authentication_with_cache(mock_open_file, api: DummyAPI) -> None:
    api.oauth_file.exists.return_value = True
    resp = api.authenticate(client_id="id", client_secret="secret", cache=True)
    # TODO: Fails because loads credentials from ENV
    assert api.oauth_token == "cached-token"
    assert isinstance(resp, MagicMock)


@patch("creatio_api_py.api.auth.open", new_callable=mock_open)
@patch("creatio_api_py.api.auth.print_response_summary")
def test_oauth_authentication_without_cache(
    mock_summary, mock_open_file, api: DummyAPI
) -> None:
    api.oauth_file.exists.return_value = False
    api.session.post.return_value = mock_response({"access_token": "new-token"})
    resp = api.authenticate(client_id="id", client_secret="secret", cache=False)
    assert api.oauth_token == "new-token"
    assert isinstance(resp, MagicMock)  # since we mock `Response`
