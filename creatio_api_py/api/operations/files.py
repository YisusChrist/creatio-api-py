import mimetypes
from pathlib import Path
from typing import Any

from requests.exceptions import RequestException
from requests.models import Response

from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import log_and_print
from creatio_api_py.utils import parse_content_disposition


class FileOperationsMixin:
    """
    Mixin class for file operations in Creatio API.
    Provides methods to download and upload files.
    """

    def download_file(
        self: CreatioAPIInterface,
        collection: str,
        file_id: str,
        path: str | Path = Path.cwd(),
    ) -> Response:
        """
        Download a file from Creatio.

        Args:
            collection (str): The collection containing the file.
            file_id (str): The ID of the file to download.
            path (str | Path): The path to save the downloaded file. Defaults to the
                current directory.

        Returns:
            Response: The response from the file download request.
        """
        response: Response = make_request(  # type: ignore[no-untyped-call]
            self, "GET", f"0/rest/FileService/Download/{collection}/{file_id}"
        )

        # Get the file name from the response headers
        content_disposition: str = response.headers.get("Content-Disposition", "")
        file_name: str | None = parse_content_disposition(content_disposition)
        if not file_name:
            raise ValueError(
                "Could not determine the file name from the response headers"
            )

        final_path: Path = path if isinstance(path, Path) else Path(path)
        with open(final_path / file_name, "wb") as f:
            f.write(response.content)

        return response

    def upload_file(
        self: CreatioAPIInterface,
        collection: str,
        entity_id: str,
        file_path: str | Path,
    ) -> Response:
        """
        Upload a file to Creatio.

        Args:
            collection (str): The collection to upload the file to.
            entity_id (str): The ID of the entity to associate the file with.
            file_path (str | Path): The path to the file to upload.

        Raises:
            ValueError: If the file ID cannot be determined from the response.
            RequestException: If the file upload request fails.

        Returns:
            Response: The response from the file upload request.
        """
        # Read the file data to ensure the file is valid
        file_path = file_path if isinstance(file_path, Path) else Path(file_path)
        with open(file_path, "rb") as f:
            data: bytes = f.read()

        file_length: int = len(data)
        parent_collection: str = collection[: -len("File")]

        # Create the file in the collection table
        payload: dict[str, Any] = {
            "Name": file_path.name,
            f"{parent_collection}Id": entity_id,
            "Size": file_length,
            "TotalSize": file_length,
            "TypeId": "529bc2f8-0ee0-df11-971b-001d60e938c6",
        }
        response: Response = self.add_collection_data(collection, data=payload)

        # Get the file ID from the response
        file_id: str = response.json().get("Id")
        if not file_id:
            raise ValueError("Could not determine the file ID from the response")

        mime_type: str | None = mimetypes.guess_type(file_path)[0]
        params: dict[str, str | int | None] = {
            "fileId": file_id,
            "totalFileLength": file_length,
            "mimeType": mime_type,
            "fileName": file_path.name,
            "columnName": "Data",
            "entitySchemaName": collection,
            "parentColumnName": parent_collection,
            "parentColumnValue": entity_id,
        }

        headers: dict[str, str] = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f"attachment; filename={file_path.name}",
            "Content-Range": f"bytes 0-{file_length - 1}/{file_length}",
        }

        try:
            response = make_request(  # type: ignore[no-untyped-call]
                self,
                "POST",
                f"0/rest/FileApiService/UploadFile",
                headers=headers,
                params=params,
                data=data,
            )
        except RequestException as e:
            if e.response is not None:
                message: str = e.response.json().get("error", "")
                log_and_print(message, e, self.debug)
            # Delete the file record if the upload fails
            self.delete_collection_data(collection, file_id)
            raise

        return response
