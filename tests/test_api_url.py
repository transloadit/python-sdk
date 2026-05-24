import unittest

from transloadit.api_url import should_sign_api_url


class ApiUrlTest(unittest.TestCase):
    def test_should_sign_same_service_url_with_different_host_casing(self):
        self.assertTrue(
            should_sign_api_url(
                "https://API2.transloadit.com/assemblies/abc",
                "https://api2.transloadit.com",
            )
        )

