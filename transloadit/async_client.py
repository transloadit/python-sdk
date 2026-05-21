from typing import Optional
from urllib.parse import quote

from . import async_assembly, async_request, async_template
from .api_url import normalize_service_url, require_path_id
from .smart_cdn import URL_PARAM_VALUES, build_signed_smart_cdn_url


def _quote_path_segment(value: str) -> str:
    return quote(str(value), safe="")


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

    async def get_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Get the assembly specified by the 'assembly_id' or the 'assembly_url'.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
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

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
        return await self.request.delete(url)

    async def get_template(self, template_id: str):
        """
        Get the template specified by the 'template_id'.
        """
        template_id = require_path_id(template_id, "template_id")
        return await self.request.get(f"/templates/{_quote_path_segment(template_id)}")

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
        template_id = require_path_id(template_id, "template_id")
        return await self.request.put(f"/templates/{_quote_path_segment(template_id)}", data=data)

    async def delete_template(self, template_id: str):
        """
        Delete the template specified by the 'template_id'.
        """
        template_id = require_path_id(template_id, "template_id")
        return await self.request.delete(f"/templates/{_quote_path_segment(template_id)}")

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
