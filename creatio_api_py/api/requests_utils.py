import json
from typing import Any
from typing import TYPE_CHECKING

from requests.exceptions import RequestException
from requests.models import Response
from requests.sessions import Session
from requests_cache import CachedSession
from requests_pprint import print_response_summary

from creatio_api_py.utils import print_exception

if TYPE_CHECKING:
    from .odata_api import CreatioODataAPI


def build_headers(
    session_cookies: dict[str, Any], endpoint: str, method: str
) -> dict[str, str]:
    """
    Build the headers for the request.

    Args:
        session_cookies (dict[str, Any]): The session cookies.
        endpoint (str): The endpoint to build the headers for.
        method (str): The method to build the headers for.

    Returns:
        dict[str, str]: The headers for the request.
    """
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "ForceUseSession": "true",
    }

    if "$metadata" not in endpoint:
        headers["Accept"] = "application/json; odata=verbose"
    if method == "PUT":
        headers["Content-Type"] = "application/octet-stream"

    bmpcsrf: str | None = session_cookies.get("BPMCSRF")
    if bmpcsrf:
        headers["BPMCSRF"] = bmpcsrf

    return headers


def make_request(
    api_instance: "CreatioODataAPI",
    session: Session | CachedSession,
    debug: bool,
    method: str,
    base_url: str,
    endpoint: str,
    headers: dict[str, str],
    data: Any = None,
    params: Any = None,
) -> Response:
    url: str = f"{base_url}{endpoint}"
    payload: str | None = json.dumps(data) if data else None
    try:
        response: Response = session.request(
            method, url, headers=headers, data=payload, params=params
        )
        response.raise_for_status()
    except RequestException as e:
        print_exception(e)
        raise

    if debug:
        print_response_summary(response)

    # If the response contains new cookies, update the session cookies
    if response.cookies and endpoint != "ServiceModel/AuthService.svc/Login":
        api_instance.session.cookies.update(response.cookies)
        api_instance.store_session_cookie(api_instance.username)

    return response
