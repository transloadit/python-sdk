

class Response(object):
    def __init__(self, response):
        self._response = response
        self.data = self._response.json()

    @property
    def status_code(self):
        return self._response.status_code

    @property
    def headers(self):
        return self._response.headers


def as_response(fn):
    def wrapper(*args, **kwargs):
        return Response(fn(*args, **kwargs))
    return wrapper
