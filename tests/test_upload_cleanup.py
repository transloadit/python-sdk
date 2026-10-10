import asyncio
import io
import threading

import pytest

from transloadit.async_client import AsyncTransloadit


def test_multipart_cancellation_drains_worker_before_releasing_file():
    async def scenario():
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        class SlowStream(io.BytesIO):
            def read(self, *args):
                started.set()
                release.wait(10)
                try:
                    return super().read(*args)
                finally:
                    finished.set()
        class Writer:
            async def write(self, chunk):
                pass
        class Context:
            def __init__(self, data):
                self.payload = data()
            async def __aenter__(self):
                await self.payload.write(Writer())
                raise AssertionError("Expected cancellation")
            async def __aexit__(self, *args):
                await self.payload.close()
        class Session:
            closed = False
            def post(self, url, **kwargs):
                return Context(kwargs["data"])
        upload = SlowStream(b"payload")
        client = AsyncTransloadit("key", "secret", session=Session())
        task = asyncio.create_task(client.create_assembly(files={"file": upload}))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(.02)
            task.cancel()
            await asyncio.sleep(.02)
            assert not task.done(), "Cancellation returned while the caller's stream was still in use"
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await asyncio.to_thread(finished.wait, 5)
            upload.close()
    asyncio.run(scenario())


def test_repeated_cancellation_still_drains_tus_worker():
    async def scenario():
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        client = AsyncTransloadit("key", "secret")
        assembly = client.new_assembly()
        def upload(*args):
            started.set()
            release.wait(10)
            finished.set()
        assembly._do_tus_upload = upload
        task = asyncio.create_task(assembly._do_tus_upload_async("assembly", "upload", 3))
        try:
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(.02)
            task.cancel()
            await asyncio.sleep(.02)
            assert not task.done(), "Repeated cancellation released a running TUS worker"
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert await asyncio.to_thread(finished.wait, 5)
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["tus", "multipart"])
def test_global_event_loop_shutdown_keeps_files_open_until_workers_finish(mode):
    started, release = threading.Event(), threading.Event()
    errors = []
    class Stream(io.BytesIO):
        def read(self, *args):
            started.set()
            release.wait(5)
            try:
                return super().read(*args)
            except ValueError as error:
                errors.append(str(error))
                raise
    class Writer:
        async def write(self, chunk):
            pass
    class Context:
        def __init__(self, data):
            self.payload = data()
        async def __aenter__(self):
            await self.payload.write(Writer())
            raise AssertionError("Expected cancellation")
        async def __aexit__(self, *args):
            await self.payload.close()
    class Session:
        closed = False
        def post(self, url, **kwargs):
            return Context(kwargs["data"])
    stream = Stream(b"payload")
    async def main():
        client = AsyncTransloadit("key", "secret", session=Session())
        assembly = client.new_assembly()
        assembly._do_tus_upload = lambda *args: stream.read()
        async def upload():
            with stream:
                if mode == "tus":
                    await assembly._do_tus_upload_async("assembly", "upload", 3)
                else:
                    await client.create_assembly(files={"file": stream})
        task = asyncio.create_task(upload())
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        await asyncio.sleep(.02)  # Enter cleanup before asyncio.run cancels all remaining tasks.
        asyncio.get_running_loop().call_later(.05, release.set)
        # Returning triggers real asyncio.run shutdown, including child-task cancellation.
    try:
        asyncio.run(main())
    finally:
        release.set()
    assert stream.closed
    assert errors == [], "A worker read the caller's file after loop shutdown closed it"
