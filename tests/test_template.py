import unittest

import requests_mock
from six.moves import urllib

from . import request_body_matcher
from transloadit.client import Transloadit


class TemplateTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit('key', 'secret')
        self.template = self.transloadit.new_template('foo')

    @requests_mock.Mocker()
    def test_save(self, mock):
        url = '{}/templates'.format(self.transloadit.host)
        sub_body = '"robot": "/image/resize"'
        mock.post(url, text='{"ok":"TEMPLATE_CREATED","template_name":"foo"}',
                  additional_matcher=request_body_matcher(urllib.parse.quote_plus(sub_body)))

        self.template.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
        template = self.template.save()
        self.assertEqual(template.data['ok'], "TEMPLATE_CREATED")
        self.assertEqual(template.data['template_name'], "foo")
