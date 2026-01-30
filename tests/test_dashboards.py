import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from creatio_api_py import CreatioODataAPI
from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import print_exception


BASE_PATH: Path = Path(__file__).parent
DATA_PATH: Path = BASE_PATH / "data"
ESQ_PATH: Path = BASE_PATH.parent / "json" / "esq.json"
GENERATED_XLSX_DIR: Path = BASE_PATH.parent


@pytest.fixture(scope="session")
def api() -> CreatioAPIInterface:
    """
    Authenticated Creatio API client.
    Fails the test session if authentication is not possible.
    """
    if not load_dotenv():
        print("No .env file found. Using environment variables.")

    url = os.getenv("CREATIO_URL")
    api: CreatioAPIInterface = CreatioODataAPI(base_url=url)  # type: ignore
    # return api

    try:
        # Authenticate with the API
        api.authenticate()
        # print_response_summary(response)
    except Exception as e:
        print_exception(e, f"Unable to authenticate on {url}")

    return api


@pytest.mark.parametrize(
    "dashboard_file", DATA_PATH.glob("*.json"), ids=lambda p: p.stem
)
def test_export_dashboards(api: CreatioAPIInterface, dashboard_file: Path) -> None:
    with open(dashboard_file, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    if not expected_data:
        pytest.skip("Skipping non-case dashboard")

    dashboard_id, dashboard_name = dashboard_file.stem.split("_", 1)

    response = api.export_dashboard(dashboard_id, dashboard_name)

    assert response.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in response.headers["content-type"]
    )

    with open(ESQ_PATH, "r", encoding="utf-8") as f:
        exported_data = json.load(f)

    assert exported_data == expected_data


@pytest.fixture(scope="session", autouse=True)
def cleanup_generated_xlsx():
    """
    Cleanup xlsx files generated during the test session.
    """
    yield  # run all tests first

    for xlsx_file in GENERATED_XLSX_DIR.rglob("*.xlsx"):
        try:
            xlsx_file.unlink()
        except Exception:
            pass
