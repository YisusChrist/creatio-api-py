"""Utility functions for the Creatio OData API."""

from email.message import Message
from typing import Optional

from rich import print  # pylint: disable=redefined-builtin

from creatio_api_py.logs import logger


def print_exception(e: Exception, custom_msg: str = "") -> None:
    """
    Print the exception and its traceback.

    Args:
        e (Exception): The exception to print.
        custom_msg (str, optional): Custom message to prepend to the exception.
    """
    if custom_msg:
        custom_text: str = f"{custom_msg}: "
    else:
        custom_text = ""
    print(f"{custom_text}[red]{e.__class__.__name__}:[/] {str(e)}")


def parse_content_disposition(content_disposition: str) -> str | None:
    """
    Get the filename from a `Content-Disposition` header.

    Reference: https://stackoverflow.com/a/78073510

    Args:
        header (str): The `Content-Disposition` header.

    Returns:
        str | None: The filename from the header.
    """
    msg = Message()
    msg["content-disposition"] = content_disposition
    filename: str | None = msg.get_filename()
    return filename.encode("latin-1").decode("utf-8") if filename else None


def log_and_print(message: str, exception: Exception, debug: bool = False) -> None:
    """
    Log and print a message.

    Args:
        message (str): The message to log and print.
        level (str): The logging level (e.g., 'info', 'debug', 'error').
        debug (bool): Whether to print the message in debug mode.
    """
    logger.error(f"{message}: {exception}")
    if debug:
        print_exception(exception, message)
