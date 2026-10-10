import asyncio
import base64
import contextvars
from functools import partial
import os
import re


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


def encode_upload_metadata(fieldname, filename, user_meta):
    metadata = {str(key): str(value) for key, value in (user_meta or {}).items()}
    metadata.update({"fieldname": fieldname, "filename": filename})
    for key in metadata:
        if not re.fullmatch(r"[!-~]+", key) or "," in key or key == "assembly_url":
            raise ValueError("Invalid or reserved TUS metadata key.")
    return ",".join(key + " " + base64.b64encode(str(value).encode()).decode("ascii")
                    for key, value in metadata.items())


def check_assembly_created(response):
    if not isinstance(response.data, dict):
        raise RuntimeError(f"Assembly creation returned non-JSON data (HTTP {response.status_code}).")
    if not 200 <= response.status_code < 300 or response.data.get("error"):
        error = response.data.get("error", "UNKNOWN_ERROR")
        raise RuntimeError(f"Assembly creation failed: {error} (HTTP {response.status_code}).")


def get_upload_filename(file_stream, fallback):
    name = getattr(file_stream, "name", None)
    if isinstance(name, (bytes, os.PathLike)):
        name = os.fsdecode(name)

    if isinstance(name, str):
        filename = os.path.basename(name)
        if filename:
            return filename
    return fallback
