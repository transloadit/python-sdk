def request_body_matcher(pattern):
    def _callback(request):
        return pattern in request.text

    return _callback
