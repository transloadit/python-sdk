from functools import wraps


_MISSING = object()


class Response:
    """
    Transloadit http Response Object

    :Attributes:
        - data (dict, str, bytes, None):
            Parsed JSON data, text fallback, raw bytes for undecodable async
            responses, or None when no response data is available.
        - status_code (int):
            HTTP response status code
        - headers (dict):
            Dictionary representation of the headers returned from the server.

    :Constructor Args:
        - response (<requests.Response>): The bare response object from the requests library.
        - data (Optional[dict]): Preloaded JSON data for async responses.
        - status_code (Optional[int]): Preloaded HTTP status code for async responses.
        - headers (Optional[dict]): Preloaded response headers for async responses.
    """

    def __init__(self, response=None, data=_MISSING, status_code=_MISSING, headers=_MISSING):
        self._response = response
        if data is _MISSING and response is not None:
            data = self._read_sync_response_data()
        self._data = data
        self._status_code = status_code
        self._headers = headers

    def _read_sync_response_data(self):
        try:
            return self._response.json()
        except ValueError:
            try:
                return self._response.content.decode(
                    self._response.encoding or "utf-8",
                    errors="strict",
                )
            except UnicodeDecodeError:
                return self._response.content

    @property
    def data(self):
        if self._data is _MISSING:
            if self._response is None:
                return None
            self._data = self._read_sync_response_data()
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def status_code(self):
        """
        Return the http status code of the request.
        """
        if self._status_code is not _MISSING:
            return self._status_code
        if self._response is None:
            return None
        return self._response.status_code

    @property
    def headers(self):
        """
        Return the response headers.
        """
        if self._headers is not _MISSING:
            return self._headers
        if self._response is None:
            return None
        return self._response.headers


def as_response(func):
    """
    Decorator function that converts the output of a function into an instance
    of the <transloadit.response.Response> class.
    """

    @wraps(func)
    def _wrapper(*args, **kwargs):
        return Response(func(*args, **kwargs))

    return _wrapper
