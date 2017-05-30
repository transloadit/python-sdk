import hashlib
import hmac
import json
import copy
from datetime import datetime, timedelta

import requests


class Request(object):
    def __init__(self, client):
        self.client = client

    def get(self, path, params=None):
        """docstrings here"""
        return requests.get(self._get_full_url(path), params=self._to_payload(params))

    def post(self, path, data=None):
        """docstrings here"""
        return requests.post(self._get_full_url(path), data=self._to_payload(data))

    def put(self, path, data=None):
        """docstrings here"""
        return requests.put(self._get_full_url(path), data=self._to_payload(data))

    def delete(self, path, data=None):
        """docstrings here"""
        return requests.delete(self._get_full_url(path), data=self._to_payload(data))

    def _to_payload(self, data):
        data = {} if data is None else data
        data = copy.deepcopy(data)
        expiry = timedelta(seconds=self.client.duration) + datetime.utcnow()
        data['auth'] = {
            'key': self.client.key,
            'expires': expiry.strftime("%Y/%m/%d %H:%M:%S+00:00")
        }
        json_data = json.dumps(data)
        return {'params': json_data,
                'signature': self._sign_data(json_data)}

    def _sign_data(self, message):
        return hmac.new(self.client.secret, message.encode('utf-8'), hashlib.sha1).hexdigest()

    def _get_full_url(self, url):
        if url.startswith('http://') or url.startswith('https://'):
            return url
        else:
            return self.client.host + url
