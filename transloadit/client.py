import base64
import typing
from time import sleep
from typing import Optional
from urllib.parse import quote

import requests

from . import assembly, request, template
from .api_url import normalize_service_url, require_path_id
from .smart_cdn import URL_PARAM_VALUES, build_signed_smart_cdn_url

if typing.TYPE_CHECKING:
    from requests import Response


class Transloadit:
    """
    This class serves as a client interface to the Transloadit API.

    :Attributes:
        - auth_key (str): Transloadit auth key.
        - auth_secret (str): Transloadit auth secret.
        - service (Optional[str]): URL of the Transloadit API.
        - duration (int): How long in seconds for which a Transloadit request should be valid.
        - request (transloadit.request.Request): An instance of the Transloadit HTTP Request object.

    :Constructor Args:
        - auth_key (str): Transloadit auth key.
        - auth_secret (str): Transloadit aut secret.
        - service (Optional[str]):
            Url of the Transloadit API. Defaults to 'https://api2.transloadit.com'
            if not specified.
        - duration (Optional[int]):
            How long in seconds for which a Transloadit request should be valid. Defaults to 300
            if not specified.
    """

    def __init__(
            self,
            auth_key: str,
            auth_secret: str,
            service: str = "https://api2.transloadit.com",
            duration: int = 300,
            *,
            bearer_token: str = None,
    ):
        self.service = normalize_service_url(service)
        self.auth_key = auth_key
        self.auth_secret = auth_secret
        self.duration = duration
        self.bearer_token = bearer_token
        self.request = request.Request(self)

    def new_assembly(self, params: dict = None) -> assembly.Assembly:
        """
        Return an instance of <transloadit.assembly.Assembly> which would be used to create
        a new assembly.
        """
        return assembly.Assembly(self, options=params)

    # Compatibility aliases and capability URL handling are maintained by hand.
    def _quote_path_segment(self, value: str) -> str:
        value = str(value)
        if value in (".", ".."):
            raise ValueError("Path parameters cannot be dot segments.")

        return quote(value, safe="")

    def _request_assembly_url(self, url, method, params=None):
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

        raw_response = requests.request(
            method,
            candidate_url,
            params=params,
            headers=request.Request.HEADERS,
            timeout=request.TIMEOUT,
            allow_redirects=False,
        )
        from .response import Response

        return Response(raw_response)

    def create_assembly_with_id(self, assembly_id: str, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create an Assembly with a chosen ID.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return self.request.post(f"/assemblies/{self._quote_path_segment(assembly_id)}", data=data, extra_data=extra_data, files=files)

    def get_bill_for_invoice(self, date: str, invoice_id: str, params: Optional[dict] = None):
        """
        Retrieve an invoice’s bill.
        """
        date = require_path_id(date, "date")
        invoice_id = require_path_id(invoice_id, "invoice_id")

        return self.request.get(f"/bill/{self._quote_path_segment(date)}/{self._quote_path_segment(invoice_id)}", params=params)

    def get_template_full(self, template_id_or_name: str, params: Optional[dict] = None):
        """
        Retrieve full Template details.
        """
        template_id_or_name = require_path_id(template_id_or_name, "template_id_or_name")

        return self.request.get(f"/templates/{self._quote_path_segment(template_id_or_name)}/full", params=params)

    def get_builtin_template_full(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Retrieve full built-in Template details.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return self.request.get(f"/templates/builtin/{self._quote_path_segment(builtin_template_slug)}/full", params=params)

    def get_builtin_template(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Retrieve a built-in Template.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return self.request.get(f"/templates/builtin/{self._quote_path_segment(builtin_template_slug)}", params=params)

    def validate_template_credential_oauth_on_create(self, data: Optional[dict] = None):
        """
        Validate an OAuth Template Credential name.
        """
        return self.request.post("/template_credentials/validateOauthOnCreate", data=data)

    # <api2-generated-endpoints>
    # Generated by scripts/generate_endpoints.py; edit the generator, not this block.

    def assembly_stats(self, params=None):
        """
        Retrieve Assembly statistics

        Contract operation: api2.assembly-stats.
        """
        return self.request.get('/assembly_stats', params=params)

    def bulk_delete_dam_assets(self, data=None):
        """
        Delete DAM assets in bulk

        Contract operation: api2.bulk-delete-dam-assets.
        Stage: alpha; this API may change.
        """
        return self.request.post('/dam/assets/bulk/delete', data=data)

    def bulk_move_dam_assets(self, data=None):
        """
        Move DAM assets in bulk

        Contract operation: api2.bulk-move-dam-assets.
        Stage: alpha; this API may change.
        """
        return self.request.post('/dam/assets/bulk/move', data=data)

    def cancel_assembly(self, assembly_id=None, assembly_url=None):
        """
        Cancel a running Assembly

        Contract operation: api2.cancel-assembly.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either assembly_id or assembly_url is required.")
        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return self._request_assembly_url(url, 'DELETE')

    def create_assembly(self, data=None, extra_data=None, files=None):
        """
        Create a new Assembly

        Contract operation: api2.create-assembly.
        """
        return self.request.post('/assemblies', data=data, extra_data=extra_data, files=files)

    def create_auth_key(self, data=None):
        """
        Create a new Auth Key

        Contract operation: api2.create-auth-key.
        """
        return self.request.post('/auth_keys', data=data)

    def create_template(self, data=None):
        """
        Create a new Template

        Contract operation: api2.create-template.
        """
        return self.request.post('/templates', data=data)

    def create_template_credentials(self, data=None):
        """
        Create a new Template Credential

        Contract operation: api2.create-template-credential.
        """
        return self.request.post('/template_credentials', data=data)

    def delete_auth_key(self, auth_key_id: str, data=None):
        """
        Delete an Auth Key

        Contract operation: api2.delete-auth-key.
        """
        auth_key_id = require_path_id(auth_key_id, 'auth_key_id')
        return self.request.delete(f'/auth_keys/{self._quote_path_segment(auth_key_id)}', data=data)

    def delete_dam_asset(self, asset_id: str, data=None):
        """
        Delete a DAM asset

        Contract operation: api2.delete-dam-asset.
        Stage: alpha; this API may change.
        """
        asset_id = require_path_id(asset_id, 'asset_id')
        return self.request.delete(f'/dam/assets/{self._quote_path_segment(asset_id)}', data=data)

    def delete_template(self, template_id: str, data=None):
        """
        Delete a Template

        Contract operation: api2.delete-template.
        """
        template_id = require_path_id(template_id, 'template_id')
        return self.request.delete(f'/templates/{self._quote_path_segment(template_id)}', data=data)

    def delete_template_credentials(self, identifier: str, data=None):
        """
        Delete a Template Credential

        Contract operation: api2.delete-template-credential.
        """
        identifier = require_path_id(identifier, 'identifier')
        return self.request.delete(f'/template_credentials/{self._quote_path_segment(identifier)}', data=data)

    def get_assembly(self, assembly_id=None, assembly_url=None, params=None):
        """
        Retrieve an Assembly Status

        Contract operation: api2.get-assembly.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either assembly_id or assembly_url is required.")
        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return self._request_assembly_url(url, 'GET', params=params)

    def get_bill(self, month: int, year: int, params=None):
        """
        Retrieve a month’s bill

        Contract operation: api2.get-bill.
        """
        return self.request.get(f'/bill/{year}-{month:02d}', params=params)

    def get_dam_asset(self, asset_id: str, params=None):
        """
        Retrieve a Storage asset

        Contract operation: api2.get-dam-asset.
        """
        asset_id = require_path_id(asset_id, 'asset_id')
        return self.request.get(f'/dam/assets/{self._quote_path_segment(asset_id)}', params=params)

    def get_template(self, template_id: str, params=None):
        """
        Retrieve a Template

        Contract operation: api2.get-template.
        """
        template_id = require_path_id(template_id, 'template_id')
        return self.request.get(f'/templates/{self._quote_path_segment(template_id)}', params=params)

    def get_template_credentials(self, identifier: str, params=None):
        """
        Retrieve a Template Credential

        Contract operation: api2.get-template-credential.
        """
        identifier = require_path_id(identifier, 'identifier')
        return self.request.get(f'/template_credentials/{self._quote_path_segment(identifier)}', params=params)

    def issue_bearer_token(self, data=None):
        """
        Create a bearer token

        Contract operation: api2.issue-bearer-token.
        """
        return self.request.issue_bearer_token(data)

    def list_assemblies(self, params=None):
        """
        Retrieve list of Assemblies

        Contract operation: api2.list-assemblies.
        """
        return self.request.get('/assemblies', params=params)

    def list_assembly_notifications(self, assembly_id: str, params=None):
        """
        Retrieve Assembly Notifications

        Contract operation: api2.list-assembly-notifications.
        """
        assembly_id = require_path_id(assembly_id, 'assembly_id')
        return self.request.public('GET', f'/assembly_notifications/{self._quote_path_segment(assembly_id)}', params=params)

    def list_auth_key_scopes(self, params=None):
        """
        Retrieve Auth Key scopes

        Contract operation: api2.list-auth-key-scopes.
        """
        return self.request.get('/auth_keys/scopes', params=params)

    def list_auth_keys(self, params=None):
        """
        Retrieve list of Auth Keys

        Contract operation: api2.list-auth-keys.
        """
        return self.request.get('/auth_keys', params=params)

    def list_dam_assets(self, params=None):
        """
        List Storage assets

        Contract operation: api2.list-dam-assets.
        """
        return self.request.get('/dam/assets', params=params)

    def list_priority_job_slots(self, params=None):
        """
        Retrieve currently used priority job slots

        Contract operation: api2.list-priority-job-slots.
        """
        return self.request.get('/queues/job_slots', params=params)

    def list_template_credential_types(self, params=None):
        """
        Retrieve Template Credential types

        Contract operation: api2.list-template-credential-types.
        """
        return self.request.get('/template_credentials/types', params=params)

    def list_template_credentials(self, params=None):
        """
        Retrieve list of Template Credentials

        Contract operation: api2.list-template-credentials.
        """
        return self.request.get('/template_credentials', params=params)

    def list_templates(self, params=None):
        """
        Retrieve list of Templates

        Contract operation: api2.list-templates.
        """
        return self.request.get('/templates', params=params)

    def move_dam_asset(self, asset_id: str, data=None):
        """
        Move or rename a DAM asset

        Contract operation: api2.move-dam-asset.
        Stage: alpha; this API may change.
        """
        asset_id = require_path_id(asset_id, 'asset_id')
        return self.request.patch(f'/dam/assets/{self._quote_path_segment(asset_id)}', data=data)

    def move_dam_entry(self, data=None):
        """
        Move a Storage file or folder

        Contract operation: api2.move-dam-entry.
        Stage: alpha; this API may change.
        """
        return self.request.post('/dam/entries/move', data=data)

    def priority_job_slot_stats(self, params=None):
        """
        Retrieve priority job slot statistics

        Contract operation: api2.priority-job-slot-stats.
        """
        return self.request.get('/priority_job_slot_stats', params=params)

    def replace_assembly(self, assembly_id: str, data=None, extra_data=None, files=None):
        """
        Create an Assembly with a supplied ID

        Contract operation: api2.replace-assembly.
        """
        assembly_id = require_path_id(assembly_id, 'assembly_id')
        return self.request.put(f'/assemblies/{self._quote_path_segment(assembly_id)}', data=data, extra_data=extra_data, files=files)

    def replay_assembly(self, assembly_id: str, data=None):
        """
        Replay an Assembly

        Contract operation: api2.replay-assembly.
        """
        assembly_id = require_path_id(assembly_id, 'assembly_id')
        return self.request.post(f'/assemblies/{self._quote_path_segment(assembly_id)}/replay', data=data)

    def replay_assembly_notification(self, assembly_id: str, data=None):
        """
        Replay Assembly Notification

        Contract operation: api2.replay-assembly-notification.
        """
        assembly_id = require_path_id(assembly_id, 'assembly_id')
        return self.request.post(f'/assembly_notifications/{self._quote_path_segment(assembly_id)}/replay', data=data)

    def show_auth_key_secret(self, auth_key_id: str, data=None):
        """
        Retrieve an Auth Key secret

        Contract operation: api2.show-auth-key-secret.
        """
        auth_key_id = require_path_id(auth_key_id, 'auth_key_id')
        return self.request.post(f'/auth_keys/show_secret/{self._quote_path_segment(auth_key_id)}', data=data)

    def stream_assembly_status(self, stream_url, *, read_timeout=120, max_event_size=1048576):
        """
        Stream Assembly changes live

        Contract operation: api2.stream-assembly-status.
        Use with a context manager. Terminal events do not imply Assembly success.
        """
        return self.request.stream_status(stream_url, read_timeout=read_timeout, max_event_size=max_event_size)

    def update_auth_key(self, auth_key_id: str, data=None):
        """
        Edit an Auth Key

        Contract operation: api2.update-auth-key.
        """
        auth_key_id = require_path_id(auth_key_id, 'auth_key_id')
        return self.request.put(f'/auth_keys/{self._quote_path_segment(auth_key_id)}', data=data)

    def update_template(self, template_id: str, data=None):
        """
        Edit a Template

        Contract operation: api2.update-template.
        """
        template_id = require_path_id(template_id, 'template_id')
        return self.request.put(f'/templates/{self._quote_path_segment(template_id)}', data=data)

    def update_template_credentials(self, identifier: str, data=None):
        """
        Edit a Template Credential

        Contract operation: api2.update-template-credential.
        """
        identifier = require_path_id(identifier, 'identifier')
        return self.request.put(f'/template_credentials/{self._quote_path_segment(identifier)}', data=data)

    def create_upload(self, assembly, headers=None, body=None):
        """
        Create a tus upload

        Contract operation: tusd.create-upload.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.create-upload', assembly, headers=headers, body=body)

    def delete_upload(self, upload_url, headers=None):
        """
        Terminate a tus upload

        Contract operation: tusd.delete-upload.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.delete-upload', upload_url, headers=headers, body=None)

    def download_upload(self, upload_url, headers=None):
        """
        Download a tus upload

        Contract operation: tusd.download-upload.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.download-upload', upload_url, headers=headers, body=None)

    def get_upload_offset(self, upload_url, headers=None):
        """
        Retrieve a tus upload offset

        Contract operation: tusd.get-upload-offset.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.get-upload-offset', upload_url, headers=headers, body=None)

    def tus_options(self, assembly, headers=None):
        """
        Discover tus capabilities

        Contract operation: tusd.options.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.options', assembly, headers=headers, body=None)

    def patch_upload(self, upload_url, headers=None, body=None):
        """
        Upload tus file bytes

        Contract operation: tusd.patch-upload.
        Pass protocol headers using headers; binary downloads return bytes.
        """
        return self.request.tus('tusd.patch-upload', upload_url, headers=headers, body=body)
    # </api2-generated-endpoints>

    # High-level upload/resume workflows are maintained by hand.

    def create_tus_assembly(self, file_count: int):
        """
        Creates a TUS-ready Assembly that waits for the requested number of resumable uploads before execution continues.
        """
        assembly = self.create_assembly(
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

    def resume_tus_upload(self, upload_url: str, content: bytes, assembly_ssl_url: str):
        """Resume from the reported offset, then poll the Assembly to completion."""
        offset_response = self.get_upload_offset(upload_url)
        if offset_response.status_code != 200:
            raise RuntimeError(f"TUS offset returned HTTP {offset_response.status_code}")
        try:
            offset = int(offset_response.headers.get("Upload-Offset", ""))
        except ValueError:
            raise RuntimeError("TUS offset is not an integer.") from None
        if not 0 <= offset <= len(content):
            raise RuntimeError("TUS offset is outside the supplied content.")
        response = self.patch_upload(upload_url, headers={"Upload-Offset": str(offset)}, body=content[offset:])
        if response.status_code != 204 or response.headers.get("Upload-Offset") != str(len(content)):
            raise RuntimeError("TUS resume did not acknowledge the complete content.")
        return self.wait_for_assembly(assembly_ssl_url)

    def upload_tus_assembly(self, content: bytes, fieldname: str, filename: str, user_meta: Optional[dict] = None):
        """Create an Assembly, upload one file using TUS, and wait for completion."""
        assembly = self.create_tus_assembly(1)
        metadata = {str(key): str(value) for key, value in (user_meta or {}).items()}
        metadata.update({"fieldname": fieldname, "filename": filename})
        encoded = ",".join(key + " " + base64.b64encode(str(value).encode()).decode("ascii")
                           for key, value in metadata.items())
        created = self.create_upload(assembly, headers={"Upload-Length": str(len(content)), "Upload-Metadata": encoded})
        if created.status_code != 201:
            raise RuntimeError(f"TUS creation returned HTTP {created.status_code}")
        response = self.patch_upload(created.upload_url, headers={"Upload-Offset": "0"}, body=content)
        if response.status_code != 204 or response.headers.get("Upload-Offset") != str(len(content)):
            raise RuntimeError("TUS upload did not acknowledge the complete content.")
        completed = self.wait_for_assembly(assembly.data["assembly_ssl_url"])
        return completed, created.upload_url

    def wait_for_assembly(self, assembly_url: str):
        """
        Waits for an Assembly to finish uploading and executing.
        Use the returned assembly_ssl_url as the assembly URL.
        """
        while True:
            response = self.get_assembly(assembly_url=assembly_url)
            data = response.data

            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected non-JSON response ({response.status_code}).")

            # Abort polling if the assembly has entered an error state
            if data.get("error"):
                return response

            # The polling is done if the assembly is not uploading or executing anymore.
            if data.get("ok") not in ("ASSEMBLY_UPLOADING", "ASSEMBLY_EXECUTING"):
                return response

            sleep(1)


    def new_template(self, name: str, params: Optional[dict] = None) -> template.Template:
        """
        Return an instance of <transloadit.template.Template> which would be used to create
        a new template.

        :Args:
            - name (str): Name of the template.
        """
        return template.Template(self, name, options=params)

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
        See https://transloadit.com/docs/topics/signature-authentication/#smart-cdn

        :Args:
            - workspace (str): Workspace slug
            - template (str): Template slug or template ID
            - input (str): Input value that is provided as ${fields.input} in the template
            - url_params (Optional[dict]): Additional parameters for the URL query string. Values can be strings, numbers, booleans, arrays thereof, or None.
            - expires_at_ms (Optional[int]): Timestamp in milliseconds since UNIX epoch when the signature is no longer valid. Defaults to 1 hour from now.

        :Returns:
            str: The signed Smart CDN URL

        :Raises:
            ValueError: If url_params contains values that are not strings, numbers, booleans, arrays, or None
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
