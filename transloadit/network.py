"""Proxy and TLS options for credential-free Assembly status requests."""
import asyncio
import os

from aiohttp.helpers import get_env_proxy_for_url
from requests.utils import get_environ_proxies
from yarl import URL


def sync_network_options(url):
    """Honor transport configuration without enabling ambient netrc auth."""
    return {"proxies": get_environ_proxies(url),
            "verify": os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE") or True}

async def async_network_options(url, session=None):
    # aiohttp exposes the connector publicly, but its session-level proxy defaults
    # only through these attributes. Keep explicit proxy/auth ahead of environment.
    proxy = getattr(session, "_default_proxy", None)
    if proxy is not None:
        return {"proxy": proxy, "proxy_auth": getattr(session, "_default_proxy_auth", None)}
    if session is not None and not getattr(session, "trust_env", True):
        return {"proxy": None}
    try:
        # Use aiohttp's exact policy (including proxy-only netrc credentials),
        # and keep netrc file reads off the event loop like ClientSession does.
        proxy, proxy_auth = await asyncio.to_thread(get_env_proxy_for_url, URL(url))
    except LookupError:
        return {"proxy": None}
    return {"proxy": proxy, "proxy_auth": proxy_auth}
