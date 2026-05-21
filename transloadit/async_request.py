import asyncio
import copy
import hashlib
import hmac
import io
import json
import mimetypes
import os
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import aiohttp
from requests.structures import CaseInsensitiveDict

from . import __version__
from .api_url import should_sign_api_url
from .response import Response
from .upload import get_upload_filename

TIMEOUT = 60


class _NonClosingUploadStream(io.IOBase):
    def __init__(self, file_stream):
        self._file_stream = file_stream

    @property
    def name(self):
        return getattr(self._file_stream, "name", None)

    def close(self):
        pass

    def fileno(self):
        return self._file_stream.fileno()

    def read(self, *args):
        return self._file_stream.read(*args)

    def readable(self):
        readable = getattr(self._file_stream, "readable", None)
        if callable(readable):
            try:
                return readable()
            except (OSError, ValueError):
                return False
        return hasattr(self._file_stream, "read")

    def readline(self, *args):
        return self._file_stream.readline(*args)

    def readlines(self, *args):
        return self._file_stream.readlines(*args)

    def seek(self, *args):
        return self._file_stream.seek(*args)

    def seekable(self):
        seekable = getattr(self._file_stream, "seekable", None)
        if callable(seekable):
            try:
                return seekable()
            except (OSError, ValueError):
                return False
        return hasattr(self._file_stream, "seek")

    def tell(self):
        return self._file_stream.tell()


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
        session = await self._ensure_session()
        async with session.get(
            url,
            params=self._to_request_payload(url, params),
            headers=self._headers(),
            timeout=self._timeout(),
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
        url = self._get_full_url(path)
        session = await self._ensure_session()
        data = self._to_request_payload(url, data) or {}
        if extra_data:
            data.update(extra_data)

        if files:
            form = aiohttp.FormData()
            for key, value in self._normalize_payload(data):
                form.add_field(key, value)

            for key, file_stream in files.items():
                filename = get_upload_filename(file_stream, key)
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(
                    key,
                    _NonClosingUploadStream(file_stream),
                    filename=filename,
                    content_type=content_type,
                )
            payload = form
        else:
            payload = self._normalize_payload(data)

        async with session.post(
            url,
            data=payload,
            headers=self._headers(),
            timeout=self._timeout(),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=CaseInsensitiveDict(response.headers),
            )

    async def put(self, path, data=None):
        """
        Makes an asynchronous HTTP PUT request.
        """
        url = self._get_full_url(path)
        session = await self._ensure_session()
        data = self._normalize_payload(self._to_request_payload(url, data) or {})
        async with session.put(
            url,
            data=data,
            headers=self._headers(),
            timeout=self._timeout(),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=CaseInsensitiveDict(response.headers),
            )

    async def delete(self, path, data=None):
        """
        Makes an asynchronous HTTP DELETE request.
        """
        url = self._get_full_url(path)
        session = await self._ensure_session()
        data = self._normalize_payload(self._to_request_payload(url, data) or {})
        async with session.delete(
            url,
            data=data,
            headers=self._headers(),
            timeout=self._timeout(),
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
