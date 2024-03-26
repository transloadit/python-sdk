import datetime


def request_body_matcher(pattern):
    def _callback(request):
        return pattern in request.text

    return _callback


def get_test_time():
    return datetime.datetime.fromisoformat("2024-04-04T04:44:44")
