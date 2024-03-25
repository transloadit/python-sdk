import copy
import json
import unittest
from datetime import timedelta

import requests_mock

from tests import get_test_time, request_body_matcher
from transloadit.client import Transloadit
from transloadit.request import Request


class TestSignatureAuthentication(unittest.TestCase):
    def setUp(self):
        self.mock_client = MockClient("TRANSLOADIT_KEY", "TRANSLOADIT_SECRET")
        self.json_response = (
            '{"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef45673"}'
        )

    @requests_mock.Mocker()
    def test_fixed_signature(self, mock):
        # Test a request with a fixed timestamp in order to have reproducible results
        assembly = self.mock_client.new_assembly()
        assembly.add_step("import", "/http/import",
                          options={"url": "https://demos.transloadit.com/inputs/chameleon.jpg"})
        assembly.add_step("resize", "/image/resize", {"use:": "import", "width": 70, "height": 70})

        url = f"{self.mock_client.service}/assemblies"
        mock.post(
            url,
            text=self.json_response,
            additional_matcher=request_body_matcher(
                "signature=sha384"
                "%3A46943b5542af95679940d94507865b20b36cb1808a7a9dc64c6255f26d1e921bd6574443b80b0dcd595769268f74273c"),
        )

        assembly.create(resumable=False)


class MockClient(Transloadit):
    """
        Mock Class of the Transloadit Clients, which loads the modified MockRequest Class
        instead of the Standard Request class.
    """

    def __init__(self,
                 auth_key: str,
                 auth_secret: str,
                 service: str = "https://api2.transloadit.com",
                 duration: int = 300):
        if not service.startswith(("http://", "https://")):
            service = "https://" + service

        self.service = service
        self.auth_key = auth_key
        self.auth_secret = auth_secret
        self.duration = duration
        self.request = MockRequest(self)


class MockRequest(Request):
    """
        Mock Request Class, which uses a fixed datetime for generating the signature.
        This is for having a reproducible value to test against.
    """
    def _to_payload(self, data):
        data = copy.deepcopy(data or {})
        expiry = timedelta(seconds=self.transloadit.duration) + get_test_time()
        data["auth"] = {
            "key": self.transloadit.auth_key,
            "expires": expiry.strftime("%Y/%m/%d %H:%M:%S+00:00"),
        }
        json_data = json.dumps(data)

        return {"params": json, "signature": self._sign_data(json_data)}
