import asyncio
import mimetypes
import os
import copy
import hashlib
import hmac
import json
from types import MappingProxyType
from datetime import datetime, timedelta, timezone

import aiohttp

from . import __version__
from .response import Response

TIMEOUT = 60


def _get_upload_filename(file_stream, fallback):
    name = getattr(file_stream, "name", None)
    if isinstance(name, (bytes, os.PathLike)):
        name = os.fsdecode(name)

    if isinstance(name, str):
        filename = os.path.basename(name)
        if filename:
            return filename
    return fallback


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
        # Large uploads can legitimately wait longer than TIMEOUT for the first response byte.
        sock_read = None if files else TIMEOUT
        return aiohttp.ClientTimeout(
            total=None,
            sock_connect=TIMEOUT,
            sock_read=sock_read,
        )

    def _normalize_payload(self, data):
        normalized = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            else:
                normalized[key] = str(value)
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
        session = await self._ensure_session()
        async with session.get(
            self._get_full_url(path),
            params=self._to_payload(params),
            headers=self._headers(),
            timeout=self._timeout(),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=dict(response.headers),
            )

    async def post(self, path, data=None, extra_data=None, files=None):
        """
        Makes an asynchronous HTTP POST request.
        """
        session = await self._ensure_session()
        data = self._to_payload(data)
        if extra_data:
            data.update(extra_data)

        if files:
            form = aiohttp.FormData()
            for key, value in self._normalize_payload(data).items():
                form.add_field(key, value)

            for key, file_stream in files.items():
                filename = _get_upload_filename(file_stream, key)
                content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                form.add_field(key, file_stream, filename=filename, content_type=content_type)
            payload = form
        else:
            payload = self._normalize_payload(data)

        async with session.post(
            self._get_full_url(path),
            data=payload,
            headers=self._headers(),
            timeout=self._timeout(files=bool(files)),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=dict(response.headers),
            )

    async def put(self, path, data=None):
        """
        Makes an asynchronous HTTP PUT request.
        """
        session = await self._ensure_session()
        data = self._normalize_payload(self._to_payload(data))
        async with session.put(
            self._get_full_url(path),
            data=data,
            headers=self._headers(),
            timeout=self._timeout(),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=dict(response.headers),
            )

    async def delete(self, path, data=None):
        """
        Makes an asynchronous HTTP DELETE request.
        """
        session = await self._ensure_session()
        data = self._normalize_payload(self._to_payload(data))
        async with session.delete(
            self._get_full_url(path),
            data=data,
            headers=self._headers(),
            timeout=self._timeout(),
        ) as response:
            return Response(
                data=await self._read_response_data(response),
                status_code=response.status,
                headers=dict(response.headers),
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
            return url
        return self.transloadit.service + url
