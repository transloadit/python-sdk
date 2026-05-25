from urllib.parse import urlparse


def normalize_service_url(service):
    if not isinstance(service, str):
        raise ValueError("service must be a URL string.")

    normalized_service = service.strip()
    if not normalized_service:
        raise ValueError("service must be a non-empty URL.")
    if "://" in normalized_service and not normalized_service.startswith(
        ("http://", "https://")
    ):
        raise ValueError("service must use http or https.")
    if not normalized_service.startswith(("http://", "https://")):
        normalized_service = "https://" + normalized_service

    parsed_service = urlparse(normalized_service)
    if parsed_service.scheme not in {"http", "https"} or not parsed_service.netloc:
        raise ValueError("service must include a valid host.")
    return normalized_service


def require_path_id(value, name):
    if value is None or not str(value).strip():
        raise ValueError(f"{name} cannot be empty.")
    return str(value)


def should_sign_api_url(url, service):
    if not url.startswith(("http://", "https://")):
        return True

    parsed_url = urlparse(url)
    parsed_service = urlparse(service)
    # Only same-service URLs and Transloadit API regional hosts may receive auth params.
    if (
        parsed_url.scheme == parsed_service.scheme
        and (parsed_url.hostname or "").lower() == (parsed_service.hostname or "").lower()
        and parsed_url.port == parsed_service.port
    ):
        return True

    service_hostname = (parsed_service.hostname or "").lower()
    service_is_transloadit_api = service_hostname == "api2.transloadit.com" or (
        service_hostname.startswith("api2-")
        and service_hostname.endswith(".transloadit.com")
    )
    hostname = (parsed_url.hostname or "").lower()
    url_is_transloadit_api = hostname == "api2.transloadit.com" or (
        hostname.startswith("api2-") and hostname.endswith(".transloadit.com")
    )
    return (
        service_is_transloadit_api
        and parsed_url.scheme == "https"
        and url_is_transloadit_api
    )
