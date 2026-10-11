import asyncio
import copy
import hashlib
import hmac
import io
import json
import mimetypes
import os
import threading
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from types import MappingProxyType

import aiohttp
from requests.structures import CaseInsensitiveDict

from . import __version__
from .api_url import should_sign_api_url
from .network import async_network_options
from .response import Response
from .upload import get_upload_filename, run_upload_worker

TIMEOUT = 60


def _multipart_parameter(value):
    return str(value).replace("\r", "%0D").replace("\n", "%0A").replace('"', "%22")


class _NonClosingUploadStream(io.IOBase):
    def __init__(self, file_stream):
        self._file_stream = file_stream
        self._lock = threading.Lock()
        self._retired = threading.Event()

    def _call(self, method, *args):
        with self._lock:
            if self._retired.is_set():
                raise ValueError("Upload stream is no longer active.")
            return getattr(self._file_stream, method)(*args)

    def retire(self):
        # Prevent queued executor reads from touching the caller's file later.
        self._retired.set()

    def drain(self):
        # An in-flight blocking read holds this lock until it releases the file.
        with self._lock:
            pass

    @property
    def name(self):
        return getattr(self._file_stream, "name", None)

    def close(self):
        pass

    def fileno(self):
        return self._call("fileno")

    def read(self, *args):
        return self._call("read", *args)

    def readable(self):
        readable = getattr(self._file_stream, "readable", None)
        if callable(readable):
            try:
                return self._call("readable")
            except (OSError, ValueError):
                return False
        return hasattr(self._file_stream, "read")

    def readline(self, *args):
        return self._call("readline", *args)

    def readlines(self, *args):
        return self._call("readlines", *args)

    def seek(self, *args):
        return self._call("seek", *args)

    def seekable(self):
        seekable = getattr(self._file_stream, "seekable", None)
        if callable(seekable):
            try:
                return self._call("seekable")
            except (OSError, ValueError):
                return False
        return hasattr(self._file_stream, "seek")

    def tell(self):
        return self._call("tell")


class _NonClosingTextUploadStream(_NonClosingUploadStream, io.TextIOBase):
    # Preserve aiohttp's TextIOPayload selection and UTF-8 encoding of text reads.
    def fileno(self):
        # Disk byte size is not the encoded payload length (CRLF, UTF-16, etc.).
        # Unknown length makes aiohttp use chunked transfer without buffering.
        raise io.UnsupportedOperation("Text upload byte length is unknown.")


class AsyncRequest:
    """
    Transloadit tailored asynchronous HTTP request object.
    """

    HEADERS = MappingProxyType({"Transloadit-Client": "python-sdk:" + __version__})

    def __init__(self, transloadit, session=None):
        self.transloadit = transloadit
        self._session = session
        self._owns_session = session is None
        self._session_lock = None

    @property
    def session(self):
        return self._session

    def _headers(self):
        return dict(self.HEADERS)

    @asynccontextmanager
    async def _api_session(self, url):
        yield await self._ensure_session()

    async def _request_options(self, url):
        return {"headers": self._headers(), "timeout": self._timeout(), "allow_redirects": False}

    def _get_session_lock(self):
        if self._session_lock is None:
            # Create the lock lazily so the client can be instantiated before the loop starts.
            self._session_lock = asyncio.Lock()
        return self._session_lock

    async def _ensure_session(self):
        if self._session is not None and not self._session.closed:
            return self._session
        async with self._get_session_lock():
            if self._session is None:
                self._session = aiohttp.ClientSession(trust_env=True)
                self._owns_session = True
            elif self._session.closed:
                if self._owns_session:
                    self._session = aiohttp.ClientSession(trust_env=True)
                else:
                    raise RuntimeError("Injected aiohttp session is closed.")
            return self._session

    async def aclose(self):
        async with self._get_session_lock():
            if self._session is not None and not self._session.closed and self._owns_session:
                await self._session.close()
                self._session = None

    def _timeout(self):
        # Keep total disabled for large request bodies, but still cap stalled responses.
        return aiohttp.ClientTimeout(
            total=None,
            sock_connect=TIMEOUT,
            sock_read=TIMEOUT,
        )

    def _normalize_payload(self, data):
        normalized = []
        for key, value in data.items():
            if value is None:
                continue
            values = value if isinstance(value, (list, tuple)) else [value]
            for item in values:
                if item is None:
                    continue
                normalized.append((key, str(item)))
        return normalized

    async def _read_response_data(self, response):
        try:
            return await response.json(content_type=None)
        except (aiohttp.ContentTypeError, json.JSONDecodeError, UnicodeDecodeError):
            try:
                return await response.text()
            except UnicodeDecodeError:
                return await response.read()

    async def get(self, path, params=None):
        """
        Makes an asynchronous HTTP GET request.
        """
        url = self._get_full_url(path)
        async with self._api_session(url) as session, session.get(
            url,
            params=self._to_request_payload(url, params),
            **(await self._request_options(url)),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=CaseInsensitiveDict(response.headers),
            )

    async def post(self, path, data=None, extra_data=None, files=None):
        """
        Makes an asynchronous HTTP POST request.
        """
        return await self._form_request("post", path, data, extra_data, files)

    async def _form_request(self, method, path, data=None, extra_data=None, files=None):
        url = self._get_full_url(path)
        data = self._to_request_payload(url, data) or {}
        if extra_data:
            data.update(extra_data)

        uploads = []
        if files:
            # Retain spaces/UTF-8; escape CR/LF/quotes as Requests does. aiohttp
            # additionally escapes backslashes, which API2 decodes equivalently.
            form = aiohttp.FormData(quote_fields=False)
            for key, value in self._normalize_payload(data):
                form.add_field(_multipart_parameter(key), value)

            for key, file_stream in files.items():
                wrapper = _NonClosingTextUploadStream if isinstance(file_stream, io.TextIOBase) else _NonClosingUploadStream
                upload = wrapper(file_stream)
                uploads.append(upload)
                filename = get_upload_filename(file_stream, key)
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(
                    _multipart_parameter(key),
                    upload,
                    filename=_multipart_parameter(filename),
                    content_type=content_type,
                )
            payload = form
        else:
            payload = self._normalize_payload(data)

        try:
            async with self._api_session(url) as session, getattr(session, method)(
                url,
                data=payload,
                **(await self._request_options(url)),
            ) as response:
                return Response(
                    data=await self._read_response_data(response),
                    status_code=response.status,
                    headers=CaseInsensitiveDict(response.headers),
                )
        finally:
            if uploads:
                for upload in uploads:
                    upload.retire()
                def drain():
                    for upload in uploads:
                        upload.drain()
                await run_upload_worker(drain)

    async def put(self, path, data=None, extra_data=None, files=None):
        """
        Makes an asynchronous HTTP PUT request.
        """
        return await self._form_request("put", path, data, extra_data, files)

    async def delete(self, path, data=None):
        """
        Makes an asynchronous HTTP DELETE request.
        """
        url = self._get_full_url(path)
        data = self._normalize_payload(self._to_request_payload(url, data) or {})
        async with self._api_session(url) as session, session.delete(
            url,
            data=data,
            **(await self._request_options(url)),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=CaseInsensitiveDict(response.headers),
            )

    def _to_payload(self, data):
        data = copy.deepcopy(data or {})
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self.transloadit.duration)
        if "auth" in data and not isinstance(data["auth"], dict):
            raise ValueError("auth must be a dictionary when provided.")
        auth = data.get("auth") or {}
        auth.update({
            "key": self.transloadit.auth_key,
            "expires": expiry.strftime("%Y/%m/%d %H:%M:%S+00:00"),
        })
        data["auth"] = auth
        json_data = json.dumps(data)
        return {"params": json_data, "signature": self._sign_data(json_data)}

    def _to_request_payload(self, url, data):
        if should_sign_api_url(url, self.transloadit.service):
            return self._to_payload(data)
        return copy.deepcopy(data) if data else None

    def _sign_data(self, message):
        hash_string = hmac.new(
            self.transloadit.auth_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha384
        ).hexdigest()
        return f"sha384:{hash_string}"

    def _get_full_url(self, url):
        if url.startswith(("http://", "https://")):
            return url
        return self.transloadit.service + url

    @asynccontextmanager
    async def _isolated_session(self):
        # Share DNS/TLS/pool configuration, never the session's cookies or auth.
        connector = getattr(self._session, "connector", None)
        if self._session is not None and self._session.closed and not self._owns_session:
            raise RuntimeError("Injected aiohttp session is closed.")
        async with aiohttp.ClientSession(connector=connector, connector_owner=connector is None,
                                         cookie_jar=aiohttp.DummyCookieJar(), trust_env=False) as session:
            yield session

    async def public(self, method, path, params=None, data=None):
        # A separate session prevents injected session cookies/auth from leaking
        # onto credential-free Assembly capability requests.
        url = self._get_full_url(path)
        async with self._isolated_session() as session:
            async with session.request(method, url, params=params, data=data,
                                       headers=self._headers(), timeout=self._timeout(), allow_redirects=False,
                                       **(await async_network_options(url, self._session))) as response:
                return Response(data=await self._read_response_data(response), status_code=response.status,
                                headers=CaseInsensitiveDict(response.headers))
