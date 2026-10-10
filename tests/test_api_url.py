import unittest

from transloadit.api_url import should_sign_api_url


class ApiUrlTest(unittest.TestCase):
    def test_regional_signing_follows_contract_hosts_and_https_port(self):
        service = "https://api2.transloadit.com"
        for host in ("api2-x.other.transloadit.com", "api2-xn--example.transloadit.com", "api2-morven.transloadit.com:8443"):
            with self.subTest(host=host):
                self.assertFalse(should_sign_api_url(f"https://{host}/auth_keys", service))
        self.assertTrue(should_sign_api_url("https://api2-morven.transloadit.com:443/auth_keys", service))

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
