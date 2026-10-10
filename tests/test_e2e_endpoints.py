"""Opt-in test-account validation using the repository's existing E2E credentials."""
import asyncio
import base64
import os

import pytest

from transloadit.async_client import AsyncTransloadit
from transloadit.client import Transloadit
from .test_e2e_upload import _get_e2e_credentials, _is_enabled


pytestmark = [pytest.mark.e2e, pytest.mark.skipif(not _is_enabled(), reason="Set PYTHON_SDK_E2E=1")]


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_raw_tus_and_status_stream_lifecycle(mode):
    async def scenario():
        key, secret = _get_e2e_credentials()
        cls = Transloadit if mode == "sync" else AsyncTransloadit
        client = cls(key, secret, service=os.getenv("TRANSLOADIT_SERVICE", "https://api2.transloadit.com"))

        async def call(name, *args, **kwargs):
            if mode == "async":
                return await getattr(client, name)(*args, **kwargs)
            return await asyncio.to_thread(getattr(client, name), *args, **kwargs)

        assembly_url = None
        stream_task = None
        try:
            scopes = await call("list_auth_key_scopes")
            assert scopes.status_code == 200
            # Keep the Assembly waiting while its incomplete upload is tested/deleted.
            assembly = await call("create_tus_assembly", 2)
            assert assembly.status_code == 200
            assembly_url = assembly.data["assembly_ssl_url"]
            options = await call("tus_options", assembly)
            assert options.status_code in {200, 204}
            assert "1.0.0" in options.headers["Tus-Version"]
            metadata = "filename " + base64.b64encode(b"sdk-test.bin").decode() + ",fieldname " + base64.b64encode(b"file").decode()
            created = await call("create_upload", assembly, headers={"Upload-Length": "16", "Upload-Metadata": metadata})
            assert created.status_code == 201, created.data
            upload_url = created.upload_url
            offset = await call("get_upload_offset", upload_url)
            assert offset.status_code == 200 and offset.headers["Upload-Offset"] == "0"
            appended = await call("patch_upload", upload_url, headers={"Upload-Offset": "0"}, body=b"sdk-test")
            assert appended.status_code == 204 and appended.headers["Upload-Offset"] == "8"
            downloaded = await call("download_upload", upload_url, headers={"Range": "bytes=1-3"})
            assert downloaded.status_code == 206 and downloaded.data == b"dk-"
            deleted = await call("delete_upload", upload_url)
            assert deleted.status_code == 204

            opened = asyncio.Event()
            loop = asyncio.get_running_loop()
            stream_url = assembly.data["update_stream_url"]

            def consume_sync():
                with client.stream_assembly_status(stream_url, read_timeout=15) as events:
                    loop.call_soon_threadsafe(opened.set)
                    return list(events)

            async def consume_async():
                async with client.stream_assembly_status(stream_url, read_timeout=15) as events:
                    opened.set()
                    return [event async for event in events]

            stream_task = asyncio.create_task(consume_async() if mode == "async" else asyncio.to_thread(consume_sync))
            await asyncio.wait_for(opened.wait(), 20)
            canceled = await call("cancel_assembly", assembly_url=assembly_url)
            assert canceled.status_code == 200
            events = await asyncio.wait_for(asyncio.shield(stream_task), 20)
            assert any(event.terminal for event in events)
            status = await call("get_assembly", assembly_url=assembly_url)
            assert status.data["ok"] == "ASSEMBLY_CANCELED"
        finally:
            try:
                if assembly_url:
                    await call("cancel_assembly", assembly_url=assembly_url)
            finally:
                if stream_task:
                    # Sync stream reads have a finite timeout; await the owned worker.
                    await asyncio.gather(stream_task, return_exceptions=True)
                if mode == "async":
                    await client.aclose()
    asyncio.run(scenario())
