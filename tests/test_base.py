"""Tests for the CreatioODataAPI class."""

import pytest
from pydantic import HttpUrl

from creatio_api_py import CreatioODataAPI


creatio_url = "https://davissamac.creatio.com"


@pytest.fixture
def api() -> CreatioODataAPI:
    base_url = HttpUrl(creatio_url)
    # Initialize the CreatioODataAPI instance with a custom base URL
    api = CreatioODataAPI(base_url=base_url)
    api.authenticate()
    return api


def test_init_failure() -> None:
    # Test the __init__ method with a missing base URL
    with pytest.raises(ValueError):
        CreatioODataAPI(base_url="")


def test_init(api: CreatioODataAPI) -> None:
    # Test the __init__ method
    assert api.base_url == HttpUrl(creatio_url)


def test_number_of_api_calls(api: CreatioODataAPI) -> None:
    # Test the number of API calls
    assert api.api_calls == 1
