import hashlib
import hmac
import time
from typing import List, Optional, Union
from urllib.parse import quote_plus, urlencode

from . import async_assembly, async_request, async_template


def _stringify_url_param(value: Union[str, int, float, bool]) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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
        if not service.startswith(("http://", "https://")):
            service = "https://" + service

        self.service = service
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

    async def get_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Get the assembly specified by the 'assembly_id' or the 'assembly_url'.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{assembly_id}"
        return await self.request.get(url)

    async def list_assemblies(self, params: dict = None):
        """
        Get the list of assemblies.
        """
        return await self.request.get("/assemblies", params=params)

    async def cancel_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Cancel the assembly specified by the 'assembly_id' or the 'assembly_url'.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{assembly_id}"
        return await self.request.delete(url)

    async def get_template(self, template_id: str):
        """
        Get the template specified by the 'template_id'.
        """
        return await self.request.get(f"/templates/{template_id}")

    async def list_templates(self, params: Optional[dict] = None):
        """
        Get the list of templates.
        """
        return await self.request.get("/templates", params=params)

    def new_template(self, name: str, params: Optional[dict] = None) -> async_template.AsyncTemplate:
        """
        Return an instance of <transloadit.async_template.AsyncTemplate>.
        """
        return async_template.AsyncTemplate(self, name, options=params)

    async def update_template(self, template_id: str, data: dict):
        """
        Update the template specified by the 'template_id'.
        """
        return await self.request.put(f"/templates/{template_id}", data=data)

    async def delete_template(self, template_id: str):
        """
        Delete the template specified by the 'template_id'.
        """
        return await self.request.delete(f"/templates/{template_id}")

    async def get_bill(self, month: int, year: int):
        """
        Get the bill for the specified month and year.
        """
        return await self.request.get(f"/bill/{year}-{month:02d}")

    def get_signed_smart_cdn_url(
        self,
        workspace: str,
        template: str,
        input: str,
        url_params: Optional[dict[str, Union[str, int, float, bool, List[Union[str, int, float, bool]], None]]] = None,
        expires_at_ms: Optional[int] = None,
    ) -> str:
        """
        Construct a signed Smart CDN URL.
        """
        workspace_slug = quote_plus(workspace)
        template_slug = quote_plus(template)
        input_field = quote_plus(input)

        expiry = expires_at_ms if expires_at_ms is not None else int(time.time() * 1000) + 60 * 60 * 1000

        params = []
        if url_params:
            for k, v in url_params.items():
                if v is None:
                    continue
                elif isinstance(v, (str, int, float, bool)):
                    params.append((k, _stringify_url_param(v)))
                elif isinstance(v, (list, tuple)):
                    params.append((k, [_stringify_url_param(vv) for vv in v]))
                else:
                    raise ValueError(
                        f"URL parameter values must be strings, numbers, booleans, arrays, or None. Got {type(v)} for {k}"
                    )

        params.append(("auth_key", self.auth_key))
        params.append(("exp", str(expiry)))
        sorted_params = sorted(params, key=lambda x: x[0])
        query_string = urlencode(sorted_params, doseq=True)

        string_to_sign = f"{workspace_slug}/{template_slug}/{input_field}?{query_string}"
        algorithm = "sha256"

        signature = algorithm + ":" + hmac.new(
            self.auth_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"https://{workspace_slug}.tlcdn.com/{template_slug}/{input_field}?{query_string}&sig={quote_plus(signature)}"
