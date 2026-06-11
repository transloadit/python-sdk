import io
import unittest
from unittest import mock

import requests_mock

from . import request_body_matcher
from transloadit.client import Transloadit
from transloadit.response import Response


class AssemblyTest(unittest.TestCase):
    def setUp(self):
        self.transloadit = Transloadit("key", "secret")
        self.assembly = self.transloadit.new_assembly()
        self.json_response = (
            '{"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef45673"}'
        )

    def test_add_file(self):
        with open("LICENSE") as fs, open("README.md") as fs_2, open(
            "CHANGELOG.md"
        ) as fs_3:
            self.assembly.add_file(fs, "foo_field")

            self.assertEqual(self.assembly.files["foo_field"], fs)

            self.assembly.add_file(fs_2)
            self.assembly.add_file(fs_3)

            self.assertEqual(self.assembly.files["file"], fs_2)
            self.assertEqual(self.assembly.files["file_1"], fs_3)

    def test_remove_file(self):
        with open("LICENSE") as fs:
            self.assembly.add_file(fs, "foo_field")

            self.assertEqual(self.assembly.files["foo_field"], fs)

            self.assembly.remove_file("foo_field")
            self.assertIsNone(self.assembly.files.get("foo_field"))

    @requests_mock.Mocker()
    def test_save(self, mock):
        url = f"{self.transloadit.service}/assemblies"
        mock.post(
            url,
            text=self.json_response,
            additional_matcher=request_body_matcher(open("LICENSE").read()),
        )

        self.assembly.add_file(open("LICENSE"))
        assembly = self.assembly.create(resumable=False)
        self.assertEqual(assembly.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(assembly.data["assembly_id"], "abcdef45673")

    @requests_mock.Mocker()
    def test_save_resumable(self, mock):
        url = f"{self.transloadit.service}/assemblies"
        mock.post(
            url,
            text=self.json_response,
            additional_matcher=request_body_matcher("tus_num_expected_upload_files=0"),
        )

        assembly = self.assembly.create()
        self.assertEqual(assembly.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(assembly.data["assembly_id"], "abcdef45673")

    @requests_mock.Mocker()
    def test_save_resumable_uses_field_name_for_nameless_stream(self, mock_requests):
        url = f"{self.transloadit.service}/assemblies"
        mock_requests.post(
            url,
            text=(
                '{"ok":"ASSEMBLY_UPLOADING",'
                '"assembly_ssl_url":"https://api2.example/assemblies/abc",'
                '"tus_url":"https://api2.example/uploads"}'
            ),
        )
        upload = io.BytesIO(b"payload")
        self.assembly.add_file(upload, "payload_field")

        with mock.patch("transloadit.assembly.tus.TusClient") as tus_client:
            uploader = tus_client.return_value.uploader.return_value
            assembly = self.assembly.create(resumable=True)

        self.assertEqual(assembly.data["ok"], "ASSEMBLY_UPLOADING")
        tus_client.return_value.uploader.assert_called_once()
        self.assertEqual(
            tus_client.return_value.uploader.call_args.kwargs["metadata"]["filename"],
            "payload_field",
        )
        uploader.upload.assert_called_once()

    def test_save_resumable_retries_rate_limit_before_tus_upload(self):
        rate_limited = Response(
            data={
                "error": "RATE_LIMIT_REACHED",
                "info": {"retryIn": 0},
            },
            status_code=200,
            headers={},
        )
        success = Response(
            data={
                "ok": "ASSEMBLY_UPLOADING",
                "assembly_ssl_url": "https://api2.example/assemblies/abc",
                "tus_url": "https://api2.example/uploads",
            },
            status_code=200,
            headers={},
        )
        self.assembly.add_file(io.BytesIO(b"payload"), "payload_field")

        with mock.patch.object(
            self.transloadit.request,
            "post",
            side_effect=[rate_limited, success],
        ) as post_mock:
            with mock.patch("transloadit.assembly.tus.TusClient") as tus_client:
                uploader = tus_client.return_value.uploader.return_value
                assembly = self.assembly.create(resumable=True, retries=1)

        self.assertEqual(assembly.data["ok"], "ASSEMBLY_UPLOADING")
        self.assertEqual(post_mock.call_count, 2)
        tus_client.assert_called_once_with("https://api2.example/uploads")
        self.assertEqual(
            tus_client.return_value.uploader.call_args.kwargs["metadata"]["assembly_url"],
            "https://api2.example/assemblies/abc",
        )
        uploader.upload.assert_called_once()

    def test_save_non_resumable_rewinds_seekable_files_before_retry(self):
        upload = io.BytesIO(b"payload")
        rate_limited = Response(
            data={
                "error": "RATE_LIMIT_REACHED",
                "info": {"retryIn": 0},
            },
            status_code=200,
            headers={},
        )
        success = Response(
            data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef45673"},
            status_code=200,
            headers={},
        )
        seen_positions = []
        self.assembly.add_file(upload, "payload_field")

        def post_side_effect(*args, **kwargs):
            seen_positions.append(kwargs["files"]["payload_field"].tell())
            kwargs["files"]["payload_field"].seek(0, io.SEEK_END)
            return rate_limited if len(seen_positions) == 1 else success

        with mock.patch.object(self.transloadit.request, "post", side_effect=post_side_effect):
            with mock.patch("transloadit.assembly.sleep"):
                assembly = self.assembly.create(resumable=False, retries=1)

        self.assertEqual(assembly.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(seen_positions, [0, 0])

    def test_save_non_resumable_rejects_non_seekable_file_retry(self):
        class NonSeekableFile:
            pass

        rate_limited = Response(
            data={
                "error": "RATE_LIMIT_REACHED",
                "info": {"retryIn": 0},
            },
            status_code=200,
            headers={},
        )
        self.assembly.add_file(NonSeekableFile(), "payload_field")

        with mock.patch.object(self.transloadit.request, "post", return_value=rate_limited):
            with self.assertRaises(RuntimeError):
                self.assembly.create(resumable=False, retries=1)

    def test_save_wait_raises_on_plain_text_create_response(self):
        plain_response = Response(
            data="plain assembly response",
            status_code=502,
            headers={"X-Route": "plain"},
        )

        with mock.patch.object(self.transloadit.request, "post", return_value=plain_response):
            with self.assertRaises(RuntimeError):
                self.assembly.create(wait=True, resumable=False)

    def test_save_returns_plain_text_success_without_wait(self):
        plain_response = Response(
            data="plain assembly response",
            status_code=200,
            headers={"X-Route": "plain"},
        )

        with mock.patch.object(self.transloadit.request, "post", return_value=plain_response):
            response = self.assembly.create(wait=False, resumable=False)

        self.assertIs(response, plain_response)

    def test_save_resumable_plain_text_response_raises_before_tus_upload(self):
        plain_response = Response(
            data="plain assembly response",
            status_code=200,
            headers={"X-Route": "plain"},
        )
        self.assembly.add_file(io.BytesIO(b"payload"), "payload_field")

        with mock.patch.object(self.transloadit.request, "post", return_value=plain_response):
            with mock.patch("transloadit.assembly.tus.TusClient") as tus_client:
                with self.assertRaises(RuntimeError):
                    self.assembly.create(resumable=True)

        tus_client.assert_not_called()

    def test_save_wait_pins_assembly_url_across_poll_rate_limits(self):
        initial_response = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": "https://api2.example/assemblies/abc",
            },
            status_code=200,
            headers={},
        )
        rate_limited = Response(
            data={
                "error": "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
                "info": {"retryIn": 0},
            },
            status_code=200,
            headers={},
        )
        completed = Response(
            data={
                "ok": "ASSEMBLY_COMPLETED",
                "assembly_ssl_url": "https://api2.example/assemblies/other",
            },
            status_code=200,
            headers={},
        )

        with mock.patch.object(self.transloadit.request, "post", return_value=initial_response):
            with mock.patch.object(
                self.transloadit,
                "get_assembly",
                side_effect=[rate_limited, completed],
            ) as get_mock:
                with mock.patch("transloadit.assembly.sleep"):
                    response = self.assembly.create(wait=True, resumable=False, retries=2)

        self.assertIs(response, completed)
        self.assertEqual(
            get_mock.call_args_list,
            [
                mock.call(assembly_url="https://api2.example/assemblies/abc"),
                mock.call(assembly_url="https://api2.example/assemblies/abc"),
            ],
        )

    def test_save_wait_does_not_follow_poll_response_assembly_url(self):
        initial_response = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": "https://api2.example/assemblies/abc",
            },
            status_code=200,
            headers={},
        )
        redirected_processing = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": "https://example.invalid/assemblies/evil",
            },
            status_code=200,
            headers={},
        )
        completed = Response(
            data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "abcdef45673"},
            status_code=200,
            headers={},
        )

        with mock.patch.object(self.transloadit.request, "post", return_value=initial_response):
            with mock.patch.object(
                self.transloadit,
                "get_assembly",
                side_effect=[redirected_processing, completed],
            ) as get_mock:
                with mock.patch("transloadit.assembly.sleep"):
                    response = self.assembly.create(wait=True, resumable=False, retries=2)

        self.assertIs(response, completed)
        self.assertEqual(
            get_mock.call_args_list,
            [
                mock.call(assembly_url="https://api2.example/assemblies/abc"),
                mock.call(assembly_url="https://api2.example/assemblies/abc"),
            ],
        )

    def test_save_wait_caps_poll_rate_limit_retries(self):
        initial_response = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": "https://api2.example/assemblies/abc",
            },
            status_code=200,
            headers={},
        )
        rate_limited = Response(
            data={
                "error": "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
                "info": {"retryIn": 0},
            },
            status_code=200,
            headers={},
        )

        with mock.patch.object(self.transloadit.request, "post", return_value=initial_response):
            with mock.patch.object(
                self.transloadit,
                "get_assembly",
                return_value=rate_limited,
            ) as get_mock:
                with mock.patch("transloadit.assembly.sleep"):
                    response = self.assembly.create(wait=True, resumable=False, retries=1)

        self.assertIs(response, rate_limited)
        self.assertEqual(get_mock.call_count, 2)
