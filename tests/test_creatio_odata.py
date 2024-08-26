"""Tests for the CreatioODataAPI class."""

import pytest
import requests

from creatio_api_py import CreatioODataAPI


record_id: str = ""


@pytest.fixture
def api() -> CreatioODataAPI:
    base_url = "https://davissamac.creatio.com"
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
    assert api.base_url == "https://davissamac.creatio.com"


def test_number_of_api_calls(api: CreatioODataAPI) -> None:
    # Test the number of API calls
    assert api.api_calls == 1


def test_make_request(api: CreatioODataAPI) -> None:
    # Test the make_request method
    response = api._make_request("GET", "/0/odata/AcademyURL")
    assert response.status_code == 200


def test_authentication(api: CreatioODataAPI) -> None:
    # Test the authentication method
    response = api.authenticate()
    assert response.status_code == 200


def test_authentication_failure(api: CreatioODataAPI) -> None:
    with pytest.raises(requests.exceptions.SSLError) as e:
        # Test the authentication method with invalid credentials
        api.base_url = "https://invalid_url.creatio.com"
        api.authenticate()

    assert "HTTPSConnectionPool(host=\\'invalid_url.creatio.com\\', port=443)" in str(e)


def test_get_collection_data(api: CreatioODataAPI) -> None:
    # Test the get_collection_data method
    response = api.get_collection_data("Case")
    assert response.status_code == 200


def test_create_record(api: CreatioODataAPI) -> None:
    global record_id
    # Test the add_collection_data method
    data: dict[str, str] = {
        "UsrEmail": "test@test.com",
        "UsrTelefono": "123456789",
        "UsrDescripcionBienContratado": "Test",
    }
    response = api.add_collection_data("Case", data)
    assert response.status_code == 201

    # Retrieve the ID of the newly created record from the response JSON
    response_json = response.json()
    assert "Id" in response_json

    record_id = response_json["Id"]


def test_modify_collection_data(api: CreatioODataAPI) -> None:
    global record_id
    # Test the modify_collection_data method
    data: dict[str, str] = {"UsrEmail": "new_email@test.com"}
    response = api.modify_collection_data(
        collection="Case", record_id=record_id, data=data
    )
    assert response.status_code == 204


def test_delete_collection_data(api: CreatioODataAPI) -> None:
    global record_id
    # Test the delete_collection_data method
    response = api.delete_collection_data(collection="Case", record_id=record_id)
    if response.status_code == 500:
        assert (
            'update or delete on table "Case" violates foreign key constraint'
            in response.json()["error"]["innererror"]["message"]
        )
    else:
        assert response.status_code == 204
