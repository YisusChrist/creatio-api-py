import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from requests.models import Response

from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import parse_content_disposition


def deep_unescape(obj):
    """
    Recursively walks a structure and:
    - If a value is a string that contains valid JSON -> json.loads()
    - Repeats until everything is real Python objects
    """
    if isinstance(obj, dict):
        return {k: deep_unescape(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_unescape(v) for v in obj]
    elif isinstance(obj, str):
        s = obj.strip()

        # Heuristic: only try JSON if it looks like JSON
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):
            try:
                parsed = json.loads(s)
                # Recursively process the parsed JSON too
                return deep_unescape(parsed)
            except json.JSONDecodeError:
                return obj
        return obj

    else:
        return obj


def _parse_to_esq(dashboard_config: dict) -> dict:
    """Convert dashboard configuration to ESQ format."""
    esq_payload = {
        "esqSerialized": {
            "rootSchemaName": dashboard_config["entitySchemaName"],
            "operationType": 0,
            "includeProcessExecutionData": True,
            "filters": {
                "items": {},
                "logicalOperation": dashboard_config["filterData"]["logicalOperation"],
                "isEnabled": dashboard_config["filterData"]["isEnabled"],
                "filterType": dashboard_config["filterData"]["filterType"],
                "rootSchemaName": dashboard_config["filterData"]["rootSchemaName"],
            },
            "columns": {"items": {}},
            "isDistinct": False,
            "rowCount": -1,
            "rowsOffset": -1,
            "isPageable": False,
            "allColumns": False,
            "useLocalization": True,
            "useRecordDeactivation": False,
            "serverESQCacheParameters": {
                "cacheLevel": 0,
                "cacheGroup": "",
                "cacheItemName": "",
            },
            "queryOptimize": False,
            "useMetrics": False,
            "adminUnitRoleSources": 0,
            "querySource": 0,
            "ignoreDisplayValues": False,
            "isHierarchical": False,
        },
    }

    filters = {}
    for key, filter_item in dashboard_config["filterData"]["items"].items():
        if not filter_item["isEnabled"]:
            continue

        filters[key] = {
            "filterType": filter_item["filterType"],
            "comparisonType": filter_item["comparisonType"],
            "isEnabled": filter_item["isEnabled"],
            "trimDateTimeParameterToDate": filter_item["trimDateTimeParameterToDate"],
            "leftExpression": {
                "expressionType": filter_item["leftExpression"]["expressionType"],
                "columnPath": filter_item["leftExpression"]["columnPath"],
            },
            "rightExpressions": [],
        }

        for right_expr in filter_item["rightExpressions"]:
            filters[key]["rightExpressions"].append(
                {
                    "expressionType": right_expr["expressionType"],
                    "parameter": {
                        "dataValueType": right_expr["parameter"]["dataValueType"],
                        "value": right_expr["parameter"]["value"]["value"],
                    },
                }
            )

    if dashboard_config["entitySchemaName"] == "Case":
        esq_payload["esqSerialized"]["filters"] = {
            "items": {
                "0a0c11a3-1453-4a49-a06f-3536eef413e0": {
                    "items": {
                        "6f3c4586-90d0-4db5-8819-31029d341d38": {
                            "items": {},
                            "logicalOperation": 0,
                            "isEnabled": True,
                            "filterType": 6,
                            "rootSchemaName": "Case",
                        },
                        "2dec8579-a7d5-49f0-a99b-1f2b8e0f9fbb": {
                            "items": {
                                "FixedFilters": {
                                    "items": {},
                                    "logicalOperation": 0,
                                    "isEnabled": True,
                                    "filterType": 6,
                                },
                                "TagFilters": {
                                    "items": {},
                                    "logicalOperation": 0,
                                    "isEnabled": True,
                                    "filterType": 6,
                                },
                                "FolderFilters": {
                                    "items": {},
                                    "logicalOperation": 1,
                                    "isEnabled": True,
                                    "filterType": 6,
                                },
                                "FilterStatus": {
                                    "filterType": 1,
                                    "comparisonType": 3,
                                    "isEnabled": True,
                                    "trimDateTimeParameterToDate": False,
                                    "leftExpression": {
                                        "expressionType": 0,
                                        "columnPath": "[Case:Id:Id].Status.IsFinal",
                                    },
                                    "rightExpression": {
                                        "expressionType": 2,
                                        "parameter": {
                                            "dataValueType": 1,
                                            "value": False,
                                        },
                                    },
                                },
                            },
                            "logicalOperation": 0,
                            "isEnabled": True,
                            "filterType": 6,
                        },
                    },
                    "logicalOperation": 0,
                    "isEnabled": True,
                    "filterType": 6,
                }
            },
            "logicalOperation": 0,
            "isEnabled": True,
            "filterType": 6,
        }

        esq_payload["esqSerialized"]["filters"]["items"][
            "0a0c11a3-1453-4a49-a06f-3536eef413e0"
        ]["items"]["6f3c4586-90d0-4db5-8819-31029d341d38"]["items"] = filters
    else:
        esq_payload["esqSerialized"]["filters"]["items"] = filters

    columns = {}
    for column in dashboard_config["gridConfig"]["items"]:
        column_name = column["metaPath"]
        columns_config = {
            "caption": column["caption"],
            "orderDirection": 0,
            "orderPosition": -1,
            "isVisible": True,
            "expression": {
                "expressionType": 0,
                "columnPath": column_name,
            },
        }
        if "orderDirection" in column:
            columns_config["orderDirection"] = column["orderDirection"]
            columns_config["orderPosition"] = column["orderPosition"]

        columns[column_name] = columns_config

    esq_payload["esqSerialized"]["columns"]["items"] = columns

    return esq_payload


class DashboardOperationsMixin:
    """
    Mixin class for file operations in Creatio API.
    Provides methods to download and upload files.
    """

    def export_dashboard(
        self: CreatioAPIInterface,
        dashboard_id: str,
        dashboard_name: str,
        path: str | Path = Path.cwd(),
    ) -> Response:
        """
        Export a dashboard from Creatio.

        Args:
            dashboard_id (str): The ID of the dashboard to export.

        Returns:
            Response: The response from the dashboard export request.
        """
        dashboard_config = json.loads(
            self.get_collection_data(
                "SysDashboard", record_id=dashboard_id, value="Items"
            ).content.decode("utf-8-sig")
        ).get(dashboard_name)
        if not dashboard_config:
            raise ValueError(f"Dashboard with ID {dashboard_id} not found.")

        dashboard_config: dict = dashboard_config["parameters"]
        dashboard_config = deep_unescape(dashboard_config)

        now = datetime.now().strftime("%d_%m_%Y_%H_%M")
        file_name = f"{dashboard_config['caption'].lower().replace(' ', '_')}_{now}"

        esq = _parse_to_esq(dashboard_config)

        # encode payload json to str
        esq_serialized = json.dumps(esq["esqSerialized"], separators=(",", ":"))
        payload = {"esqSerialized": esq_serialized}

        export_key = make_request(
            self,
            "POST",
            "0/rest/ReportService/GetExportToExcelKey",
            json=payload,
        ).json()["GetExportToExcelKeyResult"]["key"]
        if not export_key:
            raise ValueError("Could not obtain export key for dashboard export.")

        response: Response = make_request(
            self,
            "GET",
            f"0/rest/ReportService/GetExportToExcelData/{export_key}/{file_name}",
        )

        # Get the file name from the response headers
        content_disposition: str = response.headers.get("Content-Disposition", "")
        file_name: str | None = parse_content_disposition(content_disposition)
        if not file_name:
            raise ValueError(
                "Could not determine the file name from the response headers"
            )

        # URL decode
        file_name = unquote(file_name)

        final_path: Path = path if isinstance(path, Path) else Path(path)
        with open(final_path / file_name, "wb") as f:
            f.write(response.content)

        return response
