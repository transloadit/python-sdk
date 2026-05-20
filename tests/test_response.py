import unittest
from unittest import mock

from transloadit.response import Response


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
