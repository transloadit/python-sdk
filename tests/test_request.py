import json
import unittest
import urllib.parse

import requests_mock

from . import request_body_matcher
from transloadit.client import Transloadit
from transloadit.request import Request


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit("key", "secret")
        self.request = Request(self.transloadit)

    @requests_mock.Mocker()
    def test_get(self, mock):
        url = f"{self.transloadit.service}/foo"
        mock.get(
            url,
            text='{"ok": "it works"}',
            request_headers={"Transloadit-Client": "python-sdk:2.0.0"},
        )

        response = self.request.get("/foo")
        self.assertEqual(response.data["ok"], "it works")

    @requests_mock.Mocker()
    def test_post(self, mock):
        url = f"{self.transloadit.service}/foo"
        sub_body = urllib.parse.quote_plus('"foo": "bar"')
        mock.post(
            url,
            text='{"ok": "it works"}',
            additional_matcher=request_body_matcher(sub_body),
        )

        response = self.request.post("/foo", data={"foo": "bar"})
        self.assertEqual(response.data["ok"], "it works")

    def test_payload_preserves_custom_auth_constraints(self):
        payload = self.request._to_payload(
            {
                "auth": {
                    "max_size": 1024,
                    "referer": "https://example.com",
                },
                "foo": "bar",
            }
        )

        params = json.loads(payload["params"])
        self.assertEqual(params["auth"]["key"], "key")
        self.assertIn("expires", params["auth"])
        self.assertEqual(params["auth"]["max_size"], 1024)
        self.assertEqual(params["auth"]["referer"], "https://example.com")

    def test_full_url_rejects_external_absolute_urls(self):
        self.assertEqual(
            self.request._get_full_url(f"{self.transloadit.service}/foo"),
            f"{self.transloadit.service}/foo",
        )
        self.assertEqual(
            self.request._get_full_url("https://api2-region.transloadit.com/foo"),
            "https://api2-region.transloadit.com/foo",
        )
        with self.assertRaises(ValueError):
            self.request._get_full_url("https://example.com/foo")

    @requests_mock.Mocker()
    def test_put(self, mock):
        url = f"{self.transloadit.service}/foo"
        sub_body = urllib.parse.quote_plus('"foo": "bar"')
        mock.put(
            url,
            text='{"ok": "it works"}',
            additional_matcher=request_body_matcher(sub_body),
        )

        response = self.request.put("/foo", data={"foo": "bar"})
        self.assertEqual(response.data["ok"], "it works")

    @requests_mock.Mocker()
    def test_delete(self, mock):
        url = f"{self.transloadit.service}/foo"
        sub_body = urllib.parse.quote_plus('"foo": "bar"')
        mock.delete(
            url,
            text='{"ok": "it works"}',
            additional_matcher=request_body_matcher(sub_body),
        )

        response = self.request.delete("/foo", data={"foo": "bar"})
        self.assertEqual(response.data["ok"], "it works")
