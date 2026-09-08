from collections import defaultdict
from typing import Any

from core_helpers.logs import logger
from requests.exceptions import TooManyRedirects
from requests.models import Response

from creatio_api_py.interfaces import CreatioAPIInterface
from creatio_api_py.utils import log_and_print


def _read_encrypted_sessions(
    api_instance: CreatioAPIInterface,
) -> dict[str, dict[str, Any]]:
    """
    Read and decrypt the encrypted sessions file.
    
    Args:
        api_instance (CreatioAPIInterface): The API instance to access
            encryption manager and session file.

    Returns:
        dict: The decrypted sessions data, or an empty dictionary if the file
            does not exist or decryption fails.
    """
    logger.debug("Reading and decrypting sessions file.")
    if not api_instance.session_file.exists():
        return {}

    try:
        encrypted_data: bytes = api_instance.session_file.read_bytes()
        logger.debug("Sessions file read successfully.")
        return api_instance.encryption_manager.decrypt(encrypted_data)
    except Exception as e:
        log_and_print("Failed to read or decrypt sessions file", e, api_instance.debug)
        return {}


def _update_session_file(
    api_instance: CreatioAPIInterface, sessions_data: dict[str, dict[str, Any]]
) -> None:
    """
    Encrypt and save sessions data to the file.

    Args:
        api_instance (CreatioAPIInterface): The API instance to access
            encryption manager and session file.
        sessions_data (dict): The sessions data to encrypt and save.
    """
    logger.debug("Updating sessions file with new data.")

    try:
        encrypted_data: bytes = api_instance.encryption_manager.encrypt(sessions_data)
        api_instance.session_file.write_bytes(encrypted_data)
        logger.debug("Sessions data successfully updated.")
    except Exception as e:
        log_and_print("Failed to update sessions file", e, api_instance.debug)


def load_session(api_instance: CreatioAPIInterface, username: str) -> bool:
    """
    Load a session for a specific username, if available.

    Args:
        api_instance (CreatioAPIInterface): The API instance to load the
            session into.
        username (str): The username whose session to load.

    Returns:
        bool: True if a valid session was loaded, False otherwise.
    """
    sessions_data: dict[str, dict[str, Any]] = _read_encrypted_sessions(api_instance)
    url = str(api_instance.base_url)
    if url not in sessions_data or username not in sessions_data[url]:
        return False

    # Load the cached sessions for the given username
    if api_instance.username:
        api_instance.session.cookies.update(sessions_data[url][username])
    elif api_instance.client_id:
        api_instance.oauth_token = sessions_data[url][username].get("access_token")

    logger.debug(f"Session loaded for URL {url} and user {username}.")

    # TODO: Find a more reliable and efficient way to check if the session is still valid
    # Check if the session is still valid
    try:
        response: Response = api_instance.get_collection_data("Account/$count")
        # Check if the request was redirected to the login page
        return not response.history
    except TooManyRedirects:
        return False


def store_session(api_instance: CreatioAPIInterface, username: str) -> None:
    """
    Store the session for a specific username in a cache file.

    Args:
        api_instance (CreatioAPIInterface): The API instance to store the
            session from.
        username (str): The username associated with the session.
    """
    sessions_data: dict[str, dict[str, Any]] = _read_encrypted_sessions(api_instance)

    # Create a nested dictionary to store sessions for multiple URLs and usernames
    sessions_data = defaultdict(lambda: defaultdict(dict), sessions_data)
    url = str(api_instance.base_url)

    # Update the cached sessions for the given username
    if api_instance.username:
        sessions_data[url][username] = api_instance.session_cookies
    elif api_instance.client_id:
        sessions_data[url][username] = {"access_token": api_instance.oauth_token}

    logger.debug(f"Session stored for URL {url} and user {username}.")

    # Update the sessions file with the modified data
    _update_session_file(api_instance, dict(sessions_data))
