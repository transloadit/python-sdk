import asyncio
import base64
from typing import Optional
from urllib.parse import quote, urljoin

from . import async_assembly, async_request, async_template
from .api_url import normalize_service_url, require_path_id
from .smart_cdn import URL_PARAM_VALUES, build_signed_smart_cdn_url


class AsyncTransloadit:
    """
    Asynchronous client interface to the Transloadit API.
    """

    def __init__(
        self,
        auth_key: str,
        auth_secret: str,
        service: str = "https://api2.transloadit.com",
        duration: int = 300,
        session=None,
    ):
        self.service = normalize_service_url(service)
        self.auth_key = auth_key
        self.auth_secret = auth_secret
        self.duration = duration
        self.request = async_request.AsyncRequest(self, session=session)

    async def __aenter__(self):
        await self.request._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def aclose(self):
        await self.request.aclose()

    async def close(self):
        await self.aclose()

    def new_assembly(self, params: dict = None) -> async_assembly.AsyncAssembly:
        """
        Return an instance of <transloadit.async_assembly.AsyncAssembly>.
        """
        return async_assembly.AsyncAssembly(self, options=params)

    # <api2-generated-endpoints>
    # This block is generated from Transloadit API2 contracts. If it looks wrong,
    # please report the issue instead of editing this block by hand; the source fix
    # belongs in the contract generator so all SDKs stay in sync.

    def _quote_path_segment(self, value: str) -> str:
        value = str(value)
        if value in (".", ".."):
            raise ValueError("Path parameters cannot be dot segments.")

        return quote(value, safe="")

    async def _request_assembly_url(self, url, method, params=None):
        from urllib.parse import urlparse

        if "://" in url and not url.startswith(("http://", "https://")):
            raise ValueError("Invalid Assembly URL.")
        candidate_url = (
            url
            if url.startswith(("http://", "https://"))
            else self.service.rstrip("/") + "/" + url.lstrip("/")
        )
        try:
            candidate = urlparse(candidate_url)
            configured = urlparse(self.service)
            candidate_port = candidate.port or (443 if candidate.scheme == "https" else 80)
            configured_port = configured.port or (443 if configured.scheme == "https" else 80)
        except ValueError as error:
            raise ValueError("Invalid Assembly URL.") from error

        candidate_hostname = (candidate.hostname or "").lower()
        configured_hostname = (configured.hostname or "").lower()
        has_url_credentials = candidate.username is not None or candidate.password is not None
        configured_origin = (
            not has_url_credentials
            and candidate.scheme == configured.scheme
            and candidate_hostname == configured_hostname
            and candidate_port == configured_port
        )
        configured_https_host = (
            not has_url_credentials
            and candidate.scheme == "https"
            and candidate_port == 443
            and candidate_hostname != ""
            and candidate_hostname == configured_hostname
        )
        api2_cell = (
            not has_url_credentials
            and candidate.scheme == "https"
            and candidate_port == 443
            and candidate_hostname.startswith("api2-")
            and candidate_hostname.endswith(".transloadit.com")
        )
        if not (configured_origin or configured_https_host or api2_cell):
            raise ValueError("Refusing to request an untrusted Assembly URL.")
        if method not in {"GET", "DELETE"}:
            raise ValueError(f"Unsupported Assembly URL method: {method}")

        session = await self.request._ensure_session()
        async with session.request(
            method,
            candidate_url,
            params=params,
            headers=self.request._headers(),
            timeout=self.request._timeout(),
            allow_redirects=False,
        ) as raw_response:
            from .response import Response

            return Response(
                data=await self.request._read_response_data(raw_response),
                status_code=raw_response.status,
                headers=raw_response.headers,
            )

    async def create_assembly(self, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create a new Assembly.
        """
        return await self.request.post("/assemblies", data=data, extra_data=extra_data, files=files)

    async def create_assembly_with_id(self, assembly_id: str, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create an Assembly with a chosen ID.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assemblies/{self._quote_path_segment(assembly_id)}", data=data, extra_data=extra_data, files=files)

    async def list_assemblies(self, params: Optional[dict] = None):
        """
        Retrieve list of Assemblies.
        """
        return await self.request.get("/assemblies", params=params)

    async def get_assembly(self, assembly_id: str = None, assembly_url: str = None, params: Optional[dict] = None):
        """
        Retrieve an Assembly Status.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return await self._request_assembly_url(url, "GET", params=params)

    async def cancel_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Cancel a running Assembly.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return await self._request_assembly_url(url, "DELETE")

    async def replay_assembly(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay an Assembly.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assemblies/{self._quote_path_segment(assembly_id)}/replay", data=data)

    async def replay_assembly_notification(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay Assembly Notification.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assembly_notifications/{self._quote_path_segment(assembly_id)}/replay", data=data)

    async def list_assembly_notifications(self, assembly_id: str):
        """
        Retrieve Assembly Notifications.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.get(f"/assembly_notifications/{self._quote_path_segment(assembly_id)}")

    async def get_bill(self, month: int, year: int, params: Optional[dict] = None):
        """
        Retrieve a month’s bill.
        """
        return await self.request.get(f"/bill/{year}-{month:02d}", params=params)

    async def get_bill_for_invoice(self, date: str, invoice_id: str, params: Optional[dict] = None):
        """
        Retrieve an invoice’s bill.
        """
        date = require_path_id(date, "date")
        invoice_id = require_path_id(invoice_id, "invoice_id")

        return await self.request.get(f"/bill/{self._quote_path_segment(date)}/{self._quote_path_segment(invoice_id)}", params=params)

    async def list_templates(self, params: Optional[dict] = None):
        """
        Retrieve list of Templates.
        """
        return await self.request.get("/templates", params=params)

    async def create_template(self, data: Optional[dict] = None):
        """
        Create a new Template.
        """
        return await self.request.post("/templates", data=data)

    async def get_template_full(self, template_id_or_name: str, params: Optional[dict] = None):
        """
        Retrieve full Template details.
        """
        template_id_or_name = require_path_id(template_id_or_name, "template_id_or_name")

        return await self.request.get(f"/templates/{self._quote_path_segment(template_id_or_name)}/full", params=params)

    async def get_builtin_template_full(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Retrieve full built-in Template details.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return await self.request.get(f"/templates/builtin/{self._quote_path_segment(builtin_template_slug)}/full", params=params)

    async def get_template(self, template_id: str, params: Optional[dict] = None):
        """
        Retrieve a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return await self.request.get(f"/templates/{self._quote_path_segment(template_id)}", params=params)

    async def get_builtin_template(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Retrieve a built-in Template.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return await self.request.get(f"/templates/builtin/{self._quote_path_segment(builtin_template_slug)}", params=params)

    async def update_template(self, template_id: str, data: Optional[dict] = None):
        """
        Edit a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return await self.request.put(f"/templates/{self._quote_path_segment(template_id)}", data=data)

    async def delete_template(self, template_id: str, data: Optional[dict] = None):
        """
        Delete a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return await self.request.delete(f"/templates/{self._quote_path_segment(template_id)}", data=data)

    async def list_priority_job_slots(self, params: Optional[dict] = None):
        """
        Retrieve currently used priority job slots.
        """
        return await self.request.get("/queues/job_slots", params=params)

    async def issue_bearer_token(self, data: Optional[dict] = None):
        """
        Create a bearer token.
        """
        if not self.auth_secret:
            raise ValueError("Bearer token issuance requires an auth secret.")

        from ipaddress import ip_address
        from urllib.parse import urlparse

        endpoint = urlparse(self.service)
        try:
            loopback = endpoint.hostname == "localhost" or ip_address(
                endpoint.hostname or ""
            ).is_loopback
        except ValueError:
            loopback = False
        if (
            endpoint.username is not None
            or endpoint.password is not None
            or not (endpoint.scheme == "https" or (endpoint.scheme == "http" and loopback))
        ):
            raise ValueError("Refusing to send credentials to an insecure bearer token endpoint.")

        data = data or {}
        form_data = {}
        if data.get("aud") is not None:
            form_data["aud"] = data["aud"]
        form_data["grant_type"] = "client_credentials"
        if data.get("scope") is not None:
            form_data["scope"] = data["scope"]

        credentials = base64.b64encode(
            f"{self.auth_key}:{self.auth_secret}".encode("utf-8")
        ).decode("ascii")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        headers.update(self.request._headers())
        session = await self.request._ensure_session()
        async with session.post(
            self.service.rstrip("/") + "/token",
            data=form_data,
            headers=headers,
            timeout=self.request._timeout(),
            allow_redirects=False,
        ) as raw_response:
            from .response import Response

            return Response(
                data=await self.request._read_response_data(raw_response),
                status_code=raw_response.status,
                headers=raw_response.headers,
            )

    async def list_template_credentials(self, params: Optional[dict] = None):
        """
        Retrieve list of Template Credentials.
        """
        return await self.request.get("/template_credentials", params=params)

    async def list_template_credential_types(self, params: Optional[dict] = None):
        """
        Retrieve Template Credential types.
        """
        return await self.request.get("/template_credentials/types", params=params)

    async def validate_template_credential_oauth_on_create(self, data: Optional[dict] = None):
        """
        Validate an OAuth Template Credential name.
        """
        return await self.request.post("/template_credentials/validateOauthOnCreate", data=data)

    async def create_template_credentials(self, data: Optional[dict] = None):
        """
        Create a new Template Credential.
        """
        return await self.request.post("/template_credentials", data=data)

    async def get_template_credentials(self, identifier: str, params: Optional[dict] = None):
        """
        Retrieve a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.get(f"/template_credentials/{self._quote_path_segment(identifier)}", params=params)

    async def delete_template_credentials(self, identifier: str, data: Optional[dict] = None):
        """
        Delete a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.delete(f"/template_credentials/{self._quote_path_segment(identifier)}", data=data)

    async def update_template_credentials(self, identifier: str, data: Optional[dict] = None):
        """
        Edit a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.put(f"/template_credentials/{self._quote_path_segment(identifier)}", data=data)

    # </api2-generated-endpoints>

    # <api2-generated-features>
    # This block is generated from Transloadit API2 contracts. If it looks wrong,
    # please report the issue instead of editing this block by hand; the source fix
    # belongs in the contract generator so all SDKs stay in sync.

    async def create_tus_assembly(self, file_count: int):
        """
        Creates a TUS-ready Assembly that waits for the requested number of resumable uploads before execution continues.
        """
        assembly = await self.create_assembly(
            data={
                "await": False,
                "steps": {
                    ":original": {
                        "output_meta": True,
                        "result": "debug",
                        "robot": "/upload/handle",
                    },
                },
            },
            extra_data={
                "num_expected_upload_files": file_count,
            },
        )

        return assembly

    async def resume_tus_upload(self, upload_url: str, content: bytes, assembly_ssl_url: str):
        """
        Resumes an interrupted TUS upload from the server-reported offset and waits for the Assembly to finish.
        """
        stored_upload_url = upload_url
        if not stored_upload_url:
            raise RuntimeError("TUS resumeUpload needs input.storedUploadUrl")

        session = await self.request._ensure_session()

        offset_headers = {}
        offset_headers["Tus-Resumable"] = "1.0.0"
        async with session.request(
            "HEAD",
            stored_upload_url,
            data=b"",
            headers=offset_headers,
            timeout=self.request._timeout(),
        ) as offset_response:
            if offset_response.status != 200:
                raise RuntimeError(f"TUS offset returned HTTP {offset_response.status}, expected 200")
            resume_offset_header = offset_response.headers.get("Upload-Offset")
            if not resume_offset_header:
                raise RuntimeError("TUS offset did not return a Upload-Offset header")
            try:
                resume_offset = int(resume_offset_header)
            except ValueError as error:
                raise RuntimeError("TUS offset returned an invalid Upload-Offset header") from error

        upload_headers = {}
        upload_headers["Tus-Resumable"] = "1.0.0"
        upload_headers["Upload-Offset"] = str(resume_offset)
        upload_headers["Content-Type"] = "application/offset+octet-stream"
        async with session.request(
            "PATCH",
            stored_upload_url,
            data=content[resume_offset:],
            headers=upload_headers,
            timeout=self.request._timeout(),
        ) as upload_response:
            if upload_response.status != 204:
                raise RuntimeError(f"TUS upload returned HTTP {upload_response.status}, expected 204")
            try:
                upload_offset = int(upload_response.headers.get("Upload-Offset", ""))
            except ValueError as error:
                raise RuntimeError("TUS upload returned an invalid Upload-Offset header") from error
            if upload_offset != len(content):
                raise RuntimeError(f"TUS upload offset {upload_offset}, expected {len(content)}")

        completed_assembly = await self.wait_for_assembly(assembly_ssl_url)

        return completed_assembly

    async def upload_tus_assembly(self, content: bytes, fieldname: str, filename: str, user_meta: Optional[dict] = None):
        """
        Creates a TUS-ready Assembly, uploads one file with the TUS protocol, and waits for the Assembly to finish.
        """
        created_assembly = await self.create_tus_assembly(1)

        endpoint_url = created_assembly.data.get("tus_url")
        if not endpoint_url:
            raise RuntimeError("TUS singleUploadLifecycle needs input.endpointUrl")

        metadata_map = {}
        if user_meta:
            metadata_map.update({str(key): str(value) for key, value in user_meta.items()})
        metadata_map["assembly_url"] = str(created_assembly.data.get("assembly_ssl_url"))
        metadata_map["fieldname"] = str(fieldname)
        metadata_map["filename"] = str(filename)

        session = await self.request._ensure_session()

        create_headers = {}
        create_headers["Tus-Resumable"] = "1.0.0"
        create_headers["Upload-Length"] = str(len(content))
        create_metadata_parts = []
        for key, value in metadata_map.items():
            encoded_value = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
            create_metadata_parts.append(f"{key} {encoded_value}")
        create_headers["Upload-Metadata"] = ",".join(create_metadata_parts)
        async with session.request(
            "POST",
            endpoint_url,
            data=b"",
            headers=create_headers,
            timeout=self.request._timeout(),
        ) as create_response:
            if create_response.status != 201:
                raise RuntimeError(f"TUS create returned HTTP {create_response.status}, expected 201")
            upload_url_location = create_response.headers.get("Location")
            if not upload_url_location:
                raise RuntimeError("TUS create did not return a Location header")
            upload_url_text = urljoin(endpoint_url, upload_url_location)

        upload_headers = {}
        upload_headers["Tus-Resumable"] = "1.0.0"
        upload_headers["Upload-Offset"] = "0"
        upload_headers["Content-Type"] = "application/offset+octet-stream"
        async with session.request(
            "PATCH",
            upload_url_text,
            data=content,
            headers=upload_headers,
            timeout=self.request._timeout(),
        ) as upload_response:
            if upload_response.status != 204:
                raise RuntimeError(f"TUS upload returned HTTP {upload_response.status}, expected 204")
            try:
                upload_offset = int(upload_response.headers.get("Upload-Offset", ""))
            except ValueError as error:
                raise RuntimeError("TUS upload returned an invalid Upload-Offset header") from error
            if upload_offset != len(content):
                raise RuntimeError(f"TUS upload offset {upload_offset}, expected {len(content)}")

        created_assembly_assembly_ssl_url = created_assembly.data.get("assembly_ssl_url")
        if not created_assembly_assembly_ssl_url:
            raise RuntimeError("uploadTusAssembly needs createdAssembly.assembly_ssl_url")
        completed_assembly = await self.wait_for_assembly(created_assembly_assembly_ssl_url)

        return completed_assembly, upload_url_text

    async def wait_for_assembly(self, assembly_url: str):
        """
        Waits for an Assembly to finish uploading and executing.
        Use the returned assembly_ssl_url as the assembly URL.
        """
        while True:
            response = await self.get_assembly(assembly_url=assembly_url)
            data = response.data

            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected non-JSON response ({response.status_code}).")

            # Abort polling if the assembly has entered an error state
            if data.get("error"):
                return response

            # The polling is done if the assembly is not uploading or executing anymore.
            if data.get("ok") not in ("ASSEMBLY_UPLOADING", "ASSEMBLY_EXECUTING"):
                return response

            await asyncio.sleep(1)

    # </api2-generated-features>

    def new_template(self, name: str, params: Optional[dict] = None) -> async_template.AsyncTemplate:
        """
        Return an instance of <transloadit.async_template.AsyncTemplate>.
        """
        return async_template.AsyncTemplate(self, name, options=params)

    def get_signed_smart_cdn_url(
        self,
        workspace: str,
        template: str,
        input: str,
        url_params: Optional[dict[str, URL_PARAM_VALUES]] = None,
        expires_at_ms: Optional[int] = None,
    ) -> str:
        """
        Construct a signed Smart CDN URL.
        """
        return build_signed_smart_cdn_url(
            auth_key=self.auth_key,
            auth_secret=self.auth_secret,
            workspace=workspace,
            template=template,
            input=input,
            url_params=url_params,
            expires_at_ms=expires_at_ms,
        )
