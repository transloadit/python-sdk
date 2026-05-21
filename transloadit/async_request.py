import asyncio
import io
import mimetypes
import os
import copy
import hashlib
import hmac
import json
from types import MappingProxyType
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import aiohttp
from requests.structures import CaseInsensitiveDict

from . import __version__
from .response import Response

TIMEOUT = 60


def _is_transloadit_host(hostname):
    return hostname == "transloadit.com" or hostname.endswith(".transloadit.com")


def _get_upload_filename(file_stream, fallback):
    name = getattr(file_stream, "name", None)
    if isinstance(name, (bytes, os.PathLike)):
        name = os.fsdecode(name)

    if isinstance(name, str):
        filename = os.path.basename(name)
        if filename:
            return filename
    return fallback


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
        return True

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

    def _timeout(self, files=False):
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
                if isinstance(item, bool):
                    normalized.append((key, "true" if item else "false"))
                else:
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
            params=self._to_payload(params),
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
        data = self._to_payload(data)
        if extra_data:
            data.update(extra_data)

        if files:
            form = aiohttp.FormData()
            for key, value in self._normalize_payload(data):
                form.add_field(key, value)

            for key, file_stream in files.items():
                filename = _get_upload_filename(file_stream, key)
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
            timeout=self._timeout(files=bool(files)),
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
        data = self._normalize_payload(self._to_payload(data))
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
        data = self._normalize_payload(self._to_payload(data))
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
        auth = data.get("auth") if isinstance(data.get("auth"), dict) else {}
        auth.update({
            "key": self.transloadit.auth_key,
            "expires": expiry.strftime("%Y/%m/%d %H:%M:%S+00:00"),
        })
        data["auth"] = auth
        json_data = json.dumps(data)
        return {"params": json_data, "signature": self._sign_data(json_data)}

    def _sign_data(self, message):
        hash_string = hmac.new(
            self.transloadit.auth_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha384
        ).hexdigest()
        return f"sha384:{hash_string}"

    def _get_full_url(self, url):
        if url.startswith(("http://", "https://")):
            service = urlparse(self.transloadit.service)
            target = urlparse(url)
            same_origin = (target.scheme, target.netloc) == (service.scheme, service.netloc)
            transloadit_origin = (
                target.scheme == service.scheme
                and _is_transloadit_host(service.hostname or "")
                and _is_transloadit_host(target.hostname or "")
            )
            if not (same_origin or transloadit_origin):
                raise ValueError("Absolute API URLs must use the configured Transloadit service origin.")
            return url
        return self.transloadit.service + url
