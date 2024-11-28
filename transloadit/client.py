import typing
import hmac
import hashlib
import time
from urllib.parse import urlencode, quote_plus

from typing import Optional, Union, List

from . import assembly, request, template

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
        if not service.startswith(("http://", "https://")):
            service = "https://" + service

        self.service = service
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

        url = assembly_url if assembly_url else f"/assemblies/{assembly_id}"
        return self.request.get(url)

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

        url = assembly_url if assembly_url else f"/assemblies/{assembly_id}"
        return self.request.delete(url)

    def get_template(self, template_id: str):
        """
        Get the template specified by the 'template_id'.

        :Args:
            - template_id (str)

        Return an instance of <transloadit.response.Response>
        """
        return self.request.get(f"/templates/{template_id}")

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

    def new_template(self, name: str, params: Optional[dict] = None) -> template.Template:
        """
        Return an instance of <transloadit.template.Template> which would be used to create
        a new template.

        :Args:
            - name (str): Name of the template.
        """
        return template.Template(self, name, options=params)

    def update_template(self, template_id: str, data: dict):
        """
        Update the template specified by the 'template_id'.

        :Args:
            - template_id (str)
            - data (dict): key, value pair of fields and their new values.

        Return an instance of <transloadit.response.Response>
        """
        return self.request.put(f"/templates/{template_id}", data=data)

    def delete_template(self, template_id: str):
        """
        Delete the template specified by the 'template_id'.

        :Args:
            - template_id (str)

        Return an instance of <transloadit.response.Response>
        """
        return self.request.delete(f"/templates/{template_id}")

    def get_bill(self, month: int, year: int):
        """
        Get the bill for the specified month and year.

        :Args:
            - month (int): e.g 1 for January
            - year (int)

        Return an instance of <transloadit.response.Response>
        """
        return self.request.get(f"/bill/{year}-{month:02d}")

    def get_signed_smart_cdn_url(
        self,
        workspace: str,
        template: str,
        input: str,
        url_params: Optional[dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]] = None,
        expires_at_ms: Optional[int] = None
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
        workspace_slug = quote_plus(workspace)
        template_slug = quote_plus(template)
        input_field = quote_plus(input)

        expiry = expires_at_ms if expires_at_ms is not None else int(time.time() * 1000) + 60 * 60 * 1000  # 1 hour default

        params = []
        if url_params:
            for k, v in url_params.items():
                if v is None:
                    continue  # Skip None values
                elif isinstance(v, (str, int, float, bool)):
                    params.append((k, str(v)))
                elif isinstance(v, (list, tuple)):
                    params.append((k, [str(vv) for vv in v]))
                else:
                    raise ValueError(f"URL parameter values must be strings, numbers, booleans, arrays, or None. Got {type(v)} for {k}")

        params.append(("auth_key", self.auth_key))
        params.append(("exp", str(expiry)))

        # Sort params alphabetically by key
        sorted_params = sorted(params, key=lambda x: x[0])
        query_string = urlencode(sorted_params, doseq=True)

        string_to_sign = f"{workspace_slug}/{template_slug}/{input_field}?{query_string}"
        algorithm = "sha256"

        signature = algorithm + ":" + hmac.new(
            self.auth_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return f"https://{workspace_slug}.tlcdn.com/{template_slug}/{input_field}?{query_string}&sig={quote_plus(signature)}"
