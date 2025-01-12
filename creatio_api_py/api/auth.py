import os
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING

from requests.models import Response

from creatio_api_py.utils import print_exception


if TYPE_CHECKING:
    from .odata_api import CreatioODataAPI


def authenticate(
    api_instance: "CreatioODataAPI", username: Optional[str], password: Optional[str]
) -> Response:
    """
    Authenticate and get a cookie.

    Args:
        username (Optional[str], optional): The username to authenticate with.
        password (Optional[str], optional): The password to authenticate with.

    Raises:
        ValueError: If the username or password is empty or if the authentication fails.

    Returns:
        requests.models.Response: The response from the authentication request.
    """
    username = username or os.getenv("CREATIO_USERNAME", "")
    password = password or os.getenv("CREATIO_PASSWORD", "")
    if not username or not password:
        raise ValueError("Username or password empty")

    api_instance.username = username
    if api_instance.load_session_cookie(username):
        return Response()  # Simulate successful response

    api_instance.session.cookies.clear()
    data: dict[str, str] = {"UserName": username, "UserPassword": password}
    try:
        response: Response = api_instance.make_request(
            "POST", "ServiceModel/AuthService.svc/Login", data=data
        )
        response_json: dict[str, Any] = response.json()
        if response_json.get("Exception"):
            raise PermissionError(response_json["Exception"]["Message"])
        api_instance.session.cookies.update(response.cookies)
        api_instance.store_session_cookie(username)
        return response
    except Exception as e:
        print_exception(e)
        raise
