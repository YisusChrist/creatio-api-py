"""Tests for the Request handler module."""

import pytest
from pydantic import HttpUrl

from creatio_api_py import CreatioODataAPI
from creatio_api_py.api import request_handler


creatio_url = "https://davissamac.creatio.com"


@pytest.fixture
def api() -> CreatioODataAPI:
    base_url = HttpUrl(creatio_url)
    # Initialize the CreatioODataAPI instance with a custom base URL
    api = CreatioODataAPI(base_url=base_url)
    api.authenticate()
    return api


def test_make_request(api: CreatioODataAPI) -> None:
    # Test the make_request method
    response: request_handler.Response = request_handler.make_request(
        api, "GET", "/0/odata/AcademyURL"
    )
    assert response.status_code == 200  # Assuming the request is successful
