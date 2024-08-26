"""
@file     creatio-odata.py
@license  GNU General Public License v3.0
@author   Alejandro Gonzalez Momblan (alejandro.gonzalez.momblan@evoluciona.es)
@desc     This script is used to test the OData API of Creatio.
"""

import json
import logging
import os
import sys
from contextlib import suppress
from functools import lru_cache
from typing import Any
from typing import Optional

import requests  # pip install requests
from dotenv import load_dotenv  # pip install python-dotenv
from requests_pprint import print_response_summary  # pip install requests-pprint

from .logs import logger
from .utils import print_exception


DEBUG = False
if DEBUG:
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but
    # without DATA. The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client

    http_client.HTTPConnection.debuglevel = 1
    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class CreatioODataAPI:
    """A class to interact with the Creatio OData API."""

    def __init__(self, base_url: str):
        if not base_url:
            raise ValueError("base_url is required")
        self.__base_url: str = base_url
        self.__session = requests.session()  # Create a session object
        self.__api_calls = 0  # Initialize the API calls counter

    @property
    def api_calls(self) -> int:
        """Property to get the number of API calls performed."""
        return self.__api_calls

    @property
    def base_url(self) -> str:
        """Property to get the base URL of the OData service."""
        return self.__base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        """Property to set the base URL of the OData service."""
        self.__base_url = value

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
            data (dict): The request data (for POST and PATCH requests).
            params (dict): Query parameters for the request.

        Returns:
            requests.models.Response: The response from the HTTP request.
        """
        url: str = f"{self.__base_url}{endpoint}"

        headers: dict[str, str] = {
            "Accept": "application/json; odata=verbose",
            "Content-Type": "application/json",
            "ForceUseSession": "true",
        }

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

        if DEBUG:
            print_response_summary(response)

        self.__api_calls += 1  # Increment the API calls counter

        return response

    @lru_cache()
    def _load_env(self) -> None:
        """Load the environment variables from the .env file."""
        env_vars_loaded = load_dotenv()
        if env_vars_loaded:
            logger.info("Environment variables loaded successfully")
        else:
            logger.warning("Environment variables could not be loaded")
            sys.exit(1)

    def authenticate(
        self, username: Optional[str] = "", password: Optional[str] = ""
    ) -> requests.models.Response:
        """
        Authenticate and get a cookie.

        Args:
            username (str): The username to authenticate with.
            password (str): The password to authenticate with.

        Returns:
            requests.models.Response: The response from the authentication request.
        """
        if not username and not password:
            self._load_env()
            username = os.getenv("CREATIO_USERNAME") or ""
            password = os.getenv("CREATIO_PASSWORD") or ""
        if not username or not password:
            logger.error("Username or password empty")
            sys.exit(1)

        data: dict[str, str] = {
            "UserName": username,
            "UserPassword": password,
        }

        response: requests.Response = self._make_request(
            "POST", "/ServiceModel/AuthService.svc/Login", data=data
        )
        if response.json().get("Exception"):
            logger.error("Authentication failed")
            raise Exception("Authentication failed", response.json())

        # Extract the cookie from the response
        if response:
            self.__session.cookies.update(response.cookies)

        return response

    def get_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        params: Optional[dict[str, Any]] = None,
        record_id: Optional[str] = None,
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#48a0da23-68ff-4030-89c3-be0e8c634d14

        Get the specified collection data.

        Args:
            collection (str): The collection to get.
            params (dict): Query parameters for the request.
            record_id (str): The ID of the record to get.

        Returns:
            requests.models.Response: The response from the case list request.

        Examples:
            Get object collection instances:
            >>> response = get_collection_data("Collection1")
            Get an object collection instance by Id:
            >>> response = get_collection_data("Collection1", record_id="IdValue")
            Get an object collection instance by Id of another object collection:
            >>> response = get_collection_data("Collection1(Id)/Collection2")
            Get a field value of an object collection instance by Id via the $value parameter:
            >>> response = get_collection_data("Collection1(Id)/Field1/$value")
            Get the number of instances in an object collection via the $count parameter:
            >>> response = get_collection_data("Collection1", params={"$count": "true"})
            Get the number of skipped object collection instances via the $skip parameter:
            >>> response = get_collection_data("Collection1", params={"$skip": "Value"})
            Get a set number of object collection instances via the $top parameter:
            >>> response = get_collection_data("Collection1", params={"$top": "Value"})
            Get specific fields from object collection instances via the $select parameter:
            >>> response = get_collection_data("Collection1", params={"$select": "Field1,Field2"})
            Get an object collection instance by instance Id of another object collection via the $expand parameter:
            >>> response = get_collection_data("Collection1(Id)", params={"$expand": "Collection2"})
        """
        url = f"/0/odata/{collection}"

        if record_id:
            url += f"({record_id})"

        return self._make_request("GET", url, params=params)

    def add_collection_data(  # pylint: disable=line-too-long
        self,
        collection: str,
        data: dict[str, Any],
    ) -> requests.models.Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#837e4578-4a8c-4637-97d4-657079f12fe0

        Add a new record in the specified collection.

        Args:
            collection (str): The collection to insert in.
            data (dict): The data to insert.

        Returns:
            requests.models.Response: The response from the case list request.

        Examples:
            Insert a new record in the specified collection:
            >>> response = add_collection_data("Collection1", data={"Field1": "Value1", "Field2": "Value2"})
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

        Args:
            collection (str): The collection to modify.
            record_id (str): The ID of the record to modify.
            data (dict): The data to update.

        Returns:
            requests.models.Response: The response from the case list request.

        Examples:
            Modify a record in the specified collection:
            >>> response = modify_collection_data("Collection1", record_id="IdValue", data={"Field1": "Value1", "Field2": "Value2"})
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

        Args:
            collection (str): The collection to delete from.
            record_id (str): The ID of the record to delete.

        Returns:
            requests.models.Response: The response from the case list request.

        Examples:
            Delete a record in the specified collection:
            >>> response = delete_collection_data("Collection1", id="IdValue")
        """
        return self._make_request("DELETE", f"/0/odata/{collection}({record_id})")
