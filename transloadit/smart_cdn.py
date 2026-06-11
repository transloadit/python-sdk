import hashlib
import hmac
import re
import time
from typing import List, Optional, Tuple, Union
from urllib.parse import quote_plus, urlencode

URL_PARAM_VALUE = Union[str, int, float, bool]
URL_PARAM_VALUES = Union[
    URL_PARAM_VALUE,
    List[URL_PARAM_VALUE],
    Tuple[URL_PARAM_VALUE, ...],
    None,
]
RESERVED_URL_PARAMS = {"auth_key", "exp", "sig"}
WORKSPACE_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _stringify_url_param(value: URL_PARAM_VALUE) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _validate_workspace_slug(workspace: str) -> str:
    if not WORKSPACE_SLUG_PATTERN.fullmatch(workspace):
        raise ValueError(
            "workspace must be a DNS-safe Smart CDN workspace slug: "
            "letters, numbers, and hyphens only, without leading or trailing hyphens"
        )
    return workspace


def build_signed_smart_cdn_url(
    *,
    auth_key: str,
    auth_secret: str,
    workspace: str,
    template: str,
    input: str,
    url_params: Optional[dict[str, URL_PARAM_VALUES]] = None,
    expires_at_ms: Optional[int] = None,
) -> str:
    workspace_slug = quote_plus(_validate_workspace_slug(workspace))
    template_slug = quote_plus(template)
    input_field = quote_plus(input)

    expiry = (
        expires_at_ms
        if expires_at_ms is not None
        else int(time.time() * 1000) + 60 * 60 * 1000
    )

    params = []
    if url_params:
        for key, value in url_params.items():
            if key.lower() in RESERVED_URL_PARAMS:
                raise ValueError(
                    f"url_params must not include reserved Smart CDN parameter {key!r}"
                )
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                params.append((key, _stringify_url_param(value)))
            elif isinstance(value, (list, tuple)):
                params.append((key, [_stringify_url_param(item) for item in value]))
            else:
                raise ValueError(
                    "URL parameter values must be strings, numbers, booleans, arrays, "
                    f"or None. Got {type(value)} for {key}"
                )

    params.append(("auth_key", auth_key))
    params.append(("exp", str(expiry)))
    sorted_params = sorted(params, key=lambda item: item[0])
    query_string = urlencode(sorted_params, doseq=True)

    string_to_sign = f"{workspace_slug}/{template_slug}/{input_field}?{query_string}"
    algorithm = "sha256"
    signature = algorithm + ":" + hmac.new(
        auth_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"https://{workspace_slug}.tlcdn.com/{template_slug}/{input_field}"
        f"?{query_string}&sig={quote_plus(signature)}"
    )
