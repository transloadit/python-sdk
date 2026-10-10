"""Shared wire preparation for OAuth, SSE and raw TUS endpoints."""
import base64
import copy
import os
from ipaddress import ip_address
import re
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from requests.structures import CaseInsensitiveDict
from requests.utils import get_environ_proxies

from ._contract import CONTRACT
from .response import Response


def sync_network_options(url):
    """Honor transport configuration without enabling ambient netrc auth."""
    return {"proxies": get_environ_proxies(url),
            "verify": os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE") or True}


def async_network_options(url):
    proxies = get_environ_proxies(url)
    return {"proxy": proxies.get(urlsplit(url).scheme) or proxies.get("all")}


def token_request(client, data):
    data = copy.deepcopy(data or {})
    if not isinstance(data, dict):
        raise ValueError("Token data must be a dictionary.")
    selector = CONTRACT["token_auth"]
    # Preserve the pre-2.0 draft's omitted-grant default.
    grant = data.setdefault(selector["field"], "client_credentials")
    try:
        authentication = selector["values"][grant]
    except (KeyError, TypeError):
        raise ValueError("Unsupported token grant_type.") from None
    url = client.service.rstrip("/") + "/token"
    parsed = urlsplit(url)
    try:
        loopback = parsed.hostname == "localhost" or ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if parsed.username is not None or parsed.password is not None or not (
        parsed.scheme == "https" or (parsed.scheme == "http" and loopback)
    ):
        raise ValueError("Refusing to send credentials to an insecure bearer token endpoint.")
    headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    if authentication == "basic":
        if not client.auth_secret:
            raise ValueError("Bearer token issuance requires an auth secret for this grant.")
        credentials = base64.b64encode(f"{client.auth_key}:{client.auth_secret}".encode()).decode("ascii")
        headers["Authorization"] = "Basic " + credentials
    elif authentication != "none":
        raise ValueError("Unsupported contract token authentication.")
    return url, data, headers


def capability_url(client, url, kind):
    """Validate a returned capability URL without signing or following redirects.

    Custom services are explicitly trusted only at their configured origin.
    Production capabilities may additionally use the producer's regional hosts.
    Persisted upload URLs are accepted so a later process can resume an upload.
    """
    validate_raw_url(url)
    try:
        target, service = urlsplit(url), urlsplit(client.service)
        target_port = target.port or (443 if target.scheme == "https" else 80)
        service_port = service.port or (443 if service.scheme == "https" else 80)
    except ValueError:
        raise ValueError("Invalid capability URL.") from None
    if target.username is not None or target.password is not None or "#" in url:
        raise ValueError("Invalid capability URL.")
    same_origin = (target.scheme, target.hostname, target_port) == (service.scheme, service.hostname, service_port)
    host_pattern = CONTRACT["capability"]["publicHostPattern"]
    production = service.hostname == "api2.transloadit.com" or re.fullmatch(host_pattern, service.hostname or "")
    regional = production and target.scheme == "https" and target_port == 443 and re.fullmatch(host_pattern, target.hostname or "")
    if target.scheme not in {"http", "https"} or not (same_origin or regional):
        raise ValueError("Refusing an untrusted capability destination.")
    path = target.path[:-1] if kind == "tus-collection" and target.path.endswith("/") else target.path
    valid = matches_capability_path(path, kind)
    if kind == "status-stream":
        query = parse_qs(target.query, keep_blank_values=True)
        ids = query.get(CONTRACT["capability"]["streamQuery"], [])
        assembly_route = next(route for route in CONTRACT["capability"]["routes"] if route["kind"] == "assembly")
        identity_pattern = assembly_route["parameters"][0]["pattern"]
        valid = valid and set(query) == {CONTRACT["capability"]["streamQuery"]} and len(ids) == 1 and bool(re.fullmatch(identity_pattern, ids[0]))
    else:
        valid = valid and "?" not in url
    if not valid:
        raise ValueError("Capability URL does not match the requested operation.")
    return url


def matches_capability_path(path, kind):
    for route in CONTRACT["capability"]["routes"]:
        if route["kind"] != kind:
            continue
        parts, template = path.split("/"), route["path"].split("/")
        if len(parts) != len(template):
            continue
        valid = True
        for part, expected in zip(parts, template):
            if not expected.startswith("{"):
                valid = valid and part == expected
                continue
            field = next(parameter for parameter in route["parameters"] if parameter["name"] == expected[1:-1])
            value = unquote(part) if field["percentDecode"] else part
            valid = valid and len(value) >= field.get("minLength", 0) and len(value) <= field.get("maxLength", float("inf"))
            if "pattern" in field:
                valid = valid and re.fullmatch(field["pattern"], value) is not None
        if valid:
            return True
    return False


def validate_raw_url(url):
    # Validate before urljoin/urlsplit can erase dot segments or control bytes.
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url) or "\\" in url or re.search(r"%(?![0-9a-fA-F]{2})", url):
        raise ValueError("Invalid capability URL.")
    path = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^/?#]*", "", url).split("?", 1)[0].split("#", 1)[0]
    for part in path.split("/"):
        try:
            decoded = unquote(part, errors="strict")
        except UnicodeError:
            raise ValueError("Invalid capability path encoding.") from None
        if decoded in {".", ".."} or any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in "/\\?#" for c in decoded) or re.search(r"%[0-9a-fA-F]{2}", decoded):
            raise ValueError("Invalid capability path segment.")


def tus_request(client, operation_id, location, headers, body):
    spec = CONTRACT["protocols"][operation_id]
    supplied = CaseInsensitiveDict(headers or {})
    if any(name.lower() in {"authorization", "proxy-authorization", "cookie", "host"} for name in supplied):
        raise ValueError("Account credentials and Host overrides are not TUS headers.")
    if any(name.lower() in CONTRACT["capability"]["unsupportedHeaders"] for name in supplied):
        raise ValueError("Unsupported TUS header in the API2 contract.")
    outgoing = CaseInsensitiveDict(spec["defaults"])
    outgoing.update(supplied)
    if spec["destination"] == "tus-collection":
        assembly = location.data if isinstance(location, Response) else location
        if not isinstance(assembly, dict):
            raise ValueError("Pass the Assembly response to a TUS collection operation.")
        policy = CONTRACT["capability"]
        url = capability_url(client, assembly.get(policy["collectionField"]), "tus-collection")
        assembly_url = capability_url(client, assembly.get(policy["assemblyField"]), "assembly")
        # A collection and its Assembly can live on different trusted uploaders.
        b = urlsplit(assembly_url)
        if assembly.get(policy["identityField"]) != b.path.rsplit("/", 1)[1]:
            raise ValueError("Assembly URL does not match the Assembly identity.")
        if spec["method"] == "POST":
            encoded = base64.b64encode(assembly_url.encode()).decode("ascii")
            name = policy["metadataName"]
            metadata = outgoing.get(policy["metadataHeader"], "")
            parts = [part.strip() for part in metadata.split(",") if part.strip()]
            # The Assembly capability must come from this validated response.
            for part in parts:
                if part.split(" ", 1)[0] == name and part != f"{name} {encoded}":
                    raise ValueError("Upload-Metadata cannot override the Assembly URL.")
            parts = [part for part in parts if part.split(" ", 1)[0] != name]
            parts.append(f"{name} {encoded}")
            outgoing[policy["metadataHeader"]] = ",".join(parts)
            if body is not None:
                outgoing.setdefault("Content-Type", "application/offset+octet-stream")
    else:
        url = capability_url(client, location, "tus-upload-resource")
    return spec, url, dict(outgoing), body


def validate_upload_location(client, url, response):
    """Resolve a successful creation's Location and reject foreign destinations."""
    if response.status_code != CONTRACT["capability"]["creationStatus"]:
        return response
    location = response.headers.get("Location")
    if not location:
        raise ValueError("TUS creation did not return a Location header.")
    validate_raw_url(location)
    absolute = capability_url(client, urljoin(url, location), "tus-upload-resource")
    # HAProxy can forward creation to a different trusted uploader; its host is
    # then returned in Location. Trust policy still rejects arbitrary origins.
    # Leave wire headers intact. This convenience value is safe to persist/resume.
    response.upload_url = absolute
    return response
