import io
import asyncio
import json
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, mock

from aiohttp import web

from transloadit.async_client import AsyncTransloadit
from transloadit.response import Response


class _AsyncApiServer:
    def __init__(self):
        self.requests = []
        self.app = web.Application()
        self.app.router.add_get("/assemblies/{assembly_id}", self.handle_get_assembly)
        self.app.router.add_get("/assemblies-text/{assembly_id}", self.handle_get_assembly_text)
        self.app.router.add_get("/assemblies", self.handle_list_assemblies)
        self.app.router.add_delete("/assemblies/{assembly_id}", self.handle_cancel_assembly)
        self.app.router.add_get("/templates/{template_id}", self.handle_get_template)
        self.app.router.add_get("/templates", self.handle_list_templates)
        self.app.router.add_put("/templates/{template_id}", self.handle_update_template)
        self.app.router.add_post("/templates", self.handle_create_template)
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


class _RecordingSession:
    def __init__(self, payload):
        self.calls = []
        self.closed = False
        self.payload = payload

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _FakeResponseContext(self.payload)

    async def close(self):
        self.closed = True


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

        self.assertIsNotNone(client.request.session)
        self.assertTrue(client.request.session.closed)

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
        self.assertEqual(create_params["steps"]["resize"]["robot"], "/image/resize")

    async def test_async_client_accepts_json_with_text_content_type(self):
        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            response = await client.get_assembly(
                assembly_url=f"{self.server.base_url}/assemblies-text/abc123"
            )

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(response.data["assembly_id"], "abc123")
        self.assertEqual(response.headers["X-Async-Route"], "get_assembly_text")

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

    async def test_async_assembly_resumable_rate_limit_retries_before_tus_upload(self):
        calls = []

        class _TusClient:
            def __init__(self, tus_url):
                calls.append(("client", tus_url))

            def uploader(self, **kwargs):
                calls.append(("uploader", kwargs["metadata"]))

                class _Uploader:
                    def upload(self_inner):
                        calls.append(("upload", kwargs["metadata"]))

                return _Uploader()

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            upload = io.BytesIO(b"payload")
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

    async def test_async_assembly_non_resumable_rate_limit_rewinds_files_for_retry(self):
        reads = []

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

        async with AsyncTransloadit("key", "secret", service=self.server.base_url) as client:
            assembly = client.new_assembly()
            assembly.add_file(io.BytesIO(b"payload"))

            with mock.patch.object(client.request, "post", new=mock.AsyncMock(side_effect=fake_post)):
                with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock) as sleep_mock:
                    response = await assembly.create(resumable=False, retries=2)

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        self.assertEqual(reads, [b"payload", b"payload"])
        sleep_mock.assert_awaited_once_with(0)

    async def test_async_request_uses_connect_and_read_timeouts_for_uploads(self):
        session = _RecordingSession({"ok": "ASSEMBLY_COMPLETED"})
        client = AsyncTransloadit("key", "secret", service=self.server.base_url, session=session)
        upload = io.BytesIO(b"payload")

        response = await client.request.post("/assemblies", data={"foo": "bar"}, files={"file": upload})

        self.assertEqual(response.data["ok"], "ASSEMBLY_COMPLETED")
        timeout = session.calls[0][1]["timeout"]
        self.assertIsNone(timeout.total)
        self.assertEqual(timeout.sock_connect, 60)
        self.assertEqual(timeout.sock_read, 60)

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
