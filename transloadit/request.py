import hashlib
import hmac
import json
import copy
from datetime import datetime, timedelta

import requests
from six import b

from .response import as_response


class Request(object):
    """
    Transloadit tailored HTTP Request object.

    :Attributes:
        - transloadit (<translaodit.client.Transloadit>):
            An instance of the Transloadit class.

    :Constructor Args:
        - transloadit (<transloadit.client.Transloadit>)
    """

    HEADERS = {'User-Agent': 'Transloadit Python SDK'}

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
        return requests.get(self._get_full_url(path),
                            params=self._to_payload(params),
                            headers=self.HEADERS)

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
        data = self._to_payload(data)
        if extra_data:
            data.update(extra_data)
        return requests.post(self._get_full_url(path), data=data,
                             files=files, headers=self.HEADERS)

    @as_response
    def put(self, path, data=None):
        """
        Makes a HTTP PUT request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request.

        Return an instance of <transloadit.response.Response>
        """
        data = self._to_payload(data)
        return requests.put(self._get_full_url(path), data=data, headers=self.HEADERS)

    @as_response
    def delete(self, path, data=None):
        """
        Makes a HTTP DELETE request.

        :Args:
            - path (str): URL path to which the request should be made.
            - data (Optional[dict]): The body of the request.

        Return an instance of <transloadit.response.Response>
        """
        data = self._to_payload(data)
        return requests.delete(self._get_full_url(path), data=data, headers=self.HEADERS)

    def _to_payload(self, data):
        data = copy.deepcopy(data or {})
        expiry = timedelta(seconds=self.transloadit.duration) + datetime.utcnow()
        data['auth'] = {
            'key': self.transloadit.auth_key,
            'expires': expiry.strftime("%Y/%m/%d %H:%M:%S+00:00")
        }
        json_data = json.dumps(data)
        return {'params': json_data,
                'signature': self._sign_data(json_data)}

    def _sign_data(self, message):
        return hmac.new(b(self.transloadit.auth_secret),
                        message.encode('utf-8'),
                        hashlib.sha1).hexdigest()

    def _get_full_url(self, url):
        if url.startswith(('http://', 'https://')):
            return url
        else:
            return self.transloadit.service + url
