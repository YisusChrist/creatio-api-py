from collections import defaultdict
from typing import Any

from requests.exceptions import TooManyRedirects
from requests.models import Response

from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.logs import logger
from creatio_api_py.utils import log_and_print


def _read_encrypted_cookies(
    api_instance: CreatioAPIInterface,
) -> dict[str, dict[str, Any]]:
    """
    Read and decrypt the encrypted cookies file.

    Returns:
        dict: The decrypted cookies data, or an empty dictionary if the file
            does not exist or decryption fails.
    """
    logger.debug("Reading and decrypting cookies file.")
    if not api_instance.cookies_file.exists():
        return {}

    try:
        encrypted_data: bytes = api_instance.cookies_file.read_bytes()
        logger.debug("Cookies file read successfully.")
        return api_instance.encryption_manager.decrypt(encrypted_data)
    except Exception as e:
        log_and_print("Failed to read or decrypt cookies file", e, api_instance.debug)
        return {}


def _update_cookies_file(
    api_instance: CreatioAPIInterface, cookies_data: dict[str, dict[str, Any]]
) -> None:
    """Encrypt and save cookies data to the file."""
    logger.debug("Updating cookies file with new data.")

    try:
        encrypted_data: bytes = api_instance.encryption_manager.encrypt(cookies_data)
        api_instance.cookies_file.write_bytes(encrypted_data)
        logger.debug("Cookies data successfully updated.")
    except Exception as e:
        log_and_print("Failed to update cookies file", e, api_instance.debug)


def load_session_cookie(api_instance: CreatioAPIInterface, username: str) -> bool:
    """
    Load a session cookie for a specific username, if available.

    Args:
        username (str): The username whose session cookie to load.

    Returns:
        bool: True if a valid session cookie was loaded, False otherwise.
    """
    cookies_data: dict[str, dict[str, Any]] = _read_encrypted_cookies(api_instance)
    url = str(api_instance.base_url)
    if url not in cookies_data or username not in cookies_data[url]:
        return False

    # Load the cookies into the session
    api_instance.session.cookies.update(cookies_data[url][username])  # type: ignore
    logger.debug(f"Session cookie loaded for URL {url} and user {username}.")

    # TODO: Find a more reliable and efficient way to check if the session
    # cookie is still valid
    # Check if the session cookie is still valid
    try:
        response: Response = api_instance.get_collection_data("Account/$count")
        # Check if the request was redirected to the login page
        return not response.history
    except TooManyRedirects:
        return False


def store_session_cookie(api_instance: CreatioAPIInterface, username: str) -> None:
    """
    Store the session cookie for a specific username in a cache file.

    Args:
        username (str): The username associated with the session cookie.
    """
    cookies_data: dict[str, dict[str, Any]] = _read_encrypted_cookies(api_instance)

    # Create a nested dictionary to store cookies for multiple URLs and usernames
    cookies_data = defaultdict(lambda: defaultdict(dict), cookies_data)

    # Update cookies for the given username
    url = str(api_instance.base_url)
    cookies_data[url][username] = api_instance.session_cookies

    # Update the cookies file with the modified data
    _update_cookies_file(api_instance, dict(cookies_data))
