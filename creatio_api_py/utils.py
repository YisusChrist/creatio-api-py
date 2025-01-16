"""Utility functions for the Creatio OData API."""

from email.message import Message

from rich import print  # pylint: disable=redefined-builtin


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


def parse_content_disposition(header: str) -> str | None:
    """
    Get the filename from a `Content-Disposition` header.

    Reference: https://stackoverflow.com/a/78073510

    Args:
        header (str): The `Content-Disposition` header.

    Returns:
        str | None: The filename from the header.
    """
    msg = Message()
    msg["content-disposition"] = header
    return msg.get_filename()
