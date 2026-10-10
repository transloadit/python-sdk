import copy
import hashlib
import hmac
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import requests

from . import __version__
from .api_url import should_sign_api_url
from .endpoint_transport import capability_url, sync_network_options, token_request, tus_request, validate_upload_location
from .response import Response, as_response
from .stream import EventParser, StreamError

TIMEOUT = 60


class _ExplicitAuthorization(requests.auth.AuthBase):
    """Keep an explicit Authorization header from being replaced by netrc."""
    def __call__(self, request):
        return request


class Request:
    """
    Transloadit tailored HTTP Request object.

    :Attributes:
        - transloadit (<translaodit.client.Transloadit>):
            An instance of the Transloadit class.

    :Constructor Args:
        - transloadit (<transloadit.client.Transloadit>)
    """

    HEADERS = {"Transloadit-Client": "python-sdk:" + __version__}

    def __init__(self, transloadit):
        self.transloadit = transloadit

    def _headers(self, url):
        headers = dict(self.HEADERS)
        if getattr(self.transloadit, "bearer_token", None) and should_sign_api_url(url, self.transloadit.service):
            headers["Authorization"] = "Bearer " + self.transloadit.bearer_token
        return headers

    def _auth(self, url):
        return _ExplicitAuthorization() if "Authorization" in self._headers(url) else None

    @as_response
    def get(self, path, params=None):
        """
        Makes a HTTP GET request.

        :Args:
            - path (str): URL path to which the request should be made.
            - params (Optional[dict]): Optional params to send along with the request.

        Return an instance of <transloadit.response.Response>
        """
        url = self._get_full_url(path)
        return requests.get(
            url,
            params=self._to_request_payload(url, params),
            headers=self._headers(url),
            auth=self._auth(url),
            timeout=TIMEOUT,
            allow_redirects=False,
        )

    @as_response
    def post(self, path, data=None, extra_data=None, files=None):
        """
        Makes a HTTP POST request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request. This would be stored under the 'params' field.
            - extra_data (Optional[dict]): This is also added to the body of the request but not under the
                'params' field.
            - files (Optional[dict]): Files to upload with the request. This should be a key, value pair of
                field name and file stream respectively.

        Return an instance of <transloadit.response.Response>
        """
        url = self._get_full_url(path)
        data = self._to_request_payload(url, data)
        if extra_data:
            if data is None:
                data = {}
            data.update(extra_data)
        return requests.post(
            url,
            data=data,
            files=files,
            headers=self._headers(url),
            auth=self._auth(url),
            timeout=TIMEOUT,
            allow_redirects=False,
        )

    @as_response
    def put(self, path, data=None, extra_data=None, files=None):
        """
        Makes a HTTP PUT request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request.

        Return an instance of <transloadit.response.Response>
        """
        url = self._get_full_url(path)
        data = self._to_request_payload(url, data) or {}
        if extra_data:
            data.update(extra_data)
        return requests.put(
            url,
            data=data,
            files=files,
            headers=self._headers(url),
            auth=self._auth(url),
            timeout=TIMEOUT,
            allow_redirects=False,
        )

    @as_response
    def patch(self, path, data=None):
        url = self._get_full_url(path)
        return requests.patch(url, data=self._to_request_payload(url, data),
                              headers=self._headers(url), auth=self._auth(url), timeout=TIMEOUT, allow_redirects=False)

    @as_response
    def delete(self, path, data=None):
        """
        Makes a HTTP DELETE request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request.

        Return an instance of <transloadit.response.Response>
        """
        url = self._get_full_url(path)
        data = self._to_request_payload(url, data)
        return requests.delete(
            url,
            data=data,
            headers=self._headers(url),
            auth=self._auth(url),
            timeout=TIMEOUT,
            allow_redirects=False,
        )

    def _to_payload(self, data):
        data = copy.deepcopy(data or {})
        if getattr(self.transloadit, "bearer_token", None):
            return {"params": json.dumps(data)}
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self.transloadit.duration)
        if "auth" in data and not isinstance(data["auth"], dict):
            raise ValueError("auth must be a dictionary when provided.")
        auth = data.get("auth") or {}
        auth.update({
            "key": self.transloadit.auth_key,
            "expires": expiry.strftime("%Y/%m/%d %H:%M:%S+00:00"),
        })
        data["auth"] = auth
        json_data = json.dumps(data)
        return {"params": json_data, "signature": self._sign_data(json_data)}

    def _to_request_payload(self, url, data):
        if should_sign_api_url(url, self.transloadit.service):
            return self._to_payload(data)
        return copy.deepcopy(data) if data else None

    def _sign_data(self, message):
        hash_string = hmac.new(
            self.transloadit.auth_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha384
        ).hexdigest()
        return f"sha384:{hash_string}"

    def _get_full_url(self, url):
        if url.startswith(("http://", "https://")):
            return url
        else:
            return self.transloadit.service + url

    def public(self, method, path, params=None, data=None):
        with requests.Session() as session:
            session.trust_env = False  # Do not borrow netrc credentials for unsigned endpoints.
            url = self._get_full_url(path)
            raw = session.request(method, url, params=params, data=data,
                                  headers=self.HEADERS, timeout=TIMEOUT, allow_redirects=False, **sync_network_options(url))
            return Response(raw)

    def issue_bearer_token(self, data=None):
        url, data, headers = token_request(self.transloadit, data)
        headers.update(self.HEADERS)
        with requests.Session() as session:
            session.trust_env = False
            return Response(session.post(url, data=data, headers=headers, timeout=TIMEOUT, allow_redirects=False, **sync_network_options(url)))

    def tus(self, operation_id, location, headers=None, body=None):
        spec, url, headers, body = tus_request(self.transloadit, operation_id, location, headers, body)
        headers.update(self.HEADERS)
        with requests.Session() as session:
            session.trust_env = False
            raw = session.request(spec["method"], url, data=body, headers=headers,
                                  timeout=TIMEOUT, allow_redirects=False, **sync_network_options(url))
            response = Response(raw, data=raw.content) if spec["binary_response"] else Response(raw)
        if spec["method"] == "POST":
            validate_upload_location(self.transloadit, url, response)
        return response

    @contextmanager
    def stream_status(self, url, *, read_timeout=120, max_event_size=1048576):
        url = capability_url(self.transloadit, url, "status-stream")
        parser = EventParser(max_event_size)
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, headers={**self.HEADERS, "Accept": "text/event-stream"},
                             timeout=(TIMEOUT, read_timeout), stream=True, allow_redirects=False,
                             **sync_network_options(url)) as response:
                if response.status_code != 200:
                    raise StreamError(response.status_code)
                if response.headers.get("Content-Type", "").split(";", 1)[0].lower() != "text/event-stream":
                    raise StreamError(response.status_code, "Expected text/event-stream")

                def events():
                    # EOF is not Assembly success; callers inspect the final status.
                    # Keep transport exception types for existing retry policies.
                    # read1 returns available bytes without waiting to fill a chunk.
                    while chunk := response.raw.read1(65536, decode_content=True):
                        for event in parser.feed(chunk):
                            yield event
                            if event.terminal:
                                return

                yield events()
