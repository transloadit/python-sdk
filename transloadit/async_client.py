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

    # <api2-generated-endpoints>
    async def create_assembly(self, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create a new Assembly.
        """
        return await self.request.post("/assemblies", data=data, extra_data=extra_data, files=files)

    async def create_assembly_with_id(self, assembly_id: str, data: Optional[dict] = None, extra_data: Optional[dict] = None, files: Optional[dict] = None):
        """
        Create Assembly With Id.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assemblies/{_quote_path_segment(assembly_id)}", data=data, extra_data=extra_data, files=files)

    async def get_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Retrieve an Assembly Status.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
        return await self.request.get(url)

    async def list_assemblies(self, params: dict = None):
        """
        Retrieve list of Assemblies.
        """
        return await self.request.get("/assemblies", params=params)

    async def cancel_assembly(self, assembly_id: str = None, assembly_url: str = None):
        """
        Cancel a running Assembly.
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else f"/assemblies/{_quote_path_segment(assembly_id)}"
        return await self.request.delete(url)

    async def replay_assembly(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay an Assembly.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assemblies/{_quote_path_segment(assembly_id)}/replay", data=data)

    async def replay_assembly_notification(self, assembly_id: str, data: Optional[dict] = None):
        """
        Replay Assembly Notification.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.post(f"/assembly_notifications/{_quote_path_segment(assembly_id)}/replay", data=data)

    async def list_assembly_notifications(self, assembly_id: str):
        """
        List Assembly Notifications.
        """
        assembly_id = require_path_id(assembly_id, "assembly_id")

        return await self.request.get(f"/assembly_notifications/{_quote_path_segment(assembly_id)}")

    async def get_template(self, template_id: str):
        """
        Retrieve a Template.
        """
        template_id = require_path_id(template_id, "template_id")
        return await self.request.get(f"/templates/{_quote_path_segment(template_id)}")

    async def get_builtin_template(self, builtin_template_slug: str):
        """
        Get Builtin Template.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return await self.request.get(f"/templates/builtin/{_quote_path_segment(builtin_template_slug)}")

    async def get_template_full(self, template_id_or_name: str):
        """
        Get Template Full.
        """
        template_id_or_name = require_path_id(template_id_or_name, "template_id_or_name")

        return await self.request.get(f"/templates/{_quote_path_segment(template_id_or_name)}/full")

    async def get_builtin_template_full(self, builtin_template_slug: str):
        """
        Get Builtin Template Full.
        """
        builtin_template_slug = require_path_id(builtin_template_slug, "builtin_template_slug")

        return await self.request.get(f"/templates/builtin/{_quote_path_segment(builtin_template_slug)}/full")

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

    async def update_template(self, template_id: str, data: dict):
        """
        Edit a Template.
        """
        template_id = require_path_id(template_id, "template_id")
        return await self.request.put(f"/templates/{_quote_path_segment(template_id)}", data=data)

    async def delete_template(self, template_id: str):
        """
        Delete a Template.
        """
        template_id = require_path_id(template_id, "template_id")
        return await self.request.delete(f"/templates/{_quote_path_segment(template_id)}")

    async def list_priority_job_slots(self):
        """
        Retrieve currently used priority job slots.
        """
        return await self.request.get("/queues/job_slots")

    async def list_template_credentials(self):
        """
        Retrieve list of Template Credentials.
        """
        return await self.request.get("/template_credentials")

    async def list_template_credential_types(self):
        """
        List Template Credential Types.
        """
        return await self.request.get("/template_credentials/types")

    async def validate_template_credential_oauth_on_create(self, data: Optional[dict] = None):
        """
        Validate Template Credential OAuth On Create.
        """
        return await self.request.post("/template_credentials/validateOauthOnCreate", data=data)

    async def create_template_credentials(self, data: Optional[dict] = None):
        """
        Create a new Template Credential.
        """
        return await self.request.post("/template_credentials", data=data)

    async def get_template_credentials(self, identifier: str):
        """
        Retrieve a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.get(f"/template_credentials/{_quote_path_segment(identifier)}")

    async def delete_template_credentials(self, identifier: str):
        """
        Delete a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.delete(f"/template_credentials/{_quote_path_segment(identifier)}")

    async def update_template_credentials(self, identifier: str, data: Optional[dict] = None):
        """
        Edit a Template Credential.
        """
        identifier = require_path_id(identifier, "identifier")

        return await self.request.put(f"/template_credentials/{_quote_path_segment(identifier)}", data=data)

    async def get_bill(self, month: int, year: int):
        """
        Retrieve a month’s bill.
        """
        return await self.request.get(f"/bill/{year}-{month:02d}")

    # </api2-generated-endpoints>

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
