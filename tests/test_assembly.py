import unittest

import requests_mock

from . import request_body_matcher
from transloadit.client import Transloadit


class AssemblyTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit('key', 'secret')
        self.assembly = self.transloadit.new_assembly()
        self.json_response = '{"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef45673"}'

    def test_add_file(self):
        with open('LICENSE') as fs, open('README.md') as fs_2, open('requirements.txt') as fs_3:
            self.assembly.add_file(fs, 'foo_field')

            self.assertEqual(self.assembly.files['foo_field'], fs)

            self.assembly.add_file(fs_2)
            self.assembly.add_file(fs_3)

            self.assertEqual(self.assembly.files['file'], fs_2)
            self.assertEqual(self.assembly.files['file_1'], fs_3)

    def test_remove_file(self):
        with open('LICENSE') as fs:
            self.assembly.add_file(fs, 'foo_field')

            self.assertEqual(self.assembly.files['foo_field'], fs)

            self.assembly.remove_file('foo_field')
            self.assertIsNone(self.assembly.files.get('foo_field'))

    @requests_mock.Mocker()
    def test_save(self, mock):
        url = '{}/assemblies'.format(self.transloadit.service)
        mock.post(url, text=self.json_response,
                  additional_matcher=request_body_matcher(open('LICENSE').read()))

        self.assembly.add_file(open('LICENSE'))
        assembly = self.assembly.create(resumable=False)
        self.assertEqual(assembly.data['ok'], "ASSEMBLY_COMPLETED")
        self.assertEqual(assembly.data['assembly_id'], "abcdef45673")

    @requests_mock.Mocker()
    def test_save_resumable(self, mock):
        url = '{}/assemblies'.format(self.transloadit.service)
        mock.post(url, text=self.json_response,
                  additional_matcher=request_body_matcher('tus_num_expected_upload_files=0'))

        assembly = self.assembly.create()
        self.assertEqual(assembly.data['ok'], "ASSEMBLY_COMPLETED")
        self.assertEqual(assembly.data['assembly_id'], "abcdef45673")
