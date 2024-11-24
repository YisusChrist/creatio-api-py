"""
@file     creatio-odata.py
@license  GNU General Public License v3.0
@author   Alejandro Gonzalez Momblan (alejandro.gonzalez.momblan@evoluciona.es)
@desc     This script is used to test the OData API of Creatio.
"""

import json
import os
from contextlib import suppress
from typing import Any
from typing import Optional

import requests
import requests_cache
from dotenv import load_dotenv
from pydantic import Field
from pydantic import HttpUrl
from pydantic.dataclasses import dataclass
from requests_pprint import print_response_summary

from creatio_api_py.logs import logger
from creatio_api_py.utils import print_exception


@dataclass(config={"arbitrary_types_allowed": True})
class CreatioODataAPI:
    """A class to interact with the Creatio OData API."""

    base_url: HttpUrl
    debug: bool = False
    cache: bool = False
    __api_calls: int = Field(default=0, init=False)
    __session: requests.Session | requests_cache.CachedSession = Field(init=False)

    def __post_init__(self) -> None:
        """Initialize the session based on the cache setting."""
        if self.cache:
            cached_backend = requests_cache.SQLiteCache(
                db_path="creatio_cache", use_cache_dir=True
            )
            self.__session = requests_cache.CachedSession(
                backend=cached_backend, expire_after=3600
            )
            if self.debug:
                logger.debug("Using requests-cache for session.")
        else:
            self.__session = requests.Session()
            if self.debug:
                logger.debug("Using standard requests session.")

    @property
    def api_calls(self) -> int:
        """Property to get the number of API calls performed."""
        return self.__api_calls

    @property
    def session_cookies(self) -> dict[str, Any]:
        """Property to get the session cookies."""
        result: dict[str, Any] = self.__session.cookies.get_dict()
        return result

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> requests.models.Response:
        """
        Make a generic HTTP request to the OData service.

        Args:
            method (str): HTTP method (GET, POST, PATCH, etc.).
            endpoint (str): The API endpoint to request.
            data (Optional[dict[str, Any]], optional): The request data (for POST
                and PATCH requests).
            params (Optional[dict[str, Any]], optional): Query parameters for the request.

        Returns:
            requests.models.Response: The response from the HTTP request.
        """
        url: str = f"{self.base_url}{endpoint}"

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "ForceUseSession": "true",
        }

        if "$metadata" not in endpoint:
            headers["Accept"] = "application/json; odata=verbose"
        if method == "PUT":
            headers["Content-Type"] = "application/octet-stream"

        with suppress(Exception):
            # Add the BPMCSRF cookie to the headers
            headers["BPMCSRF"] = self.__session.cookies.get_dict()["BPMCSRF"]

        payload = json.dumps(data) if data else None

        try:
            response: requests.Response = self.__session.request(
                method, url, headers=headers, data=payload, params=params
            )
        except requests.exceptions.RequestException as e:
            print_exception(e)
            raise

        if self.debug:
            print_response_summary(response)

        self.__api_calls += 1  # Increment the API calls counter

        return response

    def _load_env(self) -> None:
        """Load the environment variables from the .env file."""
        env_vars_loaded: bool = load_dotenv()
        if env_vars_loaded:
            logger.info("Environment variables loaded successfully")
        else:
            logger.warning("Environment variables could not be loaded")

    def authenticate(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> requests.models.Response:
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
        if not username and not password:
            self._load_env()
            username = os.getenv("CREATIO_USERNAME", "")
            password = os.getenv("CREATIO_PASSWORD", "")
        if not username or not password:
            logger.error("Username or password empty")
            raise ValueError("Username or password empty")

        data: dict[str, str] = {
            "UserName": username,
            "UserPassword": password,
        }

        response: requests.Response = self._make_request(
            "POST", "/ServiceModel/AuthService.svc/Login", data=data
        )
        if response.json().get("Exception"):
            logger.error("Authentication failed")
            raise ValueError("Authentication failed", response.json())

        # Extract the cookie from the response
        if response:
            self.__session.cookies.update(response.cookies)

        return response

    def get_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        params: Optional[dict[str, str | int]] = None,
        record_id: Optional[str] = None,
        count: Optional[bool] = None,
        skip: Optional[int] = None,
        top: Optional[int] = None,
        select: Optional[str | list[str]] = None,
        expand: Optional[str | list[str]] = None,
        value: Optional[str] = None,
        order_by: Optional[str] = None,
        filter: Optional[str] = None,
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#48a0da23-68ff-4030-89c3-be0e8c634d14

        Get the specified collection data.

        Examples:
            Fetch all items in a collection:
            >>> response = get_collection_data("Collection1")
            Fetch a specific record by ID:
            >>> response = get_collection_data("Collection1", record_id="123")
            Fetch a subset of items, skipping the first 10:
            >>> response = get_collection_data("Collection1", skip=10, top=5)
            Select specific fields:
            >>> response = get_collection_data("Collection1", select=["Field1", "Field2"])
            Expand related entities:
            >>> response = get_collection_data("Collection1", expand="RelatedCollection")
            Retrieve the value of a specific field:
            >>> response = get_collection_data("Collection1", record_id="123", value="Field1")
            Apply ordering and filtering:
            >>> response = get_collection_data("Collection1", order_by="Field1 desc", filter="Field2 eq 'Value'")

        Args:
            collection (str): The name of the collection to query.
            record_id (Optional[str], optional): The ID of a specific record to retrieve.
            count (Optional[bool], optional): Include the total count of matching items
                in the response (`$count`).
            skip (Optional[int], optional): Skip the specified number of items (`$skip`).
            top (Optional[int], optional): Limit the number of items returned (`$top`).
            select (Optional[str | list[str]], optional): Specify the fields to include
                in the response (`$select`).
            expand (Optional[str | list[str]], optional): Include related entities in the
                response (`$expand`).
            value (Optional[str], optional): Retrieve the value of a specific field
                using the `$value` keyword.
            order_by (Optional[str], optional): Define the order of items in the response
                (`$orderby`).
            filter (Optional[str], optional): Apply a filter to the items in the response
                (`$filter`).
            params (Optional[dict[str, Any]], optional): Additional query parameters. Use
                with caution as it overrides explicit arguments.

        Returns:
            requests.models.Response: The HTTP response object containing the requested
                data.
        """
        url: str = f"/0/odata/{collection}"

        if record_id:
            url += f"({record_id})"

        if value:
            url += f"/{value}/$value"

        # Build query parameters
        if not params:
            params = {}
        if count is not None:
            params["$count"] = str(count).lower()
        if skip is not None:
            params["$skip"] = skip
        if top is not None:
            params["$top"] = top
        if select:
            params["$select"] = ",".join(select) if isinstance(select, list) else select
        if expand:
            params["$expand"] = ",".join(expand) if isinstance(expand, list) else expand
        if order_by:
            params["$orderby"] = order_by
        if filter:
            params["$filter"] = filter

        return self._make_request("GET", url, params=params)

    def add_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        data: dict[str, Any],
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#837e4578-4a8c-4637-97d4-657079f12fe0

        Add a new record in the specified collection.

        Examples:
            Insert a new record in the specified collection:
            >>> response = add_collection_data("Collection1", data={"Field1": "Value1", "Field2": "Value2"})

        Args:
            collection (str): The collection to insert in.
            data (dict[str, Any]): The data to insert.

        Returns:
            requests.models.Response: The response from the case list request.
        """
        return self._make_request("POST", f"/0/odata/{collection}", data=data)

    def modify_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        record_id: str,
        data: dict[str, Any],
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#da518295-e1c8-4114-9f03-f5f236174986

        Modify a record in the specified collection.

        Examples:
            Modify a record in the specified collection:
            >>> response = modify_collection_data("Collection1", record_id="IdValue", data={"Field1": "Value1", "Field2": "Value2"})

        Args:
            collection (str): The collection to modify.
            record_id (str): The ID of the record to modify.
            data (dict[str, Any]): The data to update.

        Returns:
            requests.models.Response: The response from the case list request.
        """
        return self._make_request(
            "PATCH", f"/0/odata/{collection}({record_id})", data=data
        )

    def delete_collection_data(  # pylint: disable=line-too-long
        self, collection: str, record_id: str
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#364435a7-12ef-4924-83cf-ed9e74c23439
        Delete a record in the specified collection.

        Examples:
            Delete a record in the specified collection:
            >>> response = delete_collection_data("Collection1", id="IdValue")

        Args:
            collection (str): The collection to delete from.
            record_id (str): The ID of the record to delete.

        Returns:
            requests.models.Response: The response from the case list request.
        """
        return self._make_request("DELETE", f"/0/odata/{collection}({record_id})")
