from six import wraps


class Response(object):
    """
    Transloadit http Response Object

    :Attributes:
        - data (dict):
            Dictionary representation of the returned JSON data.
        - status_code (int):
            HTTP response status code
        - headers (dict):
            Dictionary representation of the headers returned from the server.

    :Constructor Args:
        - response (<requests.Response>): The bare response object from the requests library.
    """
    def __init__(self, response):
        self._response = response
        self.data = self._response.json()

    @property
    def status_code(self):
        """
        Return the http status code of the request.
        """
        return self._response.status_code

    @property
    def headers(self):
        """
        Return the response headers.
        """
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
