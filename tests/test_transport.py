"""Behavioral coverage for handwritten Assembly requests and multipart uploads."""
import asyncio
import io
from contextlib import asynccontextmanager
from urllib.parse import parse_qs
from unittest import mock

import aiohttp
from aiohttp import web
import pytest
from requests.structures import CaseInsensitiveDict

from transloadit.client import Transloadit
from transloadit.async_client import AsyncTransloadit

ASSEMBLY_ID = "a" * 32


class WireServer:
    def __init__(self):
        self.requests = []

    async def handle(self, request):
        data = b""
        fields = {}
        filenames = {}
        if request.content_type == "multipart/form-data":
            for key, value in (await request.post()).items():
                fields[key] = value.file.read() if isinstance(value, web.FileField) else value
                if isinstance(value, web.FileField):
                    filenames[key] = value.filename
        else:
            data = await request.read()
            if request.content_type == "application/x-www-form-urlencoded":
                fields = {key: values[0] for key, values in parse_qs(data.decode()).items()}
        self.requests.append({"method": request.method, "path": request.path, "body": data,
                              "filenames": filenames, "fields": fields, "query": dict(request.query),
                              "headers": CaseInsensitiveDict(request.headers)})
        if request.method == "GET" and request.path == "/assemblies/" + ASSEMBLY_ID:
            return web.json_response({"ok": "ASSEMBLY_COMPLETED", "assembly_id": ASSEMBLY_ID})
        if request.method == "POST" and request.path == "/assemblies" and hasattr(self, "assembly_response"):
            return web.json_response(self.assembly_response)
        return web.json_response({"ok": "OK"})


def test_sync_isolated_transport_preserves_proxy_and_ca_settings(requests_mock, monkeypatch, tmp_path):
    url = "https://api2.transloadit.com/assemblies/" + ASSEMBLY_ID
    endpoint = requests_mock.get(url, json={"ok": "OK"})
    monkeypatch.delenv("https_proxy", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/custom/company-ca.pem")
    netrc = tmp_path / "netrc"
    netrc.write_text("machine api2.transloadit.com login ambient password must-not-leak\n")
    monkeypatch.setenv("NETRC", str(netrc))
    Transloadit("key", "secret").get_assembly(assembly_id=ASSEMBLY_ID)
    assert endpoint.last_request.proxies["https"] == "http://proxy.invalid:3128"
    assert endpoint.last_request.verify == "/custom/company-ca.pem"
    assert "Authorization" not in endpoint.last_request.headers


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_isolated_transports_use_environment_proxy_without_netrc(mode, monkeypatch, tmp_path):
    async def scenario():
        async with wire_client(mode) as (client, server):
            monkeypatch.delenv("http_proxy", raising=False)
            monkeypatch.setenv("HTTP_PROXY", server.url)
            monkeypatch.delenv("no_proxy", raising=False)
            monkeypatch.setenv("NO_PROXY", "")
            netrc = tmp_path / "netrc"
            netrc.write_text("machine 127.0.0.2 login ambient password must-not-leak\n")
            monkeypatch.setenv("NETRC", str(netrc))
            # No server listens here: every request must traverse the proxy.
            client.service = "http://127.0.0.2:1"
            await call(client, "get_assembly", assembly_id=ASSEMBLY_ID)
            await call(client, "cancel_assembly", assembly_id=ASSEMBLY_ID)
            assert len(server.requests) == 2
            assert all("Authorization" not in request["headers"] for request in server.requests)
    asyncio.run(scenario())


def test_async_isolated_transport_reuses_injected_connector_without_credentials(monkeypatch):
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.setenv("NO_PROXY", "sdk.invalid")
    async def scenario():
        async with wire_client("async") as (_, server):
            class Resolver(aiohttp.abc.AbstractResolver):
                async def resolve(self, host, port=0, family=0):
                    return [{"hostname": host, "host": "127.0.0.1", "port": port, "family": 2, "proto": 0, "flags": 0}]
                async def close(self):
                    pass
            connector = aiohttp.TCPConnector(resolver=Resolver())
            async with aiohttp.ClientSession(connector=connector, auth=aiohttp.BasicAuth("ambient", "secret"),
                                             headers={"Cookie": "session=must-not-leak"}) as session:
                service = server.url.replace("127.0.0.1", "sdk.invalid")
                async with AsyncTransloadit("key", "secret", service=service, session=session) as client:
                    await client.get_assembly(assembly_id=ASSEMBLY_ID)
                assert not connector.closed and not session.closed
                assert "Authorization" not in server.requests[-1]["headers"]
                assert "Cookie" not in server.requests[-1]["headers"]
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_assembly_capabilities_do_not_borrow_account_credentials(mode, monkeypatch, tmp_path):
    netrc = tmp_path / "netrc"
    netrc.write_text("machine 127.0.0.1 login ambient password must-not-leak\n")
    monkeypatch.setenv("NETRC", str(netrc))
    async def scenario():
        async with wire_client(mode) as (client, server):
            async with aiohttp.ClientSession(auth=aiohttp.BasicAuth("ambient", "secret"),
                                             headers={"Cookie": "ambient-cookie"}) as session:
                if mode == "async":
                    client = AsyncTransloadit("key", "secret", service=server.url, session=session)
                await call(client, "get_assembly", assembly_id=ASSEMBLY_ID)
                await call(client, "cancel_assembly", assembly_url=server.url + "/assemblies/" + ASSEMBLY_ID)
            assert len(server.requests) == 2
            for request in server.requests:
                assert "Authorization" not in request["headers"]
                assert "Cookie" not in request["headers"]
                assert request["query"] == {}
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("encoding,line_ending", [("utf-8", "\n"), ("utf-8", "\r\n"), ("utf-16", "\n")])
def test_text_mode_multipart_preserves_content_and_file_ownership(mode, tmp_path, encoding, line_ending):
    path = tmp_path / "text.txt"
    path.write_bytes(("caf\u00e9" + line_ending).encode(encoding))
    async def scenario():
        async with wire_client(mode) as (client, server):
            if mode == "async":
                client.request._timeout = lambda: aiohttp.ClientTimeout(total=5)
            assembly = client.new_assembly()
            with path.open(encoding=encoding) as upload:
                assembly.add_file(upload, "text")
                if mode == "sync":
                    await asyncio.to_thread(assembly.create, resumable=False)
                else:
                    await assembly.create(resumable=False)
                assert not upload.closed
            assert server.requests[-1]["fields"]["text"] == "caf\u00e9\n".encode()
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_custom_service_can_poll_returned_worker_origin(mode):
    async def scenario():
        async with wire_client(mode) as (client, server), wire_client(mode) as (_, worker):
            server.assembly_response = {"ok": "ASSEMBLY_UPLOADING", "assembly_id": ASSEMBLY_ID,
                                        "assembly_ssl_url": worker.url + "/assemblies/" + ASSEMBLY_ID}
            assembly = client.new_assembly()
            sleep_path = "transloadit.assembly.sleep" if mode == "sync" else "transloadit.async_assembly.asyncio.sleep"
            with mock.patch(sleep_path, new_callable=mock.Mock if mode == "sync" else mock.AsyncMock):
                if mode == "sync":
                    result = await asyncio.to_thread(assembly.create, wait=True)
                else:
                    result = await assembly.create(wait=True)
            assert result.data["ok"] == "ASSEMBLY_COMPLETED"
            assert "Authorization" not in worker.requests[-1]["headers"]
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("host", ["api2.transloadit.com", "api2-morven.transloadit.com"])
def test_legacy_http_assembly_urls_use_https(mode, host):
    async def scenario():
        client = (Transloadit if mode == "sync" else AsyncTransloadit)("key", "secret")
        client.request.public = (mock.Mock if mode == "sync" else mock.AsyncMock)()
        for method, verb in [("get_assembly", "GET"), ("cancel_assembly", "DELETE")]:
            await call(client, method, assembly_url=f"http://{host}/assemblies/{ASSEMBLY_ID}")
            client.request.public.assert_called_with(verb, f"https://{host}/assemblies/{ASSEMBLY_ID}", params=None)
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("host", ["api2-x.other.transloadit.com", "api2-xn--example.transloadit.com"])
def test_assembly_urls_reject_non_api_hosts(mode, host):
    async def scenario():
        client = (Transloadit if mode == "sync" else AsyncTransloadit)("key", "secret")
        client.request.public = (mock.Mock if mode == "sync" else mock.AsyncMock)()
        with pytest.raises(ValueError, match="untrusted Assembly URL"):
            await call(client, "get_assembly", assembly_url=f"https://{host}/assemblies/{ASSEMBLY_ID}")
        client.request.public.assert_not_called()
    asyncio.run(scenario())


@pytest.mark.parametrize("trust_env", [False, True])
def test_isolated_async_calls_preserve_explicit_proxy_configuration(monkeypatch, trust_env):
    # The injected proxy takes precedence over an unusable environment proxy.
    monkeypatch.delenv("http_proxy", raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.3:1")
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.setenv("NO_PROXY", "")
    async def scenario():
        async with wire_client("async") as (_, server):
            proxy_auth = aiohttp.BasicAuth("proxy-user", "proxy-password")
            async with aiohttp.ClientSession(proxy=server.url, proxy_auth=proxy_auth, trust_env=trust_env) as session:
                service = "http://127.0.0.2:1"
                client = AsyncTransloadit("key", "secret", service=service, session=session)
                await client.list_templates()
                await client.get_assembly(assembly_id=ASSEMBLY_ID)
                await client.cancel_assembly(assembly_id=ASSEMBLY_ID)
                assert not session.closed
            assert len(server.requests) == 3
            assert all(request["headers"]["Proxy-Authorization"] == proxy_auth.encode() for request in server.requests)
            assert all("Authorization" not in request["headers"] for request in server.requests)
    asyncio.run(scenario())


def test_async_proxy_selection_matches_signed_calls_with_all_proxy(monkeypatch):
    for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.2:1")
    monkeypatch.setenv("NO_PROXY", "")
    async def scenario():
        async with wire_client("async") as (client, server):
            await client.list_templates()
            await client.get_assembly(assembly_id=ASSEMBLY_ID)
            assert len(server.requests) == 2
    asyncio.run(scenario())


def test_async_environment_proxy_preserves_proxy_netrc_only(monkeypatch, tmp_path):
    netrc = tmp_path / "netrc"
    netrc.write_text("machine 127.0.0.1 login proxy-user password proxy-password\nmachine 127.0.0.2 login origin-user password must-not-leak\n")
    monkeypatch.setenv("NETRC", str(netrc))
    monkeypatch.delenv("http_proxy", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.setenv("NO_PROXY", "")
    async def scenario():
        async with wire_client("async") as (client, server):
            monkeypatch.setenv("HTTP_PROXY", server.url)
            client.service = "http://127.0.0.2:1"
            await client.get_assembly(assembly_id=ASSEMBLY_ID)
            await client.cancel_assembly(assembly_id=ASSEMBLY_ID)
            for request in server.requests:
                assert request["headers"]["Proxy-Authorization"] == aiohttp.BasicAuth("proxy-user", "proxy-password").encode()
            assert "Authorization" not in server.requests[0]["headers"]
            assert "Authorization" not in server.requests[1]["headers"]
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("filename", ["my photo.jpg", "caf\u00e9.jpg", "quote\"name.txt", "newline\r\nname.txt"])
def test_multipart_preserves_original_filename(mode, filename):
    async def scenario():
        async with wire_client(mode) as (client, server):
            upload = io.BytesIO(b"data")
            upload.name = filename
            assembly = client.new_assembly()
            assembly.add_file(upload)
            if mode == "async":
                await assembly.create(resumable=False)
            else:
                await asyncio.to_thread(assembly.create, resumable=False)
            # Quoting must prevent header injection while preserving spaces/UTF-8.
            expected = filename.replace("\r", "%0D").replace("\n", "%0A").replace('"', '%22')
            assert server.requests[-1]["filenames"]["file"] == expected
            assert not upload.closed
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_multipart_field_names_cannot_inject_headers(mode):
    async def scenario():
        async with wire_client(mode) as (client, server):
            options = {"files": {"file\r\nname": io.BytesIO(b"data")},
                       "extra_data": {"quoted\"field": "value"}}
            if mode == "async":
                await client.request.post("/assemblies", **options)
            else:
                await asyncio.to_thread(client.request.post, "/assemblies", **options)
            assert server.requests[-1]["fields"]["file%0D%0Aname"] == b"data"
            assert server.requests[-1]["fields"]["quoted%22field"] == "value"
    asyncio.run(scenario())


@asynccontextmanager
async def wire_client(mode):
    server = WireServer()
    app = web.Application()
    app.router.add_route("*", "/{path:.*}", server.handle)
    runner = web.AppRunner(app, shutdown_timeout=.1)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    server.url = "http://127.0.0.1:" + str(site._server.sockets[0].getsockname()[1])
    cls = Transloadit if mode == "sync" else AsyncTransloadit
    client = cls("key", "secret", service=server.url)
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
