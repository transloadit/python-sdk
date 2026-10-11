import typing
from typing import Optional
from urllib.parse import quote

from . import assembly, request, template
from .api_url import is_transloadit_api_host, normalize_service_url, require_path_id
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
            if (candidate.scheme == "http" and candidate.port in {None, 80}
                    and candidate.username is None and candidate.password is None
                    and is_transloadit_api_host(candidate.hostname)):
                # Preserve the API's legacy assembly_url field without plain HTTP.
                candidate = candidate._replace(scheme="https", netloc=candidate.hostname)
                candidate_url = candidate.geturl()
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
            and is_transloadit_api_host(candidate_hostname)
        )
        # Explicit custom/Gateway services retain their legacy worker origins.
        # These are capability requests: session account credentials stay isolated.
        custom_service = not is_transloadit_api_host(configured_hostname)
        custom_destination = custom_service and not has_url_credentials and bool(candidate_hostname) and candidate.scheme in {"http", "https"}
        if not (configured_origin or configured_https_host or api2_cell or custom_destination):
            raise ValueError("Refusing to request an untrusted Assembly URL.")
        if method not in {"GET", "DELETE"}:
            raise ValueError(f"Unsupported Assembly URL method: {method}")

        return self.request.public(method, candidate_url, params=params)

    def get_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Get the assembly specified by the 'assembly_id' or the 'assembly_url'
        Either the assembly_id or the assembly_url must be specified

        :Args:
            - assembly_id (Optional[str])
            - assembly_url (Optional[str])

        Return an instance of <transloadit.response.Response>
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return self._request_assembly_url(url, "GET")

    def list_assemblies(self, params: dict = None):
        """
        Get the list of assemblies.

        :Args:
            - options (Optional[dict]):
                params to send along with the request. Please see
                https://transloadit.com/docs/api-docs/#25-retrieve-assembly-list for available options.

        Return an instance of <transloadit.response.Response>
        """
        return self.request.get("/assemblies", params=params)

    def cancel_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Cancel the assembly specified by the 'assembly_id' or the 'assembly_url'
        Either the assembly_id or the assembly_url must be specified

        :Args:
            - assembly_id (Optional[str])
            - assembly_url (Optional[str])

        Return an instance of <transloadit.response.Response>
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"
        return self._request_assembly_url(url, "DELETE")

    def get_template(self, template_id: str):
        """
        Get the template specified by the 'template_id'.

        :Args:
            - template_id (str)

        Return an instance of <transloadit.response.Response>
        """
        template_id = require_path_id(template_id, "template_id")
        return self.request.get(f"/templates/{self._quote_path_segment(template_id)}")

    def list_templates(self, params: Optional[dict] = None):
        """
        Get the list of templates.

        :Args:
            - options (Optional[dict]):
                params to send along with the request. Please see
                https://transloadit.com/docs/api-docs/#45-retrieve-template-list for available options.

        Return an instance of <transloadit.response.Response>
        """
        return self.request.get("/templates", params=params)

    def update_template(self, template_id: str, data: dict):
        """
        Update the template specified by the 'template_id'.

        :Args:
            - template_id (str)
            - data (dict): key, value pair of fields and their new values.

        Return an instance of <transloadit.response.Response>
        """
        template_id = require_path_id(template_id, "template_id")
        return self.request.put(f"/templates/{self._quote_path_segment(template_id)}", data=data)

    def delete_template(self, template_id: str):
        """
        Delete the template specified by the 'template_id'.

        :Args:
            - template_id (str)

        Return an instance of <transloadit.response.Response>
        """
        template_id = require_path_id(template_id, "template_id")
        return self.request.delete(f"/templates/{self._quote_path_segment(template_id)}")

    def get_bill(self, month: int, year: int):
        """
        Get the bill for the specified month and year.

        :Args:
            - month (int): e.g 1 for January
            - year (int)

        Return an instance of <transloadit.response.Response>
        """
        return self.request.get(f"/bill/{year}-{month:02d}")

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
