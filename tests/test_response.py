import unittest
from unittest import mock

from transloadit.response import Response, _MISSING


class ResponseTest(unittest.TestCase):
    def test_response_data_is_assignable_and_eager_for_sync_responses(self):
        raw = mock.Mock()
        raw.json.return_value = {"ok": "original"}
        raw.status_code = 200
        raw.headers = {"X-Test": "1"}

        response = Response(raw)

        raw.json.assert_called_once()

        response.data = {"ok": "changed"}

        self.assertEqual(response.data, {"ok": "changed"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers, {"X-Test": "1"})

    def test_response_uses_text_fallback_for_sync_non_json_responses(self):
        raw = mock.Mock()
        raw.json.side_effect = ValueError("not json")
        raw.content = b"bad gateway"
        raw.encoding = "utf-8"
        raw.status_code = 502
        raw.headers = {"Content-Type": "text/html"}

        response = Response(raw)

        self.assertEqual(response.data, "bad gateway")
        self.assertEqual(response.status_code, 502)

    def test_response_uses_bytes_fallback_for_undecodable_sync_non_json_responses(self):
        raw = mock.Mock()
        raw.json.side_effect = ValueError("not json")
        raw.content = b"\xff\xfe"
        raw.encoding = "utf-8"
        raw.status_code = 200
        raw.headers = {"Content-Type": "application/octet-stream"}

        response = Response(raw)

        self.assertEqual(response.data, b"\xff\xfe")

    def test_response_lazily_rehydrates_data_when_missing(self):
        raw = mock.Mock()
        raw.json.return_value = {"ok": "lazy"}
        raw.status_code = 204
        raw.headers = {"X-Test": "1"}

        response = Response()
        response._response = raw
        response._data = _MISSING

        self.assertEqual(response.data, {"ok": "lazy"})
        raw.json.assert_called_once()

    def test_response_supports_async_preloaded_values_and_empty_default(self):
        empty = Response()
        self.assertIsNone(empty.data)
        self.assertIsNone(empty.status_code)
        self.assertIsNone(empty.headers)

        response = Response(
            data={"ok": "async"},
            status_code=202,
            headers={"X-Test": "1"},
        )

        self.assertEqual(response.data, {"ok": "async"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.headers, {"X-Test": "1"})
