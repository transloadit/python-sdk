import unittest
from unittest import mock
import json
import os
import platform
import subprocess
import time
from pathlib import Path

import requests_mock
from six.moves import urllib

from . import request_body_matcher
from transloadit.client import Transloadit


def get_expected_url(params):
    """Get expected URL from Node.js reference implementation."""
    if os.getenv('TEST_NODE_PARITY') != '1':
        return None

    # Skip Node.js parity testing on Windows
    if platform.system() == 'Windows':
        print('Skipping Node.js parity testing on Windows')
        return None

    # Check for tsx before trying to use it
    tsx_path = subprocess.run(['which', 'tsx'], capture_output=True)
    if tsx_path.returncode != 0:
        raise RuntimeError('tsx command not found. Please install it with: npm install -g tsx')

    script_path = Path(__file__).parent / 'node-smartcdn-sig.ts'
    json_input = json.dumps(params)

    result = subprocess.run(
        ['tsx', str(script_path)],
        input=json_input,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f'Node script failed: {result.stderr}')

    return result.stdout.strip()


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit("key", "secret")
        # Use fixed timestamp for all Smart CDN tests
        self.expire_at_ms = 1732550672867

    def assert_parity_with_node(self, url, params, message=''):
        """Assert that our URL matches the Node.js reference implementation."""
        expected_url = get_expected_url(params)
        if expected_url is not None:
            self.assertEqual(expected_url, url, message or 'URL should match Node.js reference implementation')

    @requests_mock.Mocker()
    def test_get_assembly(self, mock):
        id_ = "abcdef12345"
        url = f"{self.transloadit.service}/assemblies/{id_}"
        mock.get(url, text='{"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef12345"}')

        response = self.transloadit.get_assembly(assembly_id=id_)
        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(response.data["assembly_id"], "abcdef12345")

    @requests_mock.Mocker()
    def test_list_assemblies(self, mock):
        url = f"{self.transloadit.service}/assemblies"
        mock.get(url, text='{"items":[],"count":0}')

        response = self.transloadit.list_assemblies()
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["count"], 0)

    @requests_mock.Mocker()
    def test_cancel_assembly(self, mock):
        id_ = "abcdef12345"
        url = f"{self.transloadit.service}/assemblies/{id_}"
        mock.delete(
            url, text='{"ok": "ASSEMBLY_CANCELED", "assembly_id": "abcdef12345"}'
        )

        response = self.transloadit.cancel_assembly(id_)
        self.assertEqual(response.data["ok"], "ASSEMBLY_CANCELED")
        self.assertEqual(response.data["assembly_id"], "abcdef12345")

    @requests_mock.Mocker()
    def test_get_template(self, mock):
        id_ = "abcdef12345"
        url = f"{self.transloadit.service}/templates/{id_}"
        mock.get(url, text='{"ok": "TEMPLATE_FOUND", "template_id": "abcdef12345"}')

        response = self.transloadit.get_template(id_)
        self.assertEqual(response.data["ok"], "TEMPLATE_FOUND")
        self.assertEqual(response.data["template_id"], "abcdef12345")

    @requests_mock.Mocker()
    def test_list_templates(self, mock):
        url = f"{self.transloadit.service}/templates"
        mock.get(url, text='{"items":[],"count":0}')

        response = self.transloadit.list_templates()
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["count"], 0)

    @requests_mock.Mocker()
    def test_update_template(self, mock):
        id_ = "abcdef12345"
        url = f"{self.transloadit.service}/templates/{id_}"
        sub_body = '"name": "foo_bar"'
        mock.put(
            url,
            text='{"ok": "TEMPLATE_UPDATED", "template_id": "abcdef12345"}',
            additional_matcher=request_body_matcher(urllib.parse.quote_plus(sub_body)),
        )

        response = self.transloadit.update_template(id_, {"name": "foo_bar"})
        self.assertEqual(response.data["ok"], "TEMPLATE_UPDATED")
        self.assertEqual(response.data["template_id"], "abcdef12345")

    @requests_mock.Mocker()
    def test_delete_tempalte(self, mock):
        id_ = "abcdef12345"
        url = f"{self.transloadit.service}/templates/{id_}"
        mock.delete(url, text='{"ok": "TEMPLATE_DELETED"}')

        response = self.transloadit.delete_template(id_)
        self.assertEqual(response.data["ok"], "TEMPLATE_DELETED")

    @requests_mock.Mocker()
    def test_get_bill(self, mock):
        year = 2017
        month = 9
        url = f"/bill/{year}-0{month}"
        mock.get(url, text='{"ok":"BILL_FOUND"}')

        response = self.transloadit.get_bill(month, year)
        self.assertEqual(response.data["ok"], "BILL_FOUND")

    def test_get_signed_smart_cdn_url(self):
        """Test Smart CDN URL signing with various scenarios."""
        client = Transloadit("test-key", "test-secret")

        # Test basic URL generation
        params = {
            'workspace': 'workspace',
            'template': 'template',
            'input': 'file.jpg',
            'auth_key': 'test-key',
            'auth_secret': 'test-secret',
            'expire_at_ms': self.expire_at_ms
        }

        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                {},
                3600 * 1000  # 1 hour
            )

        expected_url = 'https://workspace.tlcdn.com/template/file.jpg?auth_key=test-key&exp=1732550672867&sig=sha256%3Ad994b8a737db1c43d6e04a07018dc33e8e28b23b27854bd6383d828a212cfffb'
        self.assertEqual(url, expected_url, 'Basic URL should match expected')
        self.assert_parity_with_node(url, params)

        # Test with different input field
        params['input'] = 'input.jpg'
        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                {},
                3600 * 1000
            )

        expected_url = 'https://workspace.tlcdn.com/template/input.jpg?auth_key=test-key&exp=1732550672867&sig=sha256%3A75991f02828d194792c9c99f8fea65761bcc4c62dbb287a84f642033128297c0'
        self.assertEqual(url, expected_url, 'URL with different input should match expected')
        self.assert_parity_with_node(url, params)

        # Test with additional parameters
        params['input'] = 'file.jpg'
        params['url_params'] = {'width': 100}
        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                params['url_params'],
                3600 * 1000
            )

        expected_url = 'https://workspace.tlcdn.com/template/file.jpg?auth_key=test-key&exp=1732550672867&width=100&sig=sha256%3Ae5271d8fb6482d9351ebe4285b6fc75539c4d311ff125c4d76d690ad71c258ef'
        self.assertEqual(url, expected_url, 'URL with additional params should match expected')
        self.assert_parity_with_node(url, params)

        # Test with empty parameter string
        params['url_params'] = {'width': '', 'height': '200'}
        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                params['url_params'],
                3600 * 1000
            )

        expected_url = 'https://workspace.tlcdn.com/template/file.jpg?auth_key=test-key&exp=1732550672867&height=200&width=&sig=sha256%3A1a26733c859f070bc3d83eb3174650d7a0155642e44a5ac448a43bc728bc0f85'
        self.assertEqual(url, expected_url, 'URL with empty param should match expected')
        self.assert_parity_with_node(url, params)

        # Test with null parameter (should be excluded)
        params['url_params'] = {'width': None, 'height': '200'}
        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                params['url_params'],
                3600 * 1000
            )

        expected_url = 'https://workspace.tlcdn.com/template/file.jpg?auth_key=test-key&exp=1732550672867&height=200&sig=sha256%3Adb740ebdfad6e766ebf6516ed5ff6543174709f8916a254f8d069c1701cef517'
        self.assertEqual(url, expected_url, 'URL with null param should match expected')
        self.assert_parity_with_node(url, params)

        # Test with only empty parameter
        params['url_params'] = {'width': ''}
        with mock.patch('time.time', return_value=self.expire_at_ms/1000 - 3600):
            url = client.get_signed_smart_cdn_url(
                params['workspace'],
                params['template'],
                params['input'],
                params['url_params'],
                3600 * 1000
            )

        expected_url = 'https://workspace.tlcdn.com/template/file.jpg?auth_key=test-key&exp=1732550672867&width=&sig=sha256%3A840426f9ac72dde02fd080f09b2304d659fdd41e630b1036927ec1336c312e9d'
        self.assertEqual(url, expected_url, 'URL with only empty param should match expected')
        self.assert_parity_with_node(url, params)

        # Test default expiry (should be about 1 hour from now)
        params['url_params'] = {}
        del params['expire_at_ms']
        now = time.time()
        url = client.get_signed_smart_cdn_url(
            params['workspace'],
            params['template'],
            params['input']
        )

        import re
        match = re.search(r'exp=(\d+)', url)
        self.assertIsNotNone(match, 'URL should contain expiry timestamp')

        expiry = int(match.group(1))
        now_ms = int(now * 1000)
        one_hour = 60 * 60 * 1000

        self.assertGreater(expiry, now_ms, 'Expiry should be in the future')
        self.assertLess(expiry, now_ms + one_hour + 5000, 'Expiry should be about 1 hour from now')
        self.assertGreater(expiry, now_ms + one_hour - 5000, 'Expiry should be about 1 hour from now')

        # For parity test, set the exact expiry time to match Node.js
        params['expire_at_ms'] = expiry
        self.assert_parity_with_node(url, params)
