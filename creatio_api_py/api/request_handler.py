from typing import Any
from typing import Optional

from core_helpers.logs import logger
from requests.exceptions import HTTPError
from requests.models import Response
from requests_pprint import print_response_summary

from creatio_api_py.api.sessions import store_session_cookie
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import log_and_print


def _build_headers(
    api_instance: CreatioAPIInterface, endpoint: str, method: str
) -> dict[str, str]:
    """Construct request headers."""
    headers: dict[str, str] = {}

    if api_instance.oauth_token:
        headers["Authorization"] = f"Bearer {api_instance.oauth_token}"
    else:
        bmpcsrf: str | None = api_instance.session_cookies.get("BPMCSRF")
        if bmpcsrf:
            # Add the BPMCSRF cookie to the headers
            headers["BPMCSRF"] = bmpcsrf

        headers["ForceUseSession"] = "true"

    if "$metadata" not in endpoint:
        headers["Accept"] = "application/json; odata=verbose"

    return headers


def make_request(
    api_instance: CreatioAPIInterface,
    method: str,
    endpoint: str,
    headers: Optional[dict[str, str]] = None,
    **kwargs: Any,
) -> Response:
    """
    Make a generic HTTP request to the OData service.

    Args:
        method (str): HTTP method (GET, POST, PATCH, etc.).
        endpoint (str): The API endpoint to request.
        **kwargs (Any): Additional keyword arguments to pass to the request

    Returns:
        requests.models.Response: The response from the HTTP request.
    """
    url: str = f"{api_instance.base_url}{endpoint}"
    if not headers:
        headers = {}
    headers.update(_build_headers(api_instance, endpoint, method))

    try:
        response: Response = api_instance.session.request(
            method, url, headers=headers, **kwargs
        )
        response.raise_for_status()
    except HTTPError as e:
        log_and_print("Session expired", e, api_instance.debug)
        logger.info(f"Attempting to re-authenticate for {method} request to {url}.")
        api_instance.authenticate(cache=False)
        # Retry the request after re-authentication
        headers.update(_build_headers(api_instance, endpoint, method))
        response = api_instance.session.request(method, url, headers=headers, **kwargs)

    if api_instance.debug:
        print_response_summary(response)

    response.raise_for_status()

    # If the response contains new cookies, update the session cookies
    if response.cookies and endpoint != "ServiceModel/AuthService.svc/Login":
        api_instance.session.cookies.update(response.cookies)  # type: ignore
        store_session_cookie(api_instance, api_instance.username)
        logger.debug("New cookies stored in the session.")

    api_instance.api_calls += 1

    return response
