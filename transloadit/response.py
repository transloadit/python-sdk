from functools import wraps


_MISSING = object()


class Response:
    """
    Transloadit http Response Object

    :Attributes:
        - data (dict):
            Dictionary representation of the returned JSON data. For async
            responses, this can also be preloaded data provided by the async
            request layer.
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
        self._data = data
        self._status_code = status_code
        self._headers = headers

    @property
    def data(self):
        if self._data is _MISSING:
            if self._response is None:
                return None
            self._data = self._response.json()
        return self._data

    @property
    def status_code(self):
        """
        Return the http status code of the request.
        """
        if self._status_code is not _MISSING:
            return self._status_code
        return self._response.status_code

    @property
    def headers(self):
        """
        Return the response headers.
        """
        if self._headers is not _MISSING:
            return self._headers
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
