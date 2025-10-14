from core_helpers.logs import logger


logger.setup_logger("creatio_api_py", "creatio_api_py.log")

from creatio_api_py.api.base import CreatioODataAPI


__all__: list[str] = ["CreatioODataAPI"]
