import json
import asyncio
import base64
import hashlib
import hmac
import io
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from aiohttp import web
import pytest
from requests.structures import CaseInsensitiveDict

from transloadit.client import Transloadit
from transloadit.async_client import AsyncTransloadit
from transloadit.stream import EventParser, StreamError
from transloadit.endpoint_transport import tus_request, validate_upload_location
from transloadit.response import Response


def test_create_auth_key_sends_signed_request(requests_mock):
    endpoint = requests_mock.post(
        "https://api2.transloadit.com/auth_keys", json={"ok": "AUTH_KEY_CREATED"}
    )
    client = Transloadit("key", "secret")
    response = client.create_auth_key({"description": "worker", "scope": "assemblies:read"})
    payload = parse_qs(endpoint.last_request.text)
    params = json.loads(payload["params"][0])
    assert params["description"] == "worker"
    assert params["scope"] == "assemblies:read"
    assert params["auth"]["key"] == "key"
    assert payload["signature"][0].startswith("sha384:")
    assert response.data == {"ok": "AUTH_KEY_CREATED"}


def test_move_dam_asset_uses_patch(requests_mock):
    endpoint = requests_mock.patch(
        "https://api2.transloadit.com/dam/assets/asset-123", json={"ok": "ASSET_MOVED"}
    )
    response = Transloadit("key", "secret").move_dam_asset("asset-123", {"filename": "new.jpg"})
    assert endpoint.call_count == 1
    assert response.data["ok"] == "ASSET_MOVED"


ASSEMBLY_ID = "a" * 32


class WireServer:
    def __init__(self):
        self.requests = []
        self.upload = b""
        self.disconnected = asyncio.Event()
        self.started = asyncio.Event()
        self.stream_mode = "normal"

    async def handle(self, request):
        data = b""
        fields = {}
        if request.content_type == "multipart/form-data":
            for key, value in (await request.post()).items():
                fields[key] = value.file.read() if isinstance(value, web.FileField) else value
        else:
            data = await request.read()
            if request.content_type == "application/x-www-form-urlencoded":
                fields = {key: values[0] for key, values in parse_qs(data.decode()).items()}
        record = {"method": request.method, "path": request.path, "body": data,
                  "fields": fields, "query": dict(request.query), "headers": CaseInsensitiveDict(request.headers)}
        self.requests.append(record)
        if request.path == "/ws1":
            if self.stream_mode == "redirect":
                return web.Response(status=302, headers={"Location": self.url + "/redirect-target"})
            if self.stream_mode == "unavailable":
                return web.Response(status=503)
            response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
            await response.prepare(request)
            try:
                if self.stream_mode == "normal":
                    payload = ('\ufeff: heartbeat\r\nevent: assembly_execution_progress\r\n'
                               'data: {"progress_combined": 50,\r\ndata: "label": "café"}\r\n\r\n'
                               'event: future_event\ndata: {"value": true}\n\n'
                               'data: assembly_finished\n\n'
                               'data: must_not_be_delivered\n\n').encode()
                    for byte in payload:
                        await response.write(bytes([byte]))
                else:
                    await response.write(b"data: ping\n\n")
                    self.started.set()
                    for _ in range(100):
                        await asyncio.sleep(.01)
                        await response.write(b": heartbeat\n\n")
            except (ConnectionResetError, asyncio.CancelledError):
                self.disconnected.set()
            return response
        if request.path == "/resumable/files":
            if request.method == "OPTIONS":
                return web.Response(status=204, headers={"Tus-Version": "1.0.0", "Tus-Extension": "creation,termination"})
            self.upload = data
            return web.Response(status=201, headers={"Location": "/resumable/files/upload-1", "Upload-Offset": str(len(data))})
        if request.path == "/resumable/files/upload-1":
            if request.method == "HEAD":
                return web.Response(headers={"Upload-Offset": str(len(self.upload)), "Upload-Length": "6"})
            if request.method == "PATCH":
                assert int(request.headers["Upload-Offset"]) == len(self.upload)
                self.upload += data
                return web.Response(status=204, headers={"Upload-Offset": str(len(self.upload))})
            if request.method == "DELETE":
                self.upload = b""
                return web.Response(status=204)
            if request.headers.get("Range") == "bytes=1-2":
                return web.Response(status=206, body=self.upload[1:3], headers={"Content-Range": "bytes 1-2/6"})
            return web.Response(body=self.upload, content_type="application/octet-stream")
        return web.json_response({"ok": "OK", "access_token": "token-value"})


@asynccontextmanager
async def wire_client(mode, *, bearer_token=None):
    server = WireServer()
    app = web.Application()
    app.router.add_route("*", "/{path:.*}", server.handle)
    runner = web.AppRunner(app, shutdown_timeout=.1)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    server.url = "http://127.0.0.1:" + str(site._server.sockets[0].getsockname()[1])
    cls = Transloadit if mode == "sync" else AsyncTransloadit
    client = cls("key", "secret", service=server.url, bearer_token=bearer_token)
    try:
        yield client, server
    finally:
        if mode == "async":
            await client.aclose()
        await runner.cleanup()


async def call(client, method, *args, **kwargs):
    operation = getattr(client, method)
    if isinstance(client, AsyncTransloadit):
        return await operation(*args, **kwargs)
    return await asyncio.to_thread(operation, *args, **kwargs)


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("name,verb,path,args", [
    ("create_auth_key", "POST", "/auth_keys", ()),
    ("delete_auth_key", "DELETE", "/auth_keys/key-id", ("key-id",)),
    ("update_auth_key", "PUT", "/auth_keys/key-id", ("key-id",)),
    ("list_auth_keys", "GET", "/auth_keys", ()),
    ("list_auth_key_scopes", "GET", "/auth_keys/scopes", ()),
    ("show_auth_key_secret", "POST", "/auth_keys/show_secret/key-id", ("key-id",)),
    ("get_dam_asset", "GET", "/dam/assets/asset-id", ("asset-id",)),
    ("list_dam_assets", "GET", "/dam/assets", ()),
    ("move_dam_asset", "PATCH", "/dam/assets/asset-id", ("asset-id",)),
    ("move_dam_entry", "POST", "/dam/entries/move", ()),
    ("delete_dam_asset", "DELETE", "/dam/assets/asset-id", ("asset-id",)),
    ("bulk_move_dam_assets", "POST", "/dam/assets/bulk/move", ()),
    ("bulk_delete_dam_assets", "POST", "/dam/assets/bulk/delete", ()),
    ("assembly_stats", "GET", "/assembly_stats", ()),
    ("priority_job_slot_stats", "GET", "/priority_job_slot_stats", ()),
])
def test_new_endpoints_preserve_signed_wire_payload(mode, name, verb, path, args):
    async def scenario():
        async with wire_client(mode) as (client, server):
            payload = {"custom": {"nested": [False, 3]}, "auth": {"max_size": 1024}}
            original = json.loads(json.dumps(payload))
            response = await call(client, name, *args, **{"params" if verb == "GET" else "data": payload})
            request = server.requests[-1]
            assert (request["method"], request["path"]) == (verb, path)
            fields = request["query"] if verb == "GET" else request["fields"]
            params = json.loads(fields["params"])
            assert params["custom"] == payload["custom"]
            assert params["auth"]["max_size"] == 1024
            assert params["auth"]["key"] == "key"
            expected = hmac.new(b"secret", fields["params"].encode(), hashlib.sha384).hexdigest()
            assert fields["signature"] == "sha384:" + expected
            assert payload == original
            assert response.data["ok"] == "OK"
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_replacement_sends_multipart_and_keeps_file_open(mode):
    async def scenario():
        async with wire_client(mode) as (client, server):
            stream = io.BytesIO(b"file bytes")
            await call(client, "replace_assembly", ASSEMBLY_ID, {"steps": {}}, {"field": True}, {"file": stream})
            request = server.requests[-1]
            assert request["method"] == "PUT"
            assert request["path"] == "/assemblies/" + ASSEMBLY_ID
            assert request["fields"]["file"] == b"file bytes"
            assert request["fields"]["field"] == "True"
            assert json.loads(request["fields"]["params"])["steps"] == {}
            assert not stream.closed
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_bearer_requests_and_public_notifications_have_distinct_auth(mode):
    async def scenario():
        async with wire_client(mode, bearer_token="bearer-value") as (client, server):
            await call(client, "list_auth_keys", {"fields": ["name"]})
            request = server.requests[-1]
            assert request["headers"]["Authorization"] == "Bearer bearer-value"
            assert json.loads(request["query"]["params"]) == {"fields": ["name"]}
            assert "signature" not in request["query"]
            await call(client, "list_assembly_notifications", ASSEMBLY_ID, {"page": 2})
            request = server.requests[-1]
            assert "Authorization" not in request["headers"]
            assert request["query"] == {"page": "2"}
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("data,authorization", [
    ({"scope": "assemblies:read"}, "Basic a2V5OnNlY3JldA=="),
    ({"grant_type": "authorization_code", "code": "code", "code_verifier": "proof", "client_id": "id", "redirect_uri": "https://example.test/callback"}, None),
    ({"grant_type": "refresh_token", "refresh_token": "refresh", "client_id": "id", "resource": "https://api2.transloadit.com"}, None),
])
def test_token_grants_forward_fields_with_contract_auth(mode, data, authorization):
    async def scenario():
        async with wire_client(mode) as (client, server):
            if authorization is None:
                client.auth_secret = None
            response = await call(client, "issue_bearer_token", data)
            request = server.requests[-1]
            assert (request["method"], request["path"]) == ("POST", "/token")
            assert request["headers"].get("Authorization") == authorization
            assert request["fields"] == {"grant_type": "client_credentials", **data}
            assert "signature" not in request["fields"]
            assert response.data["access_token"] == "token-value"
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_all_six_raw_tus_operations(mode):
    async def scenario():
        async with wire_client(mode, bearer_token="must-not-leak") as (client, server):
            assembly = {"assembly_id": ASSEMBLY_ID, "assembly_ssl_url": server.url + "/assemblies/" + ASSEMBLY_ID,
                        "tus_url": server.url + "/resumable/files"}
            response = await call(client, "tus_options", assembly)
            assert response.headers["tus-version"] == "1.0.0"
            response = await call(client, "create_upload", assembly, headers={"Upload-Length": "6"}, body=b"{a")
            assert response.status_code == 201
            assert response.headers["Location"] == "/resumable/files/upload-1"
            upload_url = response.upload_url
            request = server.requests[-1]
            metadata = request["headers"]["Upload-Metadata"].split(" ", 1)[1]
            assert base64.b64decode(metadata).decode() == assembly["assembly_ssl_url"]
            response = await call(client, "get_upload_offset", upload_url)
            assert response.headers["upload-offset"] == "2"
            response = await call(client, "patch_upload", upload_url, headers={"Upload-Offset": "2"}, body=b"bc}\xff")
            assert response.headers["Upload-Offset"] == "6"
            response = await call(client, "download_upload", upload_url)
            assert response.data == b"{abc}\xff"
            response = await call(client, "download_upload", upload_url, headers={"Range": "bytes=1-2"})
            assert response.status_code == 206 and response.data == b"ab"
            response = await call(client, "delete_upload", upload_url)
            assert response.status_code == 204 and server.upload == b""
            for request in server.requests:
                assert "Authorization" not in request["headers"]
                assert "params" not in request["query"]
                assert "signature" not in request["query"]
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_stream_decodes_split_unicode_multiline_and_terminal_events(mode):
    async def scenario():
        async with wire_client(mode, bearer_token="must-not-leak") as (client, server):
            url = server.url + "/ws1?assembly=" + ASSEMBLY_ID
            if mode == "sync":
                def consume():
                    with client.stream_assembly_status(url) as events:
                        return list(events)
                events = await asyncio.to_thread(consume)
            else:
                async with client.stream_assembly_status(url) as stream:
                    events = [event async for event in stream]
            assert [e.event for e in events] == ["assembly_execution_progress", "future_event", "assembly_finished"]
            assert events[0].data == {"progress_combined": 50, "label": "café"}
            assert events[-1].terminal
            assert server.requests[-1]["headers"]["Accept"] == "text/event-stream"
            assert "Authorization" not in server.requests[-1]["headers"]
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("behavior,status", [("redirect", 302), ("unavailable", 503)])
def test_stream_errors_do_not_follow_redirects(mode, behavior, status):
    async def scenario():
        async with wire_client(mode) as (client, server):
            server.stream_mode = behavior
            url = server.url + "/ws1?assembly=" + ASSEMBLY_ID
            with pytest.raises(StreamError) as caught:
                if mode == "sync":
                    def consume():
                        with client.stream_assembly_status(url) as events:
                            list(events)
                    await asyncio.to_thread(consume)
                else:
                    async with client.stream_assembly_status(url):
                        pass
            assert caught.value.status_code == status
            assert len(server.requests) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_stream_early_exit_closes_connection(mode):
    async def scenario():
        async with wire_client(mode) as (client, server):
            server.stream_mode = "held"
            url = server.url + "/ws1?assembly=" + ASSEMBLY_ID
            if mode == "sync":
                def consume():
                    with client.stream_assembly_status(url) as events:
                        assert next(events).event == "ping"
                await asyncio.to_thread(consume)
            else:
                async def consume():
                    async with client.stream_assembly_status(url) as events:
                        assert (await anext(events)).event == "ping"
                        await asyncio.sleep(100)
                task = asyncio.create_task(consume())
                await asyncio.wait_for(server.started.wait(), 2)
                await asyncio.sleep(.02)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            await asyncio.wait_for(server.disconnected.wait(), 2)
    asyncio.run(scenario())


def test_event_parser_bounds_and_eof_behavior():
    parser = EventParser(max_event_size=30)
    with pytest.raises(ValueError, match="max_event_size"):
        list(parser.feed(b"data: " + b"a" * 31))
    parser = EventParser()
    assert list(parser.feed(b"data: incomplete")) == []
    parser = EventParser()
    events = list(parser.feed(b"id: 2\nretry: 123\nevent: assembly_error\ndata: {\"error\":\"failed\"}\n\n"))
    assert events[0].id == "2" and events[0].retry == 123
    assert events[0].terminal and events[0].data["error"] == "failed"


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("url", [
    "https://evil.test/resumable/files/x", "https://api2.transloadit.com.evil.test/resumable/files/x",
    "https://user:password@api2.transloadit.com/resumable/files/x", "http://api2.transloadit.com/resumable/files/x",
    "https://api2.transloadit.com/resumable/files/../admin", "https://api2.transloadit.com/resumable/files/%2e%2e/admin",
    "https://api2.transloadit.com/templates/x", "https://api2.transloadit.com/resumable/files/x#fragment",
    "https://api2.transloadit.com/resumable/files/%252e%252e",
    "https://api2.transloadit.com/resumable/files/a%2Fb",
    "https://api2.transloadit.com/resumable/files/%ff",
    "https://api2.transloadit.com/resumable/files/x?",
])
def test_raw_upload_rejects_untrusted_capabilities(mode, url):
    async def scenario():
        cls = Transloadit if mode == "sync" else AsyncTransloadit
        client = cls("key", "secret")
        try:
            with pytest.raises(ValueError):
                await call(client, "get_upload_offset", url)
        finally:
            if mode == "async":
                await client.aclose()
    asyncio.run(scenario())


def test_generation_check():
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "scripts/generate_endpoints.py", "--check"], cwd=root, check=True)


def test_assembly_and_tus_can_use_distinct_trusted_regional_hosts():
    assembly = {
        "assembly_id": ASSEMBLY_ID,
        "assembly_ssl_url": "https://api2-cell.transloadit.com/assemblies/" + ASSEMBLY_ID,
        "tus_url": "https://api2-region.transloadit.com/resumable/files/",
    }
    _, url, headers, _ = tus_request(Transloadit("key", "secret"), "tusd.create-upload", assembly, {"Upload-Length": "1"}, None)
    assert url == assembly["tus_url"]
    assert base64.b64decode(headers["upload-metadata"].split(" ", 1)[1]).decode() == assembly["assembly_ssl_url"]


@pytest.mark.parametrize("location", [
    "https://evil.test/resumable/files/id", "/resumable/files/../files/id", "/resumable/files/%2e%2e/id", "",
])
def test_creation_rejects_untrusted_or_normalized_locations(location):
    client = Transloadit("key", "secret")
    response = Response(data="", status_code=201, headers=CaseInsensitiveDict({"Location": location}))
    with pytest.raises(ValueError):
        validate_upload_location(client, "https://api2-region.transloadit.com/resumable/files/", response)


def test_creation_accepts_location_from_another_trusted_uploader():
    client = Transloadit("key", "secret")
    location = "https://api2-cell.transloadit.com/resumable/files/id"
    response = Response(data="", status_code=201, headers=CaseInsensitiveDict({"Location": location}))
    validate_upload_location(client, "https://api2-region.transloadit.com/resumable/files/", response)
    assert response.upload_url == location


@pytest.mark.parametrize("field,value", [("Authorization", "Bearer secret"), ("Cookie", "session=secret"), ("Host", "evil.test")])
def test_tus_rejects_ambient_credentials(field, value):
    with pytest.raises(ValueError):
        tus_request(Transloadit("key", "secret"), "tusd.get-upload-offset",
                    "https://api2-region.transloadit.com/resumable/files/id", {field: value}, None)


def test_tus_metadata_cannot_change_assembly_identity():
    assembly = {"assembly_id": ASSEMBLY_ID,
                "assembly_ssl_url": "https://api2-cell.transloadit.com/assemblies/" + ASSEMBLY_ID,
                "tus_url": "https://api2-region.transloadit.com/resumable/files/"}
    client = Transloadit("key", "secret")
    with pytest.raises(ValueError, match="override"):
        tus_request(client, "tusd.create-upload", assembly, {"Upload-Metadata": "assembly_url YXR0YWNr"}, None)
    assembly["assembly_id"] = "b" * 32
    with pytest.raises(ValueError, match="identity"):
        tus_request(client, "tusd.create-upload", assembly, {}, None)
