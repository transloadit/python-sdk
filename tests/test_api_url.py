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

    def test_should_not_sign_transloadit_url_for_custom_service(self):
        self.assertFalse(
            should_sign_api_url(
                "https://api2-freja.transloadit.com/assemblies/abc",
                "https://uploads.example.test",
            )
        )
