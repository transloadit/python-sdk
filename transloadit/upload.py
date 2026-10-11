import asyncio
import contextvars
from functools import partial
import os


async def run_upload_worker(function, *args):
    """Run and drain a worker, including during global event-loop shutdown."""
    context = contextvars.copy_context()
    # Executor futures are not Tasks cancelled by asyncio.run's global shutdown.
    # Shielding this private future therefore tracks actual thread completion.
    future = asyncio.get_running_loop().run_in_executor(None, partial(context.run, function, *args))
    cancelled = False
    while not future.done():
        try:
            await asyncio.shield(future)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        if not future.cancelled():
            future.exception()  # Retrieve a worker failure while preserving cancellation.
        raise asyncio.CancelledError
    return future.result()


def get_upload_filename(file_stream, fallback):
    name = getattr(file_stream, "name", None)
    if isinstance(name, (bytes, os.PathLike)):
        name = os.fsdecode(name)

    if isinstance(name, str):
        filename = os.path.basename(name)
        if filename:
            return filename
    return fallback
