import base64
import typing
from time import sleep
from typing import Optional
from urllib.parse import quote, urljoin

import requests

from . import assembly, request, template
from .api_url import normalize_service_url, require_path_id
from .smart_cdn import URL_PARAM_VALUES, build_signed_smart_cdn_url

if typing.TYPE_CHECKING:
    from requests import Response


def _quote_path_segment(value: str) -> str:
    return quote(str(value), safe="")


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
    ):
        self.service = normalize_service_url(service)
        self.auth_key = auth_key
        self.auth_secret = auth_secret
        self.duration = duration
        self.request = request.Request(self)

    def new_assembly(self, params: dict = None) -> assembly.Assembly:
        """
        Return an instance of <transloadit.assembly.Assembly> which would be used to create
        a new assembly.
        """
        return assembly.Assembly(self, options=params)

    # <api2-generated-endpoints>
    # This block is generated from Transloadit API2 contracts. If it looks wrong,
    # please report the issue instead of editing this block by hand; the source fix
    # belongs in the contract generator so all SDKs stay in sync.

    def create_assembly(self, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create a new Assembly.
        """
        return self.request.post("/assemblies", data=data, extra_data=extra_data, files=files)

    def create_assembly_with_id(self, assembly_id: str, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create Assembly With Id.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return self.request.post(f"/assemblies/{_quote_path_segment(assembly_id)}", data=data, extra_data=extra_data, files=files)

    def list_assemblies(self, params: Optional[dict] = None):
        """
        Retrieve list of Assemblies.
        """
        return self.request.get("/assemblies", params=params)

    def get_assembly(self, assembly_id: str = None, assembly_url: str = None, params: Optional[dict] = None):
        """
        Retrieve an Assembly Status.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
        return self.request.get(url, params=params)

    def cancel_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Cancel a running Assembly.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
        return self.request.delete(url)

    def replay_assembly(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay an Assembly.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return self.request.post(f"/assemblies/{_quote_path_segment(assembly_id)}/replay", data=data)

    def replay_assembly_notification(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay Assembly Notification.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return self.request.post(f"/assembly_notifications/{_quote_path_segment(assembly_id)}/replay", data=data)

    def list_assembly_notifications(self, assembly_id: str):
        """
        List Assembly Notifications.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return self.request.get(f"/assembly_notifications/{_quote_path_segment(assembly_id)}")

    def get_bill(self, month: int, year: int, params: Optional[dict] = None):
        """
        Retrieve a month’s bill.
        """
        return self.request.get(f"/bill/{year}-{month:02d}", params=params)

    def list_templates(self, params: Optional[dict] = None):
        """
        Retrieve list of Templates.
        """
        return self.request.get("/templates", params=params)

    def create_template(self, data: Optional[dict] = None):
        """
        Create a new Template.
        """
        return self.request.post("/templates", data=data)

    def get_template(self, template_id: str, params: Optional[dict] = None):
        """
        Retrieve a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return self.request.get(f"/templates/{_quote_path_segment(template_id)}", params=params)

    def get_builtin_template(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Get Builtin Template.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return self.request.get(f"/templates/builtin/{_quote_path_segment(builtin_template_slug)}", params=params)

    def get_template_full(self, template_id_or_name: str, params: Optional[dict] = None):
        """
        Get Template Full.
        """
        template_id_or_name = require_path_id(template_id_or_name, "template_id_or_name")

        return self.request.get(f"/templates/{_quote_path_segment(template_id_or_name)}/full", params=params)

    def get_builtin_template_full(self, builtin_template_slug: str, params: Optional[dict] = None):
        """
        Get Builtin Template Full.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return self.request.get(f"/templates/builtin/{_quote_path_segment(builtin_template_slug)}/full", params=params)

    def update_template(self, template_id: str, data: Optional[dict] = None):
        """
        Edit a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return self.request.put(f"/templates/{_quote_path_segment(template_id)}", data=data)

    def delete_template(self, template_id: str, data: Optional[dict] = None):
        """
        Delete a Template.
        """
        template_id = require_path_id(template_id, "template_id")

        return self.request.delete(f"/templates/{_quote_path_segment(template_id)}", data=data)

    def list_priority_job_slots(self, params: Optional[dict] = None):
        """
        Retrieve currently used priority job slots.
        """
        return self.request.get("/queues/job_slots", params=params)

    def list_template_credentials(self, params: Optional[dict] = None):
        """
        Retrieve list of Template Credentials.
        """
        return self.request.get("/template_credentials", params=params)

    def list_template_credential_types(self, params: Optional[dict] = None):
        """
        List Template Credential Types.
        """
        return self.request.get("/template_credentials/types", params=params)

    def validate_template_credential_oauth_on_create(self, data: Optional[dict] = None):
        """
        Validate Template Credential OAuth On Create.
        """
        return self.request.post("/template_credentials/validateOauthOnCreate", data=data)

    def create_template_credentials(self, data: Optional[dict] = None):
        """
        Create a new Template Credential.
        """
        return self.request.post("/template_credentials", data=data)

    def get_template_credentials(self, identifier: str, params: Optional[dict] = None):
        """
        Retrieve a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return self.request.get(f"/template_credentials/{_quote_path_segment(identifier)}", params=params)

    def delete_template_credentials(self, identifier: str, data: Optional[dict] = None):
        """
        Delete a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return self.request.delete(f"/template_credentials/{_quote_path_segment(identifier)}", data=data)

    def update_template_credentials(self, identifier: str, data: Optional[dict] = None):
        """
        Edit a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return self.request.put(f"/template_credentials/{_quote_path_segment(identifier)}", data=data)

    # </api2-generated-endpoints>

    # <api2-generated-features>
    # This block is generated from Transloadit API2 contracts. If it looks wrong,
    # please report the issue instead of editing this block by hand; the source fix
    # belongs in the contract generator so all SDKs stay in sync.

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

    def upload_tus_assembly(self, file_count: int, content: bytes, fieldname: str, filename: str, user_meta: Optional[dict] = None):
        """
        Creates a TUS-ready Assembly, uploads one file with the TUS protocol, and waits for the Assembly to finish.
        """
        created_assembly = self.create_tus_assembly(file_count)

        endpoint_url = created_assembly.data.get("tus_url")
        if not endpoint_url:
            raise RuntimeError("TUS singleUploadLifecycle needs input.endpointUrl")

        metadata_map = {}
        if user_meta:
            metadata_map.update({str(key): str(value) for key, value in user_meta.items()})
        metadata_map["assembly_url"] = str(created_assembly.data.get("assembly_ssl_url"))
        metadata_map["fieldname"] = str(fieldname)
        metadata_map["filename"] = str(filename)

        create_headers = {}
        create_headers["Tus-Resumable"] = "1.0.0"
        create_headers["Upload-Length"] = str(len(content))
        create_metadata_parts = []
        for key, value in metadata_map.items():
            encoded_value = base64.b64encode(str(value).encode("utf-8")).decode("ascii")
            create_metadata_parts.append(f"{key} {encoded_value}")
        create_headers["Upload-Metadata"] = ",".join(create_metadata_parts)
        create_response = requests.request(
            "POST",
            endpoint_url,
            data=b"",
            headers=create_headers,
            timeout=request.TIMEOUT,
        )
        if create_response.status_code != 201:
            raise RuntimeError(f"TUS create returned HTTP {create_response.status_code}, expected 201")
        upload_url_location = create_response.headers.get("Location")
        if not upload_url_location:
            raise RuntimeError("TUS create did not return a Location header")
        upload_url_text = urljoin(endpoint_url, upload_url_location)

        upload_headers = {}
        upload_headers["Tus-Resumable"] = "1.0.0"
        upload_headers["Upload-Offset"] = "0"
        upload_headers["Content-Type"] = "application/offset+octet-stream"
        upload_response = requests.request(
            "PATCH",
            upload_url_text,
            data=content,
            headers=upload_headers,
            timeout=request.TIMEOUT,
        )
        if upload_response.status_code != 204:
            raise RuntimeError(f"TUS upload returned HTTP {upload_response.status_code}, expected 204")
        try:
            upload_offset = int(upload_response.headers.get("Upload-Offset", ""))
        except ValueError as error:
            raise RuntimeError("TUS upload returned an invalid Upload-Offset header") from error
        if upload_offset != len(content):
            raise RuntimeError(f"TUS upload offset {upload_offset}, expected {len(content)}")

        created_assembly_assembly_ssl_url = created_assembly.data.get("assembly_ssl_url")
        if not created_assembly_assembly_ssl_url:
            raise RuntimeError("uploadTusAssembly needs createdAssembly.assembly_ssl_url")
        completed_assembly = self.wait_for_assembly(created_assembly_assembly_ssl_url)

        return completed_assembly, upload_url_text

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

    # </api2-generated-features>

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
