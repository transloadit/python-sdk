import copy
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import requests

from . import __version__
from .api_url import should_sign_api_url
from .response import as_response

TIMEOUT = 60


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
            headers=self.HEADERS,
            timeout=TIMEOUT,
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
            headers=self.HEADERS,
            timeout=TIMEOUT,
        )

    @as_response
    def put(self, path, data=None):
        """
        Makes a HTTP PUT request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request.

        Return an instance of <transloadit.response.Response>
        """
        url = self._get_full_url(path)
        data = self._to_request_payload(url, data)
        return requests.put(
            url,
            data=data,
            headers=self.HEADERS,
            timeout=TIMEOUT,
        )

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
            headers=self.HEADERS,
            timeout=TIMEOUT,
        )

    def _to_payload(self, data):
        data = copy.deepcopy(data or {})
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
