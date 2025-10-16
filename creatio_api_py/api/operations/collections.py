from typing import Any
from typing import Optional

from requests.models import Response

from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface


class CollectionOperationsMixin:
    """
    Mixin class for collection operations in Creatio API.

    Provides methods to get, add, modify, and delete records in collections.
    This class is designed to be used with a CreatioAPIInterface instance.
    """

    def get_collection_data(  # pylint: disable=line-too-long
        self: CreatioAPIInterface,
        collection: str,
        params: Optional[dict[str, str | int]] = None,
        record_id: Optional[str] = None,
        only_count: Optional[bool] = None,
        count: Optional[bool] = None,
        skip: Optional[int] = None,
        top: Optional[int] = None,
        select: Optional[str | list[str]] = None,
        expand: Optional[str | list[str]] = None,
        value: Optional[str] = None,
        order_by: Optional[str] = None,
        filter: Optional[str] = None,
        property: Optional[str] = None,
    ) -> Response:
        """
        Reference: https://documenter.getpostman.com/view/10204500/SztHX5Qb?version=latest#48a0da23-68ff-4030-89c3-be0e8c634d14

        Get the specified collection data.

        Examples:
            Fetch all items in a collection:
            >>> response = get_collection_data("Collection1")
            Fetch a specific record by ID:
            >>> response = get_collection_data("Collection1", record_id="123")
            Retrieve only the count of items in a collection:
            >>> response = get_collection_data("Collection1", only_count=True)
            Retrieve the total count of matching items along with the data:
            >>> response = get_collection_data("Collection1", count=True)
            Fetch a subset of items, skipping the first 10:
            >>> response = get_collection_data("Collection1", skip=10, top=5)
            Select specific fields:
            >>> response = get_collection_data("Collection1", select=["Field1", "Field2"])
            >>> response = get_collection_data("Collection1", select="Field1,Field2")
            Expand related entities:
            >>> response = get_collection_data("Collection1", expand="RelatedCollection")
            Retrieve the value of a specific field:
            >>> response = get_collection_data("Collection1", record_id="123", value="Field1")
            Apply ordering and filtering:
            >>> response = get_collection_data("Collection1", order_by="Field1 desc", filter="Field2 eq 'Value'")
            Retrieve the value of a specific property:
            >>> response = get_collection_data("Collection1", record_id="123", property="Field1")

        Args:
            collection (str): The name of the collection to query.
            params (dict[str, Any], optional): Additional query parameters. Use
                with caution as it overrides explicit arguments.
            record_id (str, optional): The ID of a specific record to retrieve.
            only_count (bool, optional): Retrieve only the count of items.
            count (bool, optional): Include the total count of matching items
                in the response (`$count`).
            skip (int, optional): Skip the specified number of items (`$skip`).
            top (int, optional): Limit the number of items returned (`$top`).
            select (str | list[str], optional): Specify the fields to include
                in the response (`$select`).
            expand (str | list[str], optional): Include related entities in the
                response (`$expand`).
            value (str, optional): Retrieve the value of a specific field
                using the `$value` keyword.
            order_by (str, optional): Define the order of items in the response
                (`$orderby`).
            filter (str, optional): Apply a filter to the items in the response
                (`$filter`).
            property (str, optional): Retrieve the value of a specific property
                of a record. Specially useful if you are requesting for binary
                data stored under /Data suffix fields.

        Returns:
            requests.models.Response: The HTTP response object containing the requested
                data.
        """
        url: str = f"0/odata/{collection}"

        if record_id:
            url += f"({record_id})"
        if value:
            url += f"/{value}/$value"
        if property:
            url += f"/{property}"
        elif only_count:
            url += "/$count"

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

        return make_request(self, "GET", url, params=params)

    def add_collection_data(  # pylint: disable=line-too-long
        self: CreatioAPIInterface, collection: str, data: dict[str, Any]
    ) -> Response:
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
        return make_request(self, "POST", f"0/odata/{collection}", json=data)

    def modify_collection_data(  # pylint: disable=line-too-long
        self: CreatioAPIInterface,
        collection: str,
        record_id: str,
        data: dict[str, Any],
    ) -> Response:
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
        return make_request(
            self, "PATCH", f"0/odata/{collection}({record_id})", json=data
        )

    def delete_collection_data(  # pylint: disable=line-too-long
        self: CreatioAPIInterface, collection: str, record_id: str
    ) -> Response:
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
        return make_request(self, "DELETE", f"0/odata/{collection}({record_id})")
