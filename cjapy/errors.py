"""Exceptions raised by cjapy."""

from typing import Any, Optional


class CJAAPIError(Exception):
    """An API request returned an HTTP error status.

    cjapy raises this only when the connector has ``raise_on_error=True``.
    By default, error responses are returned as dicts, as in earlier versions.

    Attributes:
        status_code : the HTTP status of the final response, after any retries.
        method : the HTTP method, e.g. "GET".
        url : the full request URL, including query parameters.
        payload : the parsed JSON body, or the raw text when the body is not JSON.
    """

    def __init__(self, status_code: int, method: str, url: str, payload: Optional[Any]):
        self.status_code = status_code
        self.method = method
        self.url = url
        self.payload = payload
        super().__init__(f"{method} {url} returned HTTP {status_code}: {payload!r}"[:1000])

    def __reduce__(self):
        # Exception pickling passes only the message to __init__, so pass all four values,
        # e.g., to return the error from a multiprocessing worker.
        return (self.__class__, (self.status_code, self.method, self.url, self.payload))
