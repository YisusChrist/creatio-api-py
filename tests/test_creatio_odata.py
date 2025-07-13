"""Tests for the CreatioODataAPI class."""

import pytest
import requests
from pydantic import HttpUrl

from creatio_api_py import CreatioODataAPI


creatio_url = "https://davissamac.creatio.com"
main_collection = "Case"
record_id: str = ""


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


def test_make_request(api: CreatioODataAPI) -> None:
    # Test the make_request method
    with pytest.raises(AttributeError) as e:
        api._make_request("GET", "/0/odata/AcademyURL")
    assert "object has no attribute '_make_request'" in str(e.value)


def test_authentication_no_cache(api: CreatioODataAPI) -> None:
    # Test the authentication method
    response = api.authenticate(cache=False)
    assert response.status_code == 200  # Assuming the authentication is successful


def test_authentication_cache(api: CreatioODataAPI) -> None:
    # Test the authentication method
    response = api.authenticate(cache=True)
    assert response.status_code == None  # No response expected when using cache


def test_authentication_failure(api: CreatioODataAPI) -> None:
    with pytest.raises(requests.exceptions.SSLError) as e:
        # Test the authentication method with invalid credentials
        api.base_url = HttpUrl("https://invalid_url.creatio.com")
        api.authenticate()

    assert "host=\\'invalid_url.creatio.com\\', port=443)" in str(e)


def test_get_collection_error_wrong_collection(api: CreatioODataAPI) -> None:
    # Test to retrieve a collection that does not exist
    collection = "InvalidCollection"
    with pytest.raises(requests.exceptions.HTTPError) as e:
        api.get_collection_data("InvalidCollection")
    assert (
        f"401 Client Error: Unauthorized for url: {creatio_url}/0/odata/{collection}"
        in str(e.value)
    )


def test_get_collection_error_over_20k(api: CreatioODataAPI) -> None:
    # Test to retrieve a collection with more than 20,000 records
    with pytest.raises(requests.exceptions.HTTPError) as e:
        api.get_collection_data(main_collection)
    assert (
        f"500 Server Error: Internal Server Error for url: {creatio_url}/0/odata/{main_collection}"
        in str(e.value)
    )


def test_get_collection_data(api: CreatioODataAPI) -> None:
    # Test to retrieve one record from an existing collection
    response = api.get_collection_data(main_collection, top=1)
    assert response.status_code == 200


def test_create_record(api: CreatioODataAPI) -> None:
    global record_id

    # Test the add_collection_data method
    data: dict[str, str] = {
        "UsrEmail": "test@test.com",
        "UsrTelefono": "123456789",
        "UsrDescripcionBienContratado": "Test",
    }
    response = api.add_collection_data(main_collection, data)
    assert response.status_code == 201

    # Retrieve the ID of the newly created record from the response JSON
    response_json = response.json()
    assert "Id" in response_json

    record_id = response_json["Id"]


def test_modify_collection_data(api: CreatioODataAPI) -> None:
    # Test the modify_collection_data method
    data: dict[str, str] = {"UsrEmail": "new_email@test.com"}
    response = api.modify_collection_data(
        collection=main_collection, record_id=record_id, data=data
    )
    assert response.status_code == 204


def test_delete_collection_data(api: CreatioODataAPI) -> None:
    # Test the delete_collection_data method
    with pytest.raises(requests.exceptions.HTTPError) as e:
        api.delete_collection_data(collection=main_collection, record_id=record_id)
        assert (
            f'update or delete on table "{main_collection}" violates foreign key constraint'
            in str(e.value)
        )
