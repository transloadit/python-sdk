import asyncio
import io
import json
import threading
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, mock

from aiohttp import payload, web

from transloadit.async_client import AsyncTransloadit
from transloadit.async_request import _NonClosingUploadStream
from transloadit.client import Transloadit
from transloadit.response import Response


class _AsyncApiServer:
    def __init__(self):
        self.requests = []
        self.app = web.Application()
        self.app.router.add_get("/assemblies/{assembly_id}", self.handle_get_assembly)
        self.app.router.add_get("/assemblies-text/{assembly_id}", self.handle_get_assembly_text)
        self.app.router.add_get("/assemblies-plain/{assembly_id}", self.handle_get_assembly_plain)
        self.app.router.add_get("/assemblies", self.handle_list_assemblies)
        self.app.router.add_delete("/assemblies/{assembly_id}", self.handle_cancel_assembly)
        self.app.router.add_get("/templates/{template_id}", self.handle_get_template)
        self.app.router.add_delete("/templates/{template_id}", self.handle_delete_template)
        self.app.router.add_get("/templates", self.handle_list_templates)
        self.app.router.add_put("/templates/{template_id}", self.handle_update_template)
        self.app.router.add_post("/templates", self.handle_create_template)
        self.app.router.add_get("/bill/{year}-{month}", self.handle_get_bill)
        self.app.router.add_post("/assemblies", self.handle_create_assembly)
        self.runner = None
        self.site = None
        self.base_url = None

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()

        sock = self.site._server.sockets[0]
        host, port = sock.getsockname()[:2]
        self.base_url = f"http://{host}:{port}"
        return self

    async def close(self):
        if self.runner is not None:
            await self.runner.cleanup()

    def _record(self, request, body=None):
        entry = {
            "method": request.method,
            "path": request.path,
            "query": dict(request.query),
            "headers": dict(request.headers),
        }
        if body is not None:
            entry["body"] = body
        self.requests.append(entry)
        return entry

    async def _parse_body(self, request):
        post = await request.post()
        body = {}
        for key, value in post.items():
            if hasattr(value, "filename") and hasattr(value, "file"):
                value.file.seek(0)
                body[key] = {
                    "filename": value.filename,
                    "content": value.file.read(),
                    "content_type": value.content_type,
                }
            else:
                body[key] = value
        return body

    async def handle_get_assembly(self, request):
        self._record(request)
        return web.json_response(
            {
                "ok": "ASSEMBLY_COMPLETED",
                "assembly_id": request.match_info["assembly_id"],
            },
            headers={"X-Async-Route": "get_assembly"},
        )

    async def handle_get_assembly_text(self, request):
        self._record(request)
        payload = {
            "ok": "ASSEMBLY_COMPLETED",
            "assembly_id": request.match_info["assembly_id"],
        }
        return web.Response(
            text=json.dumps(payload),
            content_type="text/plain",
            headers={"X-Async-Route": "get_assembly_text"},
        )

    async def handle_get_assembly_plain(self, request):
        self._record(request)
        return web.Response(
            text="plain assembly response",
            content_type="text/plain",
            headers={"X-Async-Route": "get_assembly_plain"},
        )

    async def handle_list_assemblies(self, request):
        self._record(request)
        return web.json_response(
            {"items": [], "count": 0},
            headers={"X-Async-Route": "list_assemblies"},
        )

    async def handle_cancel_assembly(self, request):
        self._record(request)
        return web.json_response(
            {
                "ok": "ASSEMBLY_CANCELED",
                "assembly_id": request.match_info["assembly_id"],
            },
            headers={"X-Async-Route": "cancel_assembly"},
        )

    async def handle_get_template(self, request):
        self._record(request)
        return web.json_response(
            {
                "ok": "TEMPLATE_FOUND",
                "template_id": request.match_info["template_id"],
            },
            headers={"X-Async-Route": "get_template"},
        )

    async def handle_delete_template(self, request):
        self._record(request)
        return web.json_response(
            {
                "ok": "TEMPLATE_DELETED",
                "template_id": request.match_info["template_id"],
            },
            headers={"X-Async-Route": "delete_template"},
        )

    async def handle_list_templates(self, request):
        self._record(request)
        return web.json_response(
            {"items": [{"template_id": "tpl-1"}], "count": 1},
            headers={"X-Async-Route": "list_templates"},
        )

    async def handle_update_template(self, request):
        body = await self._parse_body(request)
        self._record(request, body)
        return web.json_response(
            {
                "ok": "TEMPLATE_UPDATED",
                "template_id": request.match_info["template_id"],
            },
            headers={"X-Async-Route": "update_template"},
        )

    async def handle_create_template(self, request):
        body = await self._parse_body(request)
        self._record(request, body)
        params = json.loads(body["params"])
        return web.json_response(
            {
                "ok": "TEMPLATE_CREATED",
                "template_name": params["name"],
            },
            headers={"X-Async-Route": "create_template"},
        )

    async def handle_get_bill(self, request):
        self._record(request)
        return web.json_response(
            {
                "ok": "BILL_FOUND",
                "period": f"{request.match_info['year']}-{request.match_info['month']}",
            },
            headers={"X-Async-Route": "get_bill"},
        )

    async def handle_create_assembly(self, request):
        body = await self._parse_body(request)
        self._record(request, body)
        return web.json_response(
            {
                "ok": "ASSEMBLY_COMPLETED",
                "assembly_id": "assembly-123",
                "assembly_ssl_url": f"{self.base_url}/assemblies/assembly-123",
                "tus_url": f"{self.base_url}/uploads",
            },
            headers={"X-Async-Route": "create_assembly"},
        )


class _FakeResponseContext:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200
        self.headers = {"X-Async-Route": "fake"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, **kwargs):
        return self.payload

    async def text(self):
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload)


class _UndecodableResponse:
    async def json(self, **kwargs):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    async def text(self):
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    async def read(self):
        return b"\xff"


class _RecordingSession:
    def __init__(self, payload):
        self.calls = []
        self.closed = False
        self.payload = payload

    def delete(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponseContext(self.payload)

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponseContext(self.payload)

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponseContext(self.payload)

    def put(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponseContext(self.payload)

    async def close(self):
        self.closed = True


class _NeverOwnedSession:
    def __init__(self):
        self.closed = False
        self.close_calls = 0

    async def close(self):
        self.close_calls += 1
        self.closed = True


class _BrokenStream:
    def __init__(self, name="broken.bin"):
        self.name = name

    def tell(self):
        raise OSError("tell failed")

    def seek(self, position):
        raise OSError("seek failed")


class AsyncClientTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = await _AsyncApiServer().start()

    async def asyncTearDown(self):
        await self.server.close()

    async def test_async_client_methods_and_context_manager(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            response = await client.get_assembly(assembly_id="abc123")
            self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
            self.assertEqual(response.data["assembly_id"], "abc123")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["X-Async-Route"], "get_assembly")
            self.assertEqual(response.headers["x-async-route"], "get_assembly")

            response = await client.list_assemblies()
            self.assertEqual(response.data["items"], [])
            self.assertEqual(response.data["count"], 0)
            self.assertEqual(response.headers["X-Async-Route"], "list_assemblies")

            response = await client.cancel_assembly(assembly_id="abc123")
            self.assertEqual(response.data["ok"], "ASSEMBLY_CANCELED")
            self.assertEqual(response.data["assembly_id"], "abc123")

            response = await client.get_template("tpl-1")
            self.assertEqual(response.data["ok"], "TEMPLATE_FOUND")
            self.assertEqual(response.data["template_id"], "tpl-1")

            response = await client.list_templates()
            self.assertEqual(response.data["items"], [{"template_id": "tpl-1"}])
            self.assertEqual(response.data["count"], 1)

            response = await client.update_template("tpl-1", {"name": "foo_bar"})
            self.assertEqual(response.data["ok"], "TEMPLATE_UPDATED")
            self.assertEqual(response.data["template_id"], "tpl-1")

            template = client.new_template("foo")
            template.add_step("resize", "/image/resize", {"width": 70, "height": 70})
            response = await template.create()
            self.assertEqual(response.data["ok"], "TEMPLATE_CREATED")
            self.assertEqual(response.data["template_name"], "foo")

        self.assertIsNone(client.request.session)

        self.assertGreaterEqual(len(self.server.requests), 7)
        first_request = self.server.requests[0]
        self.assertEqual(first_request["method"], "GET")
        self.assertEqual(first_request["path"], "/assemblies/abc123")

        update_request = next(
            entry for entry in self.server.requests if entry["path"] == "/templates/tpl-1" and entry["method"] == "PUT"
        )
        update_params = json.loads(update_request["body"]["params"])
        self.assertEqual(update_params["name"], "foo_bar")

        create_request = next(
            entry for entry in self.server.requests if entry["path"] == "/templates" and entry["method"] == "POST"
        )
        create_params = json.loads(create_request["body"]["params"])
        self.assertEqual(create_params["name"], "foo")
        self.assertEqual(create_params["template"]["steps"]["resize"]["robot"], "/image/resize")

    async def test_async_client_accepts_json_with_text_content_type(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            response = await client.get_assembly(
                assembly_url=f"{self.server.base_url}/assemblies-text/abc123"
            )

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(response.data["assembly_id"], "abc123")
        self.assertEqual(response.headers["X-Async-Route"], "get_assembly_text")

    async def test_async_client_normalizes_service_and_rejects_missing_ids(self):
        session = _NeverOwnedSession()
        client = AsyncTransloadit(
            "key",
            "secret",
            service="api2.transloadit.com",
            session=session,
        )

        self.assertEqual(client.service, "https://api2.transloadit.com")

        for service in ("", "   ", "https://", "ftp://api2.transloadit.com"):
            with self.assertRaises(ValueError):
                AsyncTransloadit("key", "secret", service=service, session=session)

        with self.assertRaises(ValueError):
            await client.get_assembly()

        with self.assertRaises(ValueError):
            await client.cancel_assembly()

        external_session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        external_client = AsyncTransloadit(
            "key",
            "secret",
            service="https://api2.transloadit.com",
            session=external_session,
        )
        await external_client.get_assembly(assembly_url="https://example.com/assemblies/abc123")
        await external_client.cancel_assembly(assembly_url="https://example.com/assemblies/abc123")
        self.assertEqual(
            [call[0] for call in external_session.calls],
            [
                "https://example.com/assemblies/abc123",
                "https://example.com/assemblies/abc123",
            ],
        )
        self.assertIsNone(external_session.calls[0][1]["params"])
        self.assertEqual(external_session.calls[1][1]["data"], [])

        transloadit_session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        transloadit_client = AsyncTransloadit(
            "key",
            "secret",
            service="https://api2.transloadit.com",
            session=transloadit_session,
        )
        await transloadit_client.get_assembly(
            assembly_url="https://api2-region.transloadit.com/assemblies/abc123"
        )
        self.assertEqual(
            transloadit_session.calls[0][0],
            "https://api2-region.transloadit.com/assemblies/abc123",
        )
        self.assertIn("signature", transloadit_session.calls[0][1]["params"])

        await client.close()

        self.assertFalse(session.closed)
        self.assertEqual(session.close_calls, 0)

        closed_session = _NeverOwnedSession()
        closed_session.closed = True
        closed_client = AsyncTransloadit(
            "key",
            "secret",
            service=self.server.base_url,
            session=closed_session,
        )

        with self.assertRaises(RuntimeError):
            await closed_client.get_assembly(assembly_id="abc123")

    async def test_async_client_quotes_path_ids(self):
        session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)

        await client.get_assembly(assembly_id="assembly/with?chars")
        await client.cancel_assembly(assembly_id="cancel/with?chars")
        await client.get_template("template/with?chars")
        await client.update_template("update/with?chars", {"name": "foo"})
        await client.delete_template("delete/with?chars")

        urls = [call[0] for call in session.calls]
        self.assertEqual(
            urls,
            [
                f"{self.server.base_url}/assemblies/assembly%2Fwith%3Fchars",
                f"{self.server.base_url}/assemblies/cancel%2Fwith%3Fchars",
                f"{self.server.base_url}/templates/template%2Fwith%3Fchars",
                f"{self.server.base_url}/templates/update%2Fwith%3Fchars",
                f"{self.server.base_url}/templates/delete%2Fwith%3Fchars",
            ],
        )

    async def test_async_client_rejects_empty_template_ids(self):
        session = _RecordingSession({"ok": "TEMPLATE_FOUND"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)

        for template_id in ("", None):
            with self.assertRaises(ValueError):
                await client.get_template(template_id)
            with self.assertRaises(ValueError):
                await client.update_template(template_id, {"name": "foo"})
            with self.assertRaises(ValueError):
                await client.delete_template(template_id)

        self.assertEqual(session.calls, [])

    async def test_async_generated_endpoint_methods_call_request_helpers(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)
        response = Response(data={"ok": "OK"}, status_code=200, headers={})
        assembly_data = {"steps": {":original": {"robot": "/upload/handle"}}}
        extra_data = {"field": "value"}
        files = {"file": io.BytesIO(b"payload")}
        replay_data = {"wait": True}
        credential_data = {"name": "demo", "type": "s3", "content": {}}

        get_mock = mock.AsyncMock(return_value=response)
        post_mock = mock.AsyncMock(return_value=response)
        put_mock = mock.AsyncMock(return_value=response)
        delete_mock = mock.AsyncMock(return_value=response)

        with mock.patch.object(client.request, "get", new=get_mock):
            with mock.patch.object(client.request, "post", new=post_mock):
                with mock.patch.object(client.request, "put", new=put_mock):
                    with mock.patch.object(client.request, "delete", new=delete_mock):
                        await client.create_assembly(assembly_data, extra_data, files)
                        await client.create_assembly_with_id(
                            "assembly/with?chars", assembly_data, extra_data, files
                        )
                        await client.replay_assembly("assembly/with?chars", replay_data)
                        await client.replay_assembly_notification(
                            "assembly/with?chars", replay_data
                        )
                        await client.create_template({"name": "template"})
                        await client.validate_template_credential_oauth_on_create(
                            {"type": "dropbox"}
                        )
                        await client.create_template_credentials(credential_data)
                        await client.list_assembly_notifications("assembly/with?chars")
                        await client.get_builtin_template("builtin/with?chars")
                        await client.get_template_full("template/with?chars")
                        await client.get_builtin_template_full("builtin/full?chars")
                        await client.list_priority_job_slots()
                        await client.list_template_credentials()
                        await client.list_template_credential_types()
                        await client.get_template_credentials("cred/with?chars")
                        await client.update_template_credentials("cred/with?chars", credential_data)
                        await client.delete_template_credentials("cred/with?chars")

        self.assertEqual(
            post_mock.await_args_list,
            [
                mock.call(
                    "/assemblies",
                    data=assembly_data,
                    extra_data=extra_data,
                    files=files,
                ),
                mock.call(
                    "/assemblies/assembly%2Fwith%3Fchars",
                    data=assembly_data,
                    extra_data=extra_data,
                    files=files,
                ),
                mock.call("/assemblies/assembly%2Fwith%3Fchars/replay", data=replay_data),
                mock.call(
                    "/assembly_notifications/assembly%2Fwith%3Fchars/replay",
                    data=replay_data,
                ),
                mock.call("/templates", data={"name": "template"}),
                mock.call("/template_credentials/validateOauthOnCreate", data={"type": "dropbox"}),
                mock.call("/template_credentials", data=credential_data),
            ],
        )
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call("/assembly_notifications/assembly%2Fwith%3Fchars"),
                mock.call("/templates/builtin/builtin%2Fwith%3Fchars"),
                mock.call("/templates/template%2Fwith%3Fchars/full"),
                mock.call("/templates/builtin/builtin%2Ffull%3Fchars/full"),
                mock.call("/queues/job_slots"),
                mock.call("/template_credentials"),
                mock.call("/template_credentials/types"),
                mock.call("/template_credentials/cred%2Fwith%3Fchars"),
            ],
        )
        put_mock.assert_awaited_once_with(
            "/template_credentials/cred%2Fwith%3Fchars", data=credential_data
        )
        delete_mock.assert_awaited_once_with("/template_credentials/cred%2Fwith%3Fchars")

    async def test_async_generated_endpoint_methods_reject_empty_path_ids(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)
        methods = [
            client.create_assembly_with_id,
            client.replay_assembly,
            client.replay_assembly_notification,
            client.list_assembly_notifications,
            client.get_builtin_template,
            client.get_template_full,
            client.get_builtin_template_full,
            client.get_template_credentials,
            client.delete_template_credentials,
            client.update_template_credentials,
        ]

        for method in methods:
            with self.assertRaises(ValueError):
                await method("")

    async def test_async_client_close_reopens_owned_session(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)

        first_session = await client.request._ensure_session()
        self.assertFalse(first_session.closed)

        await client.close()
        self.assertTrue(first_session.closed)
        self.assertIsNone(client.request.session)

        second_session = await client.request._ensure_session()
        self.assertIsNot(first_session, second_session)
        self.assertFalse(second_session.closed)

        await client.close()

    async def test_async_request_owned_sessions_trust_environment(self):
        session = _NeverOwnedSession()
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)

        with mock.patch("aiohttp.ClientSession", return_value=session) as session_mock:
            ensured_session = await client.request._ensure_session()

        self.assertIs(ensured_session, session)
        session_mock.assert_called_once_with(trust_env=True)

        await client.close()

    async def test_async_client_reopens_owned_session_when_session_is_closed(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)

        first_session = await client.request._ensure_session()
        self.assertFalse(first_session.closed)

        await first_session.close()
        reopened_session = await client.request._ensure_session()

        self.assertIsNot(first_session, reopened_session)
        self.assertFalse(reopened_session.closed)

        await client.close()

    async def test_async_client_delete_template_get_bill_and_plain_text_fallback(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            response = await client.delete_template("tpl-1")
            self.assertEqual(response.data["ok"], "TEMPLATE_DELETED")
            self.assertEqual(response.data["template_id"], "tpl-1")
            self.assertEqual(response.headers["X-Async-Route"], "delete_template")

            response = await client.get_bill(9, 2017)
            self.assertEqual(response.data["ok"], "BILL_FOUND")
            self.assertEqual(response.data["period"], "2017-09")
            self.assertEqual(response.headers["X-Async-Route"], "get_bill")

            response = await client.get_assembly(
                assembly_url=f"{self.server.base_url}/assemblies-plain/abc123"
            )

        self.assertEqual(response.data, "plain assembly response")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Async-Route"], "get_assembly_plain")

    async def test_async_request_falls_back_to_bytes_when_text_decode_fails(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)

        data = await client.request._read_response_data(_UndecodableResponse())

        self.assertEqual(data, b"\xff")

    async def test_async_assembly_create_raises_on_plain_text_error_response(self):
        plain_response = Response(
            data="plain assembly response",
            status_code=502,
            headers={"X-Async-Route": "plain"},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=plain_response)) as post_mock:
                with self.assertRaises(RuntimeError):
                    await assembly.create(wait=True, resumable=False)

        post_mock.assert_awaited_once()

    async def test_async_assembly_create_returns_plain_text_success_response(self):
        plain_response = Response(
            data="plain assembly response",
            status_code=200,
            headers={"X-Async-Route": "plain"},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=plain_response)) as post_mock:
                response = await assembly.create(wait=False, resumable=False)

        self.assertIs(response, plain_response)
        post_mock.assert_awaited_once()

    async def test_async_assembly_resumable_plain_text_success_response_raises_before_tus_upload(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                raise AssertionError("TUS upload should not start without upload URLs")

        plain_response = Response(
            data="plain assembly response",
            status_code=200,
            headers={"X-Async-Route": "plain"},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=plain_response)) as post_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    with self.assertRaises(RuntimeError):
                        await assembly.create(resumable=True)

        post_mock.assert_awaited_once()
        self.assertEqual(calls, [])

    async def test_async_assembly_wait_raises_on_plain_text_poll_response(self):
        initial_response = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
            },
            status_code=200,
            headers={"X-Async-Route": "initial"},
        )
        plain_response = Response(
            data="plain assembly response",
            status_code=502,
            headers={"X-Async-Route": "plain"},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial_response)) as post_mock:
                with mock.patch.object(client, "get_assembly", new=mock.AsyncMock(return_value=plain_response)) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        with self.assertRaises(RuntimeError):
                            await assembly.create(wait=True, resumable=False)

        post_mock.assert_awaited_once()
        get_mock.assert_awaited_once_with(
            assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
        )
        sleep_mock.assert_awaited_once_with(0)

    async def test_async_assembly_wait_raises_on_plain_text_success_poll_response(self):
        initial_response = Response(
            data={
                "ok": "ASSEMBLY_PROCESSING",
                "info": {"retryIn": 0},
                "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
            },
            status_code=200,
            headers={"X-Async-Route": "initial"},
        )
        plain_response = Response(
            data="plain assembly response",
            status_code=200,
            headers={"X-Async-Route": "plain"},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial_response)) as post_mock:
                with mock.patch.object(client, "get_assembly", new=mock.AsyncMock(return_value=plain_response)) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        with self.assertRaises(RuntimeError):
                            await assembly.create(wait=True, resumable=False)

        post_mock.assert_awaited_once()
        get_mock.assert_awaited_once_with(
            assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
        )
        sleep_mock.assert_awaited_once_with(0)

    async def test_async_wait_for_assembly_polls_until_terminal(self):
        responses = [
            Response(data={"ok": "ASSEMBLY_UPLOADING"}, status_code=200),
            Response(data={"ok": "ASSEMBLY_EXECUTING"}, status_code=200),
            Response(data={"ok": "ASSEMBLY_COMPLETED"}, status_code=200),
        ]
        assembly_url = f"{self.server.base_url}/assemblies/assembly-123"

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            with mock.patch.object(
                client,
                "get_assembly",
                new=mock.AsyncMock(side_effect=responses),
            ) as get_mock:
                with mock.patch(
                    "transloadit.async_client.asyncio.sleep",
                    new_callable=mock.AsyncMock,
                ) as sleep_mock:
                    response = await client.wait_for_assembly(assembly_url)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call(assembly_url=assembly_url),
                mock.call(assembly_url=assembly_url),
                mock.call(assembly_url=assembly_url),
            ],
        )
        self.assertEqual(sleep_mock.await_args_list, [mock.call(1), mock.call(1)])

    async def test_async_wait_for_assembly_rejects_non_json_poll_response(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            with mock.patch.object(
                client,
                "get_assembly",
                new=mock.AsyncMock(return_value=Response(data="plain response", status_code=502)),
            ):
                with self.assertRaises(RuntimeError):
                    await client.wait_for_assembly(
                        f"{self.server.base_url}/assemblies/assembly-123"
                    )

    def test_async_signed_smart_cdn_url_matches_sync_and_rejects_bad_types(self):
        async_client = AsyncTransloadit("test-key", "test-secret")
        sync_client = Transloadit("test-key", "test-secret")
        params = {"width": 100, "tags": ["a", "b"], "enabled": True, "flags": [True, False], "skip": None}

        with mock.patch("time.time", return_value=1732550672.867):
            async_url = async_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
                params,
            )
            explicit_async_url = async_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
                params,
                expires_at_ms=1732550672867,
            )
            sync_url = sync_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
                params,
            )
            explicit_sync_url = sync_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
                params,
                expires_at_ms=1732550672867,
            )
            bare_async_url = async_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
            )
            bare_sync_url = sync_client.get_signed_smart_cdn_url(
                "acme-workspace",
                "My Template",
                "folder/file name.jpg",
            )

        self.assertEqual(async_url, sync_url)
        self.assertEqual(explicit_async_url, explicit_sync_url)
        self.assertEqual(bare_async_url, bare_sync_url)
        self.assertIn("auth_key=test-key", async_url)
        self.assertIn("exp=1732554272867", async_url)
        self.assertIn("width=100", async_url)
        self.assertIn("tags=a", async_url)
        self.assertIn("tags=b", async_url)
        self.assertIn("enabled=true", async_url)
        self.assertIn("flags=true", async_url)
        self.assertIn("flags=false", async_url)
        self.assertIn("exp=1732550672867", explicit_async_url)
        self.assertNotIn("width=", bare_async_url)
        self.assertNotIn("skip=", async_url)

        with self.assertRaises(ValueError):
            async_client.get_signed_smart_cdn_url("workspace", "template", "input", {"bad": object()})
        with self.assertRaises(ValueError):
            async_client.get_signed_smart_cdn_url("Acme Workspace", "template", "input")
        with self.assertRaises(ValueError):
            sync_client.get_signed_smart_cdn_url("bad.workspace", "template", "input")
        for reserved_key in ("auth_key", "exp", "sig"):
            with self.assertRaises(ValueError):
                async_client.get_signed_smart_cdn_url(
                    "workspace",
                    "template",
                    "input",
                    {reserved_key: "override"},
                )

    async def test_async_assembly_create_non_resumable_upload(self):
        fixture_path = Path(__file__).resolve().parents[1] / "LICENSE"

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_step("resize", "/image/resize", {"use": ":original", "width": 128})

            with fixture_path.open("rb") as upload:
                assembly.add_file(upload)
                response = await assembly.create(resumable=False)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(response.data["assembly_id"], "assembly-123")

        create_request = next(
            entry for entry in self.server.requests if entry["path"] == "/assemblies" and entry["method"] == "POST"
        )
        create_params = json.loads(create_request["body"]["params"])
        self.assertEqual(create_params["steps"]["resize"]["robot"], "/image/resize")
        self.assertIn("signature", create_request["body"])

        uploaded_file = create_request["body"]["file"]
        self.assertEqual(uploaded_file["filename"], "LICENSE")
        self.assertEqual(uploaded_file["content"], fixture_path.read_bytes())

    async def test_async_assembly_wait_polls_with_async_sleep(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0.25},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "initial"},
            )
            rate_limited = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "error": "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0.25},
                },
                status_code=200,
                headers={"X-Async-Route": "rate_limited"},
            )
            completed = Response(
                data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "assembly-123"},
                status_code=200,
                headers={"X-Async-Route": "completed"},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial)) as post_mock:
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(side_effect=[rate_limited, completed]),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        response = await assembly.create(wait=True, resumable=False)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        post_mock.assert_awaited_once()
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call(
                    assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
                ),
                mock.call(
                    assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
                ),
            ],
        )
        self.assertEqual(sleep_mock.await_args_list, [mock.call(0.25), mock.call(0.25)])

    async def test_async_assembly_wait_polls_zero_file_resumable_assembly_without_tus(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0.25},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "initial"},
            )
            completed = Response(
                data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "assembly-123"},
                status_code=200,
                headers={"X-Async-Route": "completed"},
            )

            class _TusClient:
                def __init__(self, tus_url):
                    raise AssertionError("TUS upload should not start for zero-file resumable assemblies")

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial)) as post_mock:
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(return_value=completed),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                            response = await assembly.create(wait=True, resumable=True)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        post_mock.assert_awaited_once()
        self.assertEqual(
            post_mock.await_args.kwargs["extra_data"],
            {"tus_num_expected_upload_files": 0},
        )
        get_mock.assert_awaited_once_with(
            assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
        )
        self.assertEqual(sleep_mock.await_args_list, [mock.call(0.25)])

    async def test_async_assembly_resumable_rate_limit_retries_before_tus_upload(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                calls.append(("uploader", kwargs["metadata"], kwargs["retries"]))

                class _Uploader:
                    def upload(self_inner):
                        calls.append(("upload", kwargs["metadata"]))

                return _Uploader()

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            upload = io.BytesIO(b"payload")
            upload.name = b"payload.bin"
            assembly.add_file(upload)

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
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                    "tus_url": f"{self.server.base_url}/uploads",
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(
                client.request,
                "post",
                new=mock.AsyncMock(side_effect=[rate_limited, success]),
            ) as post_mock:
                with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
                    with mock.patch("asyncio.to_thread", new=mock.AsyncMock(side_effect=lambda func, *args: func(*args))) as to_thread_mock:
                        with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                            response = await assembly.create(resumable=True, retries=2)

        self.assertEqual(response.data["assembly_ssl_url"], f"{self.server.base_url}/assemblies/assembly-123")
        self.assertEqual(post_mock.await_count, 2)
        self.assertEqual(to_thread_mock.await_count, 1)
        self.assertEqual(calls[0], ("client", f"{self.server.base_url}/uploads"))
        self.assertEqual(calls[1], ("uploader", {"assembly_url": f"{self.server.base_url}/assemblies/assembly-123", "fieldname": "file", "filename": "payload.bin"}, 2))

    async def test_async_assembly_resumable_rate_limit_skips_rewind_before_retrying(self):
        calls = []

        class _BrokenRewindStream(io.BytesIO):
            def seek(self, position, *args, **kwargs):
                raise OSError("seek failed")

        class _Uploader:
            def __init__(self, metadata):
                self.metadata = metadata

            def upload(self):
                calls.append(("upload", dict(self.metadata)))

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                calls.append(("uploader", dict(kwargs["metadata"])))
                return _Uploader(kwargs["metadata"])

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            upload = _BrokenRewindStream(b"payload")
            upload.name = "payload.bin"
            assembly.add_file(upload)

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
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                    "tus_url": f"{self.server.base_url}/uploads",
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(
                client.request,
                "post",
                new=mock.AsyncMock(side_effect=[rate_limited, success]),
            ) as post_mock:
                with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
                    with mock.patch("asyncio.to_thread", new=mock.AsyncMock(side_effect=lambda func, *args: func(*args))) as to_thread_mock:
                        with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                            response = await assembly.create(resumable=True, retries=2)

        self.assertEqual(response.data["assembly_ssl_url"], f"{self.server.base_url}/assemblies/assembly-123")
        self.assertEqual(post_mock.await_count, 2)
        self.assertEqual(to_thread_mock.await_count, 1)
        self.assertEqual(calls[0], ("client", f"{self.server.base_url}/uploads"))
        self.assertEqual(calls[1][0], "uploader")

    async def test_async_assembly_non_resumable_rate_limit_raises_when_stream_cannot_be_snapshotted(self):
        class _NonSeekableStream(io.BytesIO):
            def tell(self):
                raise OSError("tell failed")

        reads = []

        async def fake_post(path, data=None, extra_data=None, files=None):
            file_stream = files["file"]
            reads.append(file_stream.read())
            return Response(
                data={
                    "error": "RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                },
                status_code=200,
                headers={},
            )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(_NonSeekableStream(b"payload"))

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(side_effect=fake_post)) as post_mock:
                with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                    with self.assertRaises(RuntimeError):
                        await assembly.create(resumable=False, retries=1)

        self.assertEqual(reads, [b"payload"])
        post_mock.assert_awaited_once()
        sleep_mock.assert_not_awaited()

    async def test_async_assembly_resumable_rate_limit_returns_response_without_upload_when_retries_exhausted(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                raise AssertionError("TUS upload should not start when retries are exhausted")

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            rate_limited = Response(
                data={
                    "error": "RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=rate_limited)) as post_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        response = await assembly.create(resumable=True, retries=0)

        self.assertEqual(response.data["error"], "RATE_LIMIT_REACHED")
        post_mock.assert_awaited_once()
        sleep_mock.assert_not_awaited()
        self.assertEqual(calls, [])

    async def test_async_assembly_resumable_error_response_skips_tus_upload(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                raise AssertionError("TUS upload should not start for error responses")

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            error_response = Response(
                data={
                    "error": "ASSEMBLY_NOT_AUTHORIZED",
                },
                status_code=401,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=error_response)) as post_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    response = await assembly.create(resumable=True)

        self.assertIs(response, error_response)
        post_mock.assert_awaited_once()
        self.assertEqual(calls, [])

    async def test_async_assembly_resumable_response_without_upload_urls_raises_before_tus_upload(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                raise AssertionError("TUS upload should not start when upload URLs are missing")

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            incomplete_response = Response(
                data={"ok": "ASSEMBLY_PROCESSING"},
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=incomplete_response)) as post_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    with self.assertRaisesRegex(RuntimeError, "missing upload URLs"):
                        await assembly.create(resumable=True)

        post_mock.assert_awaited_once()
        self.assertEqual(calls, [])

    async def test_async_assembly_resumable_response_allows_configured_service_tus_url(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                calls.append(("upload", kwargs["metadata"]))
                return self

            def upload(self):
                calls.append(("uploaded",))

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            response = Response(
                data={
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                    "tus_url": "https://example.com/uploads",
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=response)) as post_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    await assembly.create(resumable=True)

        post_mock.assert_awaited_once()
        self.assertEqual(calls[0], ("client", "https://example.com/uploads"))
        self.assertEqual(calls[1][0], "upload")
        self.assertEqual(calls[2], ("uploaded",))

    async def test_async_assembly_wait_returns_response_without_assembly_url(self):
        incomplete_response = Response(
            data={"ok": "ASSEMBLY_PROCESSING"},
            status_code=200,
            headers={},
        )

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=incomplete_response)) as post_mock:
                with mock.patch.object(client, "get_assembly", new=mock.AsyncMock()) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        response = await assembly.create(wait=True, resumable=False)

        self.assertIs(response, incomplete_response)
        post_mock.assert_awaited_once()
        get_mock.assert_not_awaited()
        sleep_mock.assert_not_awaited()

    async def test_async_resumable_upload_posts_extra_data_and_uses_tus_metadata(self):
        calls = []

        class _Uploader:
            def __init__(self, metadata):
                self.metadata = metadata

            def upload(self):
                calls.append(("upload", dict(self.metadata)))

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                calls.append(("uploader", dict(kwargs["metadata"])))
                return _Uploader(kwargs["metadata"])

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            upload = io.BytesIO(b"payload")
            upload.name = 123
            assembly.add_file(upload, "explicit_field")

            with mock.patch(
                "asyncio.to_thread",
                new=mock.AsyncMock(side_effect=lambda func, *args: func(*args)),
            ) as to_thread_mock:
                with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                    response = await assembly.create(resumable=True)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        tus_upload_calls = [
            call
            for call in to_thread_mock.await_args_list
            if getattr(call.args[0], "__name__", "") == "_do_tus_upload"
        ]
        self.assertEqual(len(tus_upload_calls), 1)

        create_request = next(
            entry for entry in self.server.requests if entry["path"] == "/assemblies" and entry["method"] == "POST"
        )
        self.assertEqual(create_request["body"]["tus_num_expected_upload_files"], "1")
        create_params = json.loads(create_request["body"]["params"])
        self.assertEqual(create_params["auth"]["key"], "key")

        self.assertEqual(calls[0], ("client", f"{self.server.base_url}/uploads"))
        self.assertEqual(calls[1][0], "uploader")
        metadata = calls[1][1]
        self.assertEqual(metadata["assembly_url"], f"{self.server.base_url}/assemblies/assembly-123")
        self.assertEqual(metadata["fieldname"], "explicit_field")
        self.assertEqual(metadata["filename"], "explicit_field")
        self.assertEqual(calls[2][0], "upload")

    async def test_async_assembly_wait_retries_after_polling_rate_limit(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "initial"},
            )
            rate_limited = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "error": "RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "rate_limited"},
            )
            completed = Response(
                data={
                    "ok": "ASSEMBLY_COMPLETED",
                    "assembly_id": "assembly-123",
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "completed"},
            )

            with mock.patch.object(
                client.request,
                "post",
                new=mock.AsyncMock(side_effect=[initial, initial]),
            ) as post_mock:
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(side_effect=[rate_limited, completed]),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        response = await assembly.create(wait=True, resumable=False, retries=2)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(post_mock.await_count, 1)
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call(assembly_url=f"{self.server.base_url}/assemblies/assembly-123"),
                mock.call(assembly_url=f"{self.server.base_url}/assemblies/assembly-123"),
            ],
        )
        self.assertEqual(sleep_mock.await_args_list, [mock.call(0), mock.call(0)])

    async def test_async_assembly_wait_resets_poll_rate_limit_retry_budget(self):
        assembly_url = f"{self.server.base_url}/assemblies/assembly-123"

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": assembly_url,
                },
                status_code=200,
                headers={"X-Async-Route": "initial"},
            )
            rate_limited = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "error": "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": assembly_url,
                },
                status_code=200,
                headers={"X-Async-Route": "rate_limited"},
            )
            processing = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": assembly_url,
                },
                status_code=200,
                headers={"X-Async-Route": "processing"},
            )
            completed = Response(
                data={
                    "ok": "ASSEMBLY_COMPLETED",
                    "assembly_id": "assembly-123",
                    "assembly_ssl_url": assembly_url,
                },
                status_code=200,
                headers={"X-Async-Route": "completed"},
            )

            with mock.patch.object(
                client.request,
                "post",
                new=mock.AsyncMock(return_value=initial),
            ) as post_mock:
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(
                        side_effect=[rate_limited, processing, rate_limited, completed]
                    ),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
                        response = await assembly.create(wait=True, resumable=False, retries=1)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(post_mock.await_count, 1)
        self.assertEqual(get_mock.await_count, 4)

    async def test_async_assembly_wait_does_not_follow_poll_response_assembly_url(self):
        initial_url = f"{self.server.base_url}/assemblies/assembly-123"

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": initial_url,
                },
                status_code=200,
                headers={},
            )
            malicious_poll = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "error": "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": "https://example.invalid/assemblies/evil",
                },
                status_code=200,
                headers={},
            )
            completed = Response(
                data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "assembly-123"},
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial)):
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(side_effect=[malicious_poll, completed]),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
                        response = await assembly.create(wait=True, resumable=False, retries=2)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call(assembly_url=initial_url),
                mock.call(assembly_url=initial_url),
            ],
        )

    async def test_async_assembly_wait_returns_last_poll_response_when_budget_exhausted(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "initial"},
            )
            rate_limited = Response(
                data={
                    "ok": "ASSEMBLY_PROCESSING",
                    "error": "RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                },
                status_code=200,
                headers={"X-Async-Route": "rate_limited"},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial)) as post_mock:
                with mock.patch.object(
                    client,
                    "get_assembly",
                    new=mock.AsyncMock(return_value=rate_limited),
                ) as get_mock:
                    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                        response = await assembly.create(wait=True, resumable=False, retries=1)

        self.assertEqual(response.data["error"], "RATE_LIMIT_REACHED")
        post_mock.assert_awaited_once()
        self.assertEqual(
            get_mock.await_args_list,
            [
                mock.call(
                    assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
                ),
                mock.call(
                    assembly_url=f"{self.server.base_url}/assemblies/assembly-123"
                ),
            ],
        )
        self.assertEqual(sleep_mock.await_args_list, [mock.call(0), mock.call(0)])

    async def test_async_assembly_non_resumable_rate_limit_rewinds_files_for_retry(self):
        reads = []
        upload = io.BytesIO(b"payload")

        async def fake_post(path, data=None, extra_data=None, files=None):
            file_stream = files["file"]
            reads.append(file_stream.read())
            if len(reads) == 1:
                return Response(
                    data={
                        "error": "RATE_LIMIT_REACHED",
                        "info": {"retryIn": 0},
                    },
                    status_code=200,
                    headers={},
                )
            return Response(
                data={"ok": "ASSEMBLY_COMPLETED", "assembly_id": "assembly-123"},
                status_code=200,
                headers={},
            )

        async def fake_sleep(delay):
            self.assertEqual(upload.tell(), 0)

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(upload)

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(side_effect=fake_post)):
                with mock.patch("asyncio.sleep", new=mock.AsyncMock(side_effect=fake_sleep)) as sleep_mock:
                    response = await assembly.create(resumable=False, retries=2)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(reads, [b"payload", b"payload"])
        sleep_mock.assert_awaited_once_with(0)

    async def test_async_assembly_non_resumable_rate_limit_raises_when_rewind_fails(self):
        class _BrokenRewindStream(io.BytesIO):
            def seek(self, position, *args, **kwargs):
                raise OSError("seek failed")

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(_BrokenRewindStream(b"payload"))

            rate_limited = Response(
                data={
                    "error": "RATE_LIMIT_REACHED",
                    "info": {"retryIn": 0},
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=rate_limited)) as post_mock:
                with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
                    with self.assertRaises(RuntimeError):
                        await assembly.create(resumable=False, retries=1)

        post_mock.assert_awaited_once()

    async def test_async_assembly_rate_limit_ignores_malformed_error_values(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)
        assembly = client.new_assembly()

        self.assertFalse(assembly._rate_limit_reached({"error": ["RATE_LIMIT_REACHED"]}))
        self.assertFalse(assembly._rate_limit_reached({"error": {"code": "RATE_LIMIT_REACHED"}}))

    async def test_async_assembly_retry_delay_sanitizes_response_info(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)
        assembly = client.new_assembly()

        self.assertEqual(assembly._retry_delay({}), 1)
        self.assertEqual(assembly._retry_delay({"info": None}), 1)
        self.assertEqual(assembly._retry_delay({"info": {"retryIn": "bad"}}), 1)
        self.assertEqual(assembly._retry_delay({"info": {"retryIn": float("nan")}}), 1)
        self.assertEqual(assembly._retry_delay({"info": {"retryIn": -2}}), 0)
        self.assertEqual(assembly._retry_delay({"info": {"retryIn": 0.25}}), 0.25)
        self.assertEqual(assembly._retry_delay({"info": {"retryIn": 9999}}), 9999)

    async def test_async_tus_upload_cancellation_waits_for_thread_to_finish(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)
        assembly = client.new_assembly()
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def blocking_upload(assembly_url, tus_url, retries):
            started.set()
            release.wait(timeout=5)
            finished.set()

        assembly._do_tus_upload = blocking_upload
        upload_task = asyncio.create_task(
            assembly._do_tus_upload_async(
                f"{self.server.base_url}/assemblies/assembly-123",
                f"{self.server.base_url}/uploads",
                retries=1,
            )
        )

        await asyncio.to_thread(started.wait, 5)
        upload_task.cancel()
        await asyncio.sleep(0.05)

        self.assertFalse(upload_task.done())
        self.assertFalse(finished.is_set())

        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await upload_task

        await asyncio.to_thread(finished.wait, 5)
        self.assertTrue(finished.is_set())

    async def test_async_request_uses_connect_and_read_timeouts_for_uploads(self):
        session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)
        upload = io.BytesIO(b"payload")
        upload.name = "clip.jpg"

        response = await client.request.post("/assemblies", data={"foo": "bar"}, files={"file": upload})

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        timeout = session.calls[0][1]["timeout"]
        self.assertIsNone(timeout.total)
        self.assertEqual(timeout.sock_connect, 60)
        self.assertEqual(timeout.sock_read, 60)
        self.assertEqual(session.calls[0][1]["data"]._fields[2][1]["Content-Type"], "image/jpeg")

    async def test_async_request_upload_does_not_close_caller_stream(self):
        fixture_path = Path(__file__).resolve().parents[1] / "LICENSE"
        upload = fixture_path.open("rb")

        try:
            upload_payload = payload.get_payload(_NonClosingUploadStream(upload))
            await upload_payload.close()
            await asyncio.sleep(0.05)

            self.assertFalse(upload.closed)
            upload.seek(0)
            self.assertEqual(upload.read(5), fixture_path.read_bytes()[:5])
        finally:
            if not upload.closed:
                upload.close()

    async def test_async_request_payload_preserves_custom_auth_constraints(self):
        client = AsyncTransloadit("key", "secret", service=self.server.base_url)

        payload = client.request._to_payload(
            {
                "auth": {
                    "max_size": 1024,
                    "referer": "https://example.com",
                },
                "foo": "bar",
            }
        )

        params = json.loads(payload["params"])
        self.assertEqual(params["auth"]["key"], "key")
        self.assertIn("expires", params["auth"])
        self.assertEqual(params["auth"]["max_size"], 1024)
        self.assertEqual(params["auth"]["referer"], "https://example.com")

        with self.assertRaises(ValueError):
            client.request._to_payload({"auth": "not-a-dict"})

    async def test_async_request_filters_none_and_matches_sync_booleans_in_extra_data(self):
        session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)
        upload = io.BytesIO(b"payload")
        upload.name = "clip.jpg"

        response = await client.request.post(
            "/assemblies",
            data={"foo": "bar"},
            extra_data={"enabled": True, "skip": None, "tags": ["a", "b"]},
            files={"file": upload},
        )

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        fields = {field[0]["name"]: field for field in session.calls[0][1]["data"]._fields}
        self.assertIn("enabled", fields)
        self.assertNotIn("skip", fields)
        self.assertEqual(fields["enabled"][2], "True")
        tag_values = [field[2] for field in session.calls[0][1]["data"]._fields if field[0]["name"] == "tags"]
        self.assertEqual(tag_values, ["a", "b"])

    def test_non_closing_upload_stream_reflects_seekability(self):
        class _NonSeekableUpload(io.BytesIO):
            def seekable(self):
                return False

        class _BrokenSeekableUpload(io.BytesIO):
            def seekable(self):
                raise OSError("seekable failed")

        class _WriteOnlyUpload:
            def readable(self):
                return False

        self.assertTrue(_NonClosingUploadStream(io.BytesIO(b"payload")).seekable())
        self.assertFalse(_NonClosingUploadStream(_NonSeekableUpload(b"payload")).seekable())
        self.assertFalse(_NonClosingUploadStream(_BrokenSeekableUpload(b"payload")).seekable())
        self.assertFalse(_NonClosingUploadStream(_WriteOnlyUpload()).readable())

    async def test_async_request_uses_filename_fallback_for_trailing_slash_stream_name(self):
        session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)
        upload = io.BytesIO(b"payload")
        upload.name = "/tmp/"

        response = await client.request.post("/assemblies", data={"foo": "bar"}, files={"file": upload})

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(session.calls[0][1]["data"]._fields[2][0]["filename"], "file")

    async def test_async_resumable_upload_uses_to_thread(self):
        calls = []

        class _Uploader:
            def __init__(self, metadata):
                self.metadata = metadata

            def upload(self):
                calls.append(("upload", dict(self.metadata)))

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))
                self.tus_url = tus_url

            def uploader(self, **kwargs):
                calls.append(("uploader", kwargs["metadata"], kwargs["chunk_size"], kwargs["retries"]))
                return _Uploader(kwargs["metadata"])

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()

            initial = Response(
                data={
                    "assembly_ssl_url": f"{self.server.base_url}/assemblies/assembly-123",
                    "tus_url": f"{self.server.base_url}/uploads",
                },
                status_code=200,
                headers={},
            )

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(return_value=initial)):
                with mock.patch("asyncio.to_thread", new=mock.AsyncMock(side_effect=lambda func, *args: func(*args))) as to_thread_mock:
                    with mock.patch("transloadit.async_assembly.tus.TusClient", new=_TusClient):
                        assembly.add_file(io.BytesIO(b"payload"))
                        response = await assembly.create(resumable=True, retries=5)

        self.assertEqual(response.data["assembly_ssl_url"], f"{self.server.base_url}/assemblies/assembly-123")
        to_thread_mock.assert_awaited_once()
        self.assertEqual(calls[0], ("client", f"{self.server.base_url}/uploads"))
        self.assertEqual(calls[1][0], "uploader")
        metadata = calls[1][1]
        self.assertEqual(metadata["assembly_url"], f"{self.server.base_url}/assemblies/assembly-123")
        self.assertEqual(metadata["fieldname"], "file")
        self.assertEqual(metadata["filename"], "file")
        self.assertEqual(calls[2][0], "upload")

    def test_async_assembly_helpers_cover_duplicate_names_and_rewind_edges(self):
        client = AsyncTransloadit("key", "secret")
        assembly = client.new_assembly()

        first = io.BytesIO(b"abc")
        second = io.BytesIO(b"xyz")
        third = io.BytesIO(b"456")
        explicit = io.BytesIO(b"123")

        assembly.add_file(first)
        assembly.add_file(second)
        assembly.add_file(third)
        assembly.add_file(explicit, "explicit")

        self.assertIs(assembly.files["file"], first)
        self.assertIs(assembly.files["file_1"], second)
        self.assertIs(assembly.files["file_2"], third)
        self.assertIs(assembly.files["explicit"], explicit)

        assembly.remove_file("explicit")
        self.assertIsNone(assembly.files.get("explicit"))

        first.read(1)
        second.read(2)
        positions, missing = assembly._snapshot_file_positions()
        self.assertEqual(positions["file"], 1)
        self.assertEqual(positions["file_1"], 2)
        self.assertEqual(missing, [])

        first.read(1)
        second.read(1)
        assembly._rewind_files(positions)
        self.assertEqual(first.tell(), 1)
        self.assertEqual(second.tell(), 2)

        broken = _BrokenStream()
        assembly.files["broken"] = broken
        positions, missing = assembly._snapshot_file_positions()
        self.assertNotIn("broken", positions)
        self.assertEqual(missing, ["broken"])

        assembly._rewind_files({"missing": 4})
        with self.assertRaises(RuntimeError):
            assembly._rewind_files({"broken": 7})
