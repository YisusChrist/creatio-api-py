import json
from datetime import datetime
from pathlib import Path

from requests.models import Response

from creatio_api_py.api.operations.files import download_file
from creatio_api_py.api.request_handler import make_request
from creatio_api_py.interfaces import CreatioAPIInterface


def _deep_unescape(obj: dict | list | str) -> dict | list | str:
    """
    Converts deeply escaped JSON strings within a structure to real Python
    objects.

    Recursively walks a structure and:
    - If a value is a string that contains valid JSON -> json.loads()
    - Repeats until everything is real Python objects

    Returns:
        dict | list | str: The unescaped object.
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


def parse_filter_node(node: dict) -> dict | None:
    """
    Parses a Terrasoft filter node (FilterGroup or leaf filter) into an
    ESQ-compatible structure.

    It handles different filter types including CompareFilter, IsNullFilter,
    InFilter, AggregationFilter, and FilterGroup (recursive).

    Args:
        node (dict): The filter node to parse.

    Returns:
        dict | None: The parsed filter node in ESQ format or None if the node
            is disabled or invalid.
    """
    if not node.get("isEnabled", True):
        return None

    filter_type = node.get("filterType")

    # FilterGroup (recursive)
    if filter_type == 6:
        parsed: dict = {
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
                parsed["items"][key] = parsed_child  # type: ignore

        return parsed if parsed["items"] else None

    filter_data: dict = {
        "filterType": filter_type,
        "comparisonType": node["comparisonType"],
        "isEnabled": node["isEnabled"],
        "trimDateTimeParameterToDate": node.get("trimDateTimeParameterToDate", False),
        "leftExpression": {
            "expressionType": node["leftExpression"]["expressionType"],
        },
    }

    # CompareFilter
    if filter_type == 1:
        left: dict = node["leftExpression"]
        right: dict = node["rightExpression"]

        if left["expressionType"] == 1:
            # Function expression (YEAR, MONTH, etc.)
            filter_data["leftExpression"] = {
                "expressionType": left["expressionType"],
                "functionType": left["functionType"],
                "functionArgument": {
                    "expressionType": left["functionArgument"]["expressionType"],
                    "columnPath": left["functionArgument"]["columnPath"],
                },
                "datePartType": left.get("datePartType"),
            }
        else:
            # Simple expression
            filter_data["leftExpression"]["columnPath"] = left["columnPath"]

        if right["expressionType"] == 1:
            filter_data["rightExpression"] = {
                "expressionType": right["expressionType"],
                "functionType": right["functionType"],
                "macrosType": right["macrosType"],
            }
        else:
            filter_data["rightExpression"] = {
                "expressionType": right["expressionType"],
                "parameter": {
                    "dataValueType": right["parameter"]["dataValueType"],
                    "value": right["parameter"]["value"],
                },
            }

        return filter_data
    # IsNullFilter
    elif filter_type == 2:
        filter_data["isNull"] = node["isNull"]
    # InFilter
    elif filter_type == 4:
        filter_data["rightExpressions"] = [
            {
                "expressionType": expr["expressionType"],
                "parameter": {
                    "dataValueType": expr["parameter"]["dataValueType"],
                    "value": expr["parameter"]["value"]["value"],
                },
            }
            for expr in node.get("rightExpressions", [])
        ]
    # AggregationFilter
    elif filter_type == 5:
        filter_data["subFilters"] = parse_filter_node(node["subFilters"])
    # Unknown filter → ignore
    else:
        return None

    filter_data["leftExpression"]["columnPath"] = node["leftExpression"]["columnPath"]
    return filter_data


def parse_arithmetic_node(node: dict) -> dict | None:
    """
    Parse an arithmetic expression node into ESQ format.

    Args:
        node (dict): The arithmetic expression node.

    Returns:
        dict | None: The parsed arithmetic expression in ESQ format or None if
            the node is invalid.
    """
    if "value" in node:
        return {
            "expressionType": 2,
            "parameter": {
                "dataValueType": node["dataType"],
                "value": node["value"],
            },
        }

    if "subFilters" in node:
        return {
            "expressionType": 3,
            "functionType": 2,
            "aggregationType": node["aggregationType"],
            "columnPath": node["columnPath"],
            "subFilters": parse_filter_node(node["subFilters"]),
        }

    elif "leftExpression" in node and "rightExpression" in node:
        return {
            "expressionType": 4,
            "arithmeticOperation": node["arithmeticOperatorType"],
            "leftArithmeticOperand": parse_arithmetic_node(node["leftExpression"]),
            "rightArithmeticOperand": parse_arithmetic_node(node["rightExpression"]),
        }

    return None


def parse_column(column: dict) -> dict:
    """
    Parse a dashboard column configuration into ESQ format handling simple
    columns, aggregated columns, and arithmetic expressions.

    Args:
        column (dict): The dashboard column configuration.

    Returns:
        dict: The parsed column configuration in ESQ format.
    """
    column_name: str | None = column.get("metaPath")
    columns_config: dict = {
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
        columns_config["expression"] = {
            "expressionType": 3,
            "functionType": 2,
            "aggregationType": column["aggregationType"],
            "columnPath": column_name,
            "subFilters": parse_filter_node(column["serializedFilter"]),
        }
    elif not column_name:
        columns_config["expression"] = parse_arithmetic_node(column["expression"])

    return columns_config


def parse_to_esq(dashboard_config: dict) -> dict:
    """
    Convert dashboard configuration to ESQ format.

    Args:
        dashboard_config (dict): The dashboard configuration.

    Returns:
        dict: The ESQ representation of the dashboard configuration.
    """
    esq_payload: dict = {
        "esqSerialized": {
            "rootSchemaName": dashboard_config["entitySchemaName"],
            "operationType": 0,
            "includeProcessExecutionData": True,
            "filters": {},
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

    filters: dict | None = parse_filter_node(dashboard_config["filterData"])

    # Case section
    if (
        dashboard_config["sectionId"] == "c97824d9-3952-4d5e-9a5b-c6c468bf555a"
        and "sectionBindingColumn" in dashboard_config
    ):
        # Add status filter for cases
        binding_path: str = (
            f"[Case:Id:{dashboard_config['sectionBindingColumn']}].Status.IsFinal"
        )

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
                                        "columnPath": binding_path,
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

    columns: dict[str, dict] = {
        c["bindTo"]: parse_column(c) for c in dashboard_config["gridConfig"]["items"]
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
            dashboard_name (str): The name of the dashboard to export.
            path (str | Path, optional): The path to save the exported
                dashboard file. Defaults to the current working directory.
        Raises:
            ValueError: If the dashboard with the specified name is not found
                or if the export key cannot be obtained.

        Returns:
            Response: The response from the dashboard export request.
        """
        dashboard_config = json.loads(
            self.get_collection_data(
                "SysDashboard", record_id=dashboard_id, value="Items"
            ).content.decode("utf-8-sig")
        ).get(dashboard_name)
        if not dashboard_config:
            raise ValueError(f"Dashboard with name {dashboard_name} not found.")

        dashboard_config: dict = dashboard_config["parameters"]
        dashboard_config = _deep_unescape(dashboard_config)  # type: ignore

        now: str = datetime.now().strftime("%d_%m_%Y_%H_%M")
        file_name: str = f"{dashboard_config['caption'].lower().replace(' ', '_')}_{now}"

        esq: dict = parse_to_esq(dashboard_config)

        # encode payload json to str
        esq_serialized: str = json.dumps(esq["esqSerialized"], separators=(",", ":"))
        payload: dict[str, str] = {"esqSerialized": esq_serialized}

        export_key: str = make_request(
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
