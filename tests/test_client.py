import unittest

import requests_mock
from six.moves import urllib

from . import request_body_matcher
from transloadit.client import Transloadit


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit('key', 'secret')

    @requests_mock.Mocker()
    def test_get_assembly(self, mock):
        id_ = 'abcdef12345'
        url = '{}/assemblies/{}'.format(self.transloadit.host, id_)
        mock.get(url, text='{"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef12345"}')

        response = self.transloadit.get_assembly(assembly_id=id_)
        self.assertEqual(response.data['ok'], 'ASSEMBLY_COMPLETED')
        self.assertEqual(response.data['assembly_id'], 'abcdef12345')

    @requests_mock.Mocker()
    def test_list_assemblies(self, mock):
        url = '{}/assemblies'.format(self.transloadit.host)
        mock.get(url, text='{"items":[],"count":0}')

        response = self.transloadit.list_assemblies()
        self.assertEqual(response.data['items'], [])
        self.assertEqual(response.data['count'], 0)

    @requests_mock.Mocker()
    def test_cancel_assembly(self, mock):
        id_ = 'abcdef12345'
        url = '{}/assemblies/{}'.format(self.transloadit.host, id_)
        mock.delete(url, text='{"ok": "ASSEMBLY_CANCELED", "assembly_id": "abcdef12345"}')

        response = self.transloadit.cancel_assembly(id_)
        self.assertEqual(response.data['ok'], 'ASSEMBLY_CANCELED')
        self.assertEqual(response.data['assembly_id'], 'abcdef12345')

    @requests_mock.Mocker()
    def test_get_template(self, mock):
        id_ = 'abcdef12345'
        url = '{}/templates/{}'.format(self.transloadit.host, id_)
        mock.get(url, text='{"ok": "TEMPLATE_FOUND", "template_id": "abcdef12345"}')

        response = self.transloadit.get_template(id_)
        self.assertEqual(response.data['ok'], 'TEMPLATE_FOUND')
        self.assertEqual(response.data['template_id'], 'abcdef12345')

    @requests_mock.Mocker()
    def test_list_templates(self, mock):
        url = '{}/templates'.format(self.transloadit.host)
        mock.get(url, text='{"items":[],"count":0}')

        response = self.transloadit.list_templates()
        self.assertEqual(response.data['items'], [])
        self.assertEqual(response.data['count'], 0)

    @requests_mock.Mocker()
    def test_update_template(self, mock):
        id_ = 'abcdef12345'
        url = '{}/templates/{}'.format(self.transloadit.host, id_)
        sub_body = '"name": "foo_bar"'
        mock.put(url, text='{"ok": "TEMPLATE_UPDATED", "template_id": "abcdef12345"}',
                 additional_matcher=request_body_matcher(urllib.parse.quote_plus(sub_body)))

        response = self.transloadit.update_template(id_, {'name': 'foo_bar'})
        self.assertEqual(response.data['ok'], 'TEMPLATE_UPDATED')
        self.assertEqual(response.data['template_id'], 'abcdef12345')

    @requests_mock.Mocker()
    def test_delete_tempalte(self, mock):
        id_ = 'abcdef12345'
        url = '{}/templates/{}'.format(self.transloadit.host, id_)
        mock.delete(url, text='{"ok": "TEMPLATE_DELETED"}')

        response = self.transloadit.delete_template(id_)
        self.assertEqual(response.data['ok'], 'TEMPLATE_DELETED')

    @requests_mock.Mocker()
    def test_get_bill(self, mock):
        year = 2017
        month = 9
        url = '/bill/{}-0{}'.format(year, month)
        mock.get(url, text='{"ok":"BILL_FOUND"}')

        response = self.transloadit.get_bill(month, year)
        self.assertEqual(response.data['ok'], 'BILL_FOUND')
