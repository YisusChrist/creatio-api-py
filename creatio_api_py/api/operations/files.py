import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from requests.exceptions import RequestException
from requests.models import Response
from rich import print

from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import parse_content_disposition


def download_file(response: Response, path: str | Path = Path.cwd()) -> Response:
    """
    Download a file from a response and save it to the specified path.

    Args:
        response (Response): The response containing the file to download.
        path (str | Path): The path to save the downloaded file. Defaults to the
            current directory.

    Raises:
        ValueError: If the file name cannot be determined from the response.

    Returns:
        Response: The response from the file download request.
    """
    # Get the file name from the response headers
    content_disposition: str = response.headers.get("Content-Disposition", "")
    file_name: str | None = parse_content_disposition(content_disposition)
    if not file_name:
        raise ValueError("Could not determine the file name from the response headers")

    # URL decode
    file_name = unquote(file_name)

    final_path: Path = path if isinstance(path, Path) else Path(path)
    with open(final_path / file_name, "wb") as f:
        f.write(response.content)

    return response


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
        response: Response = make_request(
            self, "GET", f"0/rest/FileService/Download/{collection}/{file_id}"
        )
        return download_file(response, path)

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
        file_path = file_path if isinstance(file_path, Path) else Path(file_path)

        file_length: int = file_path.stat().st_size
        if collection.endswith("File"):
            parent_collection: str = collection[: -len("File")]
        else:
            parent_collection = collection

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
            "Content-Type": mime_type or "application/octet-stream",
            "Content-Disposition": f"attachment; filename={file_path.name}",
            "Content-Range": f"bytes 0-{file_length - 1}/{file_length}",
        }

        try:
            with open(file_path, "rb") as f:
                response = make_request(
                    self,
                    "POST",
                    f"0/rest/FileApiService/UploadFile",
                    headers=headers,
                    params=params,
                    data=f,
                )
        except RequestException as e:
            # Delete the file record if the upload fails
            self.delete_collection_data(collection, file_id)
            raise

        return response

    def import_excel_file(
        self: CreatioAPIInterface,
        entity_schema_name: str,
        entity_schema_uid: str,
        file_path: str | Path,
        custom_column_mapping: dict[str, Any] | None = None,
    ) -> Response:
        """
        Import an Excel file into Creatio.

        1. POST /0/DataService/json/SyncReply/QuerySysSettings
        {
            "sysSettingsNameCollection": [
                "FileImportMaxFileSize"
            ]
        }


        2. POST /0/rest/FileImportService/SetImportObject
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6",
                "importObject": {
                    "uId": "726793ca-96ee-465d-a70c-7066a17e64d4",
                    "caption": "NPS",
                    "name": "BCNPS",
                    "isOtherObject": true
                }
            }
        }

        3. POST /0/rest/FileImportUploadFileService/SaveFile?fileapi17824776426385&importSessionId=02305146-d5db-6460-0505-93875dd4bdb6&entitySchemaUId=726793ca-96ee-465d-a70c-7066a17e64d4&entitySchemaName=FileImportParameters&isOtherObject=true&fileId=02305146-d5db-6460-0505-93875dd4bdb6&totalFileLength=15295&mimeType=application%2Fvnd.openxmlformats-officedocument.spreadsheetml.sheet&columnName=FileData&fileName=actividad_24_06_2026_13_11.xlsx&parentColumnName=Id&parentColumnValue=02305146-d5db-6460-0505-93875dd4bdb6
        [EXCEL FILE BINARY DATA]

        4. POST /0/rest/FileImportUploadFileService/CheckIsFileValid
        {
            "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6"
        }

        5. POST /0/rest/FileImportService/SetFileInfo
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6",
                "fileName": "actividad_24_06_2026_13_11.xlsx"
            }
        }

        6. GET /0/rest/FileImportService/GetColumnsMappingParameters
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6"
            }
        }

        7. POST /0/rest/FileImportService/SetColumnsMappingParameters
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6",
                "columns": [
                {
                    "destinations": [
                    {
                        "attributes": [],
                        "columnName": "Name",
                        "columnValueName": "Name",
                        "isKey": true,
                        "properties": [
                        {
                            "Key": "TypeUId",
                            "Value": "8b3f29bb-ea14-4ce5-a5c5-293a929b6ba2"
                        }
                        ],
                        "schemaUId": "16be3651-8fe2-4159-8dd0-a803d4683dd3"
                    }
                    ],
                    "findExistsRowsDBColumnName": null,
                    "index": "A",
                    "source": "Nombre y apellidos"
                },
                {
                    "destinations": [
                    {
                        "attributes": [],
                        "columnName": "DecisionRole",
                        "columnValueName": "DecisionRoleId",
                        "isKey": false,
                        "properties": [
                        {
                            "Key": "TypeUId",
                            "Value": "b295071f-7ea9-4e62-8d1a-919bf3732ff2"
                        },
                        {
                            "Key": "ReferenceSchemaUId",
                            "Value": "54aa771f-fba6-4d76-9239-bff3f00ee3e5"
                        }
                        ],
                        "schemaUId": "16be3651-8fe2-4159-8dd0-a803d4683dd3"
                    }
                    ],
                    "findExistsRowsDBColumnName": null,
                    "index": "B",
                    "source": "Rol"
                }
                ]
            }
        }

        8. POST /0/rest/FileImportValidationService/Validate
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6"
            }
        }

        9. POST /0/rest/FileImportService/Import
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6"
            }
        }

        10. POST /0/rest/FileImportService/GetImportSessionInfo
        {
            "request": {
                "importSessionId": "02305146-d5db-6460-0505-93875dd4bdb6"
            }
        }

        Response:
        {
            "GetImportSessionInfoResult": {
                "errorInfo": null,
                "success": true,
                "nextPrcElReady": false,
                "queryId": null,
                "responseStatus": null,
                "rowsAffected": -1,
                "fileName": "test-contact-import.xlsx",
                "hasLookupProcessingErrors": false,
                "importObject": {
                    "caption": "Contacto",
                    "isOtherObject": true,
                    "name": "Contact",
                    "uId": "16be3651-8fe2-4159-8dd0-a803d4683dd3"
                },
                "importTags": [
                    {
                        "displayValue": "Importación de datos 26/06/2026 15:07",
                        "type": {
                            "displayValue": "Privada",
                            "value": "8d7f6d6c-4ca5-4b43-bdd9-a5e01a582260"
                        },
                        "value": "ffdacd2a-c98a-4dd1-9ebe-a53ea7ca25b9"
                    }
                ],
                "importedRowsCount": 1,
                "notImportedRowsCount": 0,
                "processedRowsCount": 0,
                "rootSchemaName": "Contact",
                "totalRowsCount": 1
            }
        }

        Args:
            file_path (str | Path): The path to the Excel file to import.

        Raises:
            RequestException: If the file import request fails.

        Returns:
            Response: The response from the file import request.
        """
        file_path = file_path if isinstance(file_path, Path) else Path(file_path)

        # Generate a unique session ID for the import process
        session_id = str(uuid.uuid4())
        file_length: int = file_path.stat().st_size

        print(f"Starting file import for session {session_id}...")

        # 1. Check the maximum file size allowed for import
        print("Checking maximum file size allowed for import...", end=" ")

        endpoint = "/0/DataService/json/SyncReply/QuerySysSettings"
        payload = {"sysSettingsNameCollection": ["FileImportMaxFileSize"]}
        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json()
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to query system settings.")
        print(f"[green]OK[/]")

        max_file_size = result["values"]["FileImportMaxFileSize"]["value"] * 1024 * 1024
        if file_length > max_file_size:
            raise ValueError(
                f"File size {file_length} exceeds maximum allowed size of {max_file_size} bytes."
            )
        else:
            print(
                f"File size {file_length} is within the allowed limit of {max_file_size} bytes."
            )

        # 2. Set the import object using the SetImportObject endpoint
        print(f"Setting import object for entity {entity_schema_name}...", end=" ")

        endpoint = "/0/rest/FileImportService/SetImportObject"
        payload = {
            "request": {
                "importSessionId": session_id,
                "importObject": {
                    "uId": entity_schema_uid,
                    "name": entity_schema_name,
                    "isOtherObject": True,
                },
            }
        }

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to set import object.")
        print(f"[green]OK[/]")

        # 3. Upload the file using the SaveFile endpoint
        print(f"Uploading file '{file_path.name}'...", end=" ")

        mime_type: str | None = mimetypes.guess_type(file_path)[0]

        endpoint = "/0/rest/FileImportUploadFileService/SaveFile"
        params = {
            "importSessionId": session_id,
            "entitySchemaUId": entity_schema_uid,
            "entitySchemaName": "FileImportParameters",
            "isOtherObject": True,
            "fileId": session_id,
            "totalFileLength": file_length,
            "mimeType": mime_type,
            "columnName": "FileData",
            "fileName": file_path.name,
            "parentColumnName": "Id",
            "parentColumnValue": session_id,
        }
        headers: dict[str, str] = {
            "Content-Disposition": f"attachment; filename={file_path.name}",
            "Content-Range": f"bytes 0-{file_length - 1}/{file_length}",
        }

        with open(file_path, "rb") as f:
            response = make_request(
                self, "POST", endpoint, headers=headers, params=params, data=f
            )

        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to upload file.")
        print(f"[green]OK[/]")

        # 4. Check if the file is valid using the CheckIsFileValid endpoint
        print(f"Checking if file '{file_path.name}' is valid...", end=" ")

        endpoint = "/0/rest/FileImportUploadFileService/CheckIsFileValid"
        payload = {"importSessionId": session_id}

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to check if file is valid.")
        print(f"[green]OK[/]")

        # 5. Set the file info using the SetFileInfo endpoint
        print(f"Setting file info for '{file_path.name}'...", end=" ")

        endpoint = "/0/rest/FileImportService/SetFileInfo"
        payload = {
            "request": {
                "importSessionId": session_id,
                "fileName": file_path.name,
            }
        }

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to set file info.")
        print(f"[green]OK[/]")

        # 6. Get the columns mapping parameters using the GetColumnsMappingParameters endpoint
        print(f"Getting columns mapping parameters...", end=" ")

        endpoint = "/0/rest/FileImportService/GetColumnsMappingParameters"
        payload = {"request": {"importSessionId": session_id}}

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to get columns mapping parameters.")
        print(f"[green]OK[/]")

        # 7. Set the columns mapping parameters using the SetColumnsMappingParameters endpoint
        print(f"Setting columns mapping parameters...", end=" ")

        if custom_column_mapping is None:
            print(f"[yellow]SKIPPED[/]")
        else:
            endpoint = "/0/rest/FileImportService/SetColumnsMappingParameters"
            payload = {
                "request": {
                    "importSessionId": session_id,
                    "columns": custom_column_mapping,
                }
            }

            response = make_request(self, "POST", endpoint, json=payload)
            result = response.json().get(f"{endpoint.split('/')[-1]}Result")
            if not result["success"]:
                print("[red]ERROR[/]")
                raise ValueError("Failed to set columns mapping parameters.")
            print(f"[green]OK[/]")

        # 8. Validate the import using the Validate endpoint
        print(f"Validating import...", end=" ")

        endpoint = "/0/rest/FileImportValidationService/Validate"
        payload = {"request": {"importSessionId": session_id}}

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to validate import.")
        print(f"[green]OK[/]")

        # 9. Perform the import using the Import endpoint
        print(f"Performing import...", end=" ")

        endpoint = "/0/rest/FileImportService/Import"
        payload = {"request": {"importSessionId": session_id}}

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to perform import.")
        print(f"[green]OK[/]")

        # 10. Get the import session info using the GetImportSessionInfo endpoint
        print(f"Getting import session info...", end=" ")

        endpoint = "/0/rest/FileImportService/GetImportSessionInfo"
        payload = {"request": {"importSessionId": session_id}}

        response = make_request(self, "POST", endpoint, json=payload)
        result = response.json().get(f"{endpoint.split('/')[-1]}Result")
        if not result["success"]:
            print("[red]ERROR[/]")
            raise ValueError("Failed to get import session info.")
        print(f"[green]OK[/]")

        print("Result of import:")
        print(result)

        return response
