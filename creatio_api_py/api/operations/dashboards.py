import json
from datetime import datetime
from pathlib import Path

from requests.models import Response

from creatio_api_py.api.operations.files import download_file
from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface


def _deep_unescape(obj):
    """
    Recursively walks a structure and:
    - If a value is a string that contains valid JSON -> json.loads()
    - Repeats until everything is real Python objects
    """
    if isinstance(obj, dict):
        return {k: _deep_unescape(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_unescape(v) for v in obj]
    elif isinstance(obj, str):
        s = obj.strip()

        # Heuristic: only try JSON if it looks like JSON
        if (s.startswith("{") and s.endswith("}")) or (
            s.startswith("[") and s.endswith("]")
        ):
            try:
                parsed = json.loads(s)
                # Recursively process the parsed JSON too
                return _deep_unescape(parsed)
            except json.JSONDecodeError:
                return obj
        return obj

    else:
        return obj


def parse_filter_node(node: dict) -> dict:
    """
    Parses a Terrasoft filter node (FilterGroup or leaf filter)
    into an ESQ-compatible structure.
    """
    if not node.get("isEnabled", True):
        return None

    filter_type = node.get("filterType")

    # FilterGroup (recursive)
    if filter_type == 6:
        parsed = {
            "items": {},
            "logicalOperation": node.get("logicalOperation", 0),
            "isEnabled": node.get("isEnabled", True),
            "filterType": 6,
        }

        if "rootSchemaName" in node:
            parsed["rootSchemaName"] = node["rootSchemaName"]

        for key, child in node.get("items", {}).items():
            parsed_child = parse_filter_node(child)
            if parsed_child is not None:
                parsed["items"][key] = parsed_child

        return parsed if parsed["items"] else None

    # InFilter
    elif filter_type == 4 or filter_type == 1:
        return {
            "filterType": 4,
            "comparisonType": node["comparisonType"],
            "isEnabled": node["isEnabled"],
            "trimDateTimeParameterToDate": node.get(
                "trimDateTimeParameterToDate", False
            ),
            "leftExpression": {
                "expressionType": node["leftExpression"]["expressionType"],
                "columnPath": node["leftExpression"]["columnPath"],
            },
            "rightExpressions": [
                {
                    "expressionType": expr["expressionType"],
                    "parameter": {
                        "dataValueType": expr["parameter"]["dataValueType"],
                        "value": expr["parameter"]["value"]["value"],
                    },
                }
                for expr in node.get("rightExpressions", [])
            ],
        }

    """
    # CompareFilter
    elif filter_type == 1:
        left = node["leftExpression"]

        parsed_left = {"expressionType": left["expressionType"]}

        # FunctionExpression (YEAR, MONTH, etc.)
        if left["expressionType"] == 1:
            parsed_left.update(
                {
                    "functionType": left["functionType"],
                    "functionArgument": {
                        "expressionType": left["functionArgument"]["expressionType"],
                        "columnPath": left["functionArgument"]["columnPath"],
                    },
                    "datePartType": left.get("datePartType"),
                }
            )
        else:
            parsed_left["columnPath"] = left["columnPath"]

        return {
            "filterType": 1,
            "comparisonType": node["comparisonType"],
            "isEnabled": node["isEnabled"],
            "trimDateTimeParameterToDate": node.get(
                "trimDateTimeParameterToDate", False
            ),
            "leftExpression": parsed_left,
            "rightExpression": {
                "expressionType": node["rightExpression"]["expressionType"],
                "parameter": {
                    "dataValueType": node["rightExpression"]["parameter"][
                        "dataValueType"
                    ],
                    "value": node["rightExpression"]["parameter"]["value"],
                },
            },
        }
    """

    # Unknown filter → ignore
    return None


def parse_column(column: dict) -> dict:
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

    if "aggregationType" in column and column["aggregationType"] != 0:
        column_filter = column["serializedFilter"]
        column_items = {}

        if column_filter.get("isEnabled", True):
            for key, filter_item in column_filter["items"].items():
                if not filter_item["isEnabled"]:
                    continue

                column_items[key] = {
                    "filterType": filter_item["filterType"],
                    "comparisonType": filter_item["comparisonType"],
                    "isEnabled": filter_item["isEnabled"],
                    "trimDateTimeParameterToDate": filter_item[
                        "trimDateTimeParameterToDate"
                    ],
                    "leftExpression": {
                        "expressionType": filter_item["leftExpression"][
                            "expressionType"
                        ],
                        "columnPath": filter_item["leftExpression"]["columnPath"],
                    },
                    "rightExpressions": [
                        {
                            "expressionType": expr["expressionType"],
                            "parameter": {
                                "dataValueType": expr["parameter"]["dataValueType"],
                                "value": expr["parameter"]["value"]["value"],
                            },
                        }
                        for expr in filter_item.get("rightExpressions", [])
                    ],
                }

        columns_config["expression"] = {
            "expressionType": 3,
            "functionType": 2,
            "aggregationType": column["aggregationType"],
            "columnPath": column_name,
            "subFilters": {
                "items": column_items,
                "logicalOperation": column_filter["logicalOperation"],
                "isEnabled": column_filter["isEnabled"],
                "filterType": column_filter["filterType"],
                "rootSchemaName": column_filter["rootSchemaName"],
            },
        }

    return columns_config


def _parse_to_esq(dashboard_config: dict) -> dict:
    """Convert dashboard configuration to ESQ format."""
    esq_payload = {
        "esqSerialized": {
            "rootSchemaName": dashboard_config["entitySchemaName"],
            "operationType": 0,
            "includeProcessExecutionData": True,
            "filters": {},
            "columns": {"items": {}},
            "isDistinct": False,
            "rowCount": -1,
            # "rowsOffset": -1,
            "isPageable": False,
            # "allColumns": False,
            "useLocalization": True,
            # "useRecordDeactivation": False,
            # "serverESQCacheParameters": {
            #    "cacheLevel": 0,
            #    "cacheGroup": "",
            #    "cacheItemName": "",
            # },
            # "queryOptimize": False,
            # "useMetrics": False,
            # "adminUnitRoleSources": 0,
            # "querySource": 0,
            # "ignoreDisplayValues": False,
            # "isHierarchical": False,
        },
    }

    filters = parse_filter_node(dashboard_config["filterData"])

    if dashboard_config["entitySchemaName"] == "Case":
        # Add status filter for cases
        esq_payload["esqSerialized"]["filters"] = {
            "items": {
                "0a0c11a3-1453-4a49-a06f-3536eef413e0": {
                    "items": {
                        "6f3c4586-90d0-4db5-8819-31029d341d38": filters,
                        "2dec8579-a7d5-49f0-a99b-1f2b8e0f9fbb": {
                            "items": {
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

    else:
        esq_payload["esqSerialized"]["filters"] = filters

    columns = {
        c["metaPath"]: parse_column(c) for c in dashboard_config["gridConfig"]["items"]
    }

    esq_payload["esqSerialized"]["columns"]["items"] = columns  # type: ignore

    return esq_payload


class DashboardOperationsMixin:
    """
    Mixin class for dashboard operations in Creatio API.
    Provides methods to export dashboards.
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
        dashboard_config = _deep_unescape(dashboard_config)  # type: ignore

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
        return download_file(response, path)
