"""Run the API2 contract TUS resume scenario against a devdock API2 server.

This example is intentionally checked into the SDK repository: it reads the
API/TUS facts from API2's injected scenario JSON, interrupts an upload like an
unlucky user would, and resumes it through the public SDK method.
"""

import base64
import json
import os
from pathlib import Path
from urllib.parse import urljoin

import requests

from transloadit.client import Transloadit


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def fail(message):
    raise RuntimeError(message)


def load_scenario():
    configured_path = os.environ.get("API2_SDK_EXAMPLE_SCENARIO")
    scenario_path = (
        Path(configured_path) if configured_path else Path(__file__).with_name("api2-scenario.json")
    )
    with scenario_path.open(encoding="utf-8") as scenario_file:
        return json.load(scenario_file)


def response_data(response, operation):
    data = response.data
    if not isinstance(data, dict):
        fail(f"{operation} returned non-JSON data: {data!r}")
    if data.get("error"):
        fail(f"{operation} returned {data.get('error')}: {data.get('message')}")
    return data


def resolve_value(value_spec, context, label):
    if not isinstance(value_spec, dict):
        fail(f"{label} value spec must be an object")
    if "value" in value_spec:
        return value_spec["value"]

    source = value_spec.get("source")
    if not isinstance(source, dict):
        fail(f"{label} value spec has no literal value or source")
    root = source.get("root")
    if not isinstance(root, str) or root not in context:
        fail(f"{label} value source root is unavailable")
    current = context[root]
    for part in source.get("path", []):
        if not isinstance(current, dict) or part not in current:
            fail(f"{label} value source cannot read {part}")
        current = current[part]
    return current


def scenario_bytes(upload):
    source = upload.get("source")
    if not isinstance(source, dict) or source.get("kind") != "bytes":
        fail("upload.source.kind must be bytes")
    if source.get("encoding") != "utf8":
        fail("upload.source.encoding must be utf8")
    return str(source["value"]).encode("utf-8")


def upload_metadata(upload, context):
    metadata = {}
    for field in upload.get("metadata", []):
        metadata[field["name"]] = str(resolve_value(field["value"], context, field["name"]))
    return metadata


def create_interrupted_upload(tus_url, content, metadata, stop_after_accepted_bytes):
    """Create a TUS upload and only send the first chunk, leaving the upload
    interrupted the way a dropped connection would."""
    metadata_parts = []
    for name, value in metadata.items():
        encoded_value = base64.b64encode(value.encode("utf-8")).decode("ascii")
        metadata_parts.append(f"{name} {encoded_value}")

    create_response = requests.post(
        tus_url,
        data=b"",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(len(content)),
            "Upload-Metadata": ",".join(metadata_parts),
        },
        timeout=60,
    )
    if create_response.status_code != 201:
        fail(f"TUS create returned HTTP {create_response.status_code}, expected 201")
    location = create_response.headers.get("Location")
    if not location:
        fail("TUS create did not return a Location header")
    upload_url = urljoin(tus_url, location)

    patch_response = requests.patch(
        upload_url,
        data=content[:stop_after_accepted_bytes],
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Offset": "0",
            "Content-Type": "application/offset+octet-stream",
        },
        timeout=60,
    )
    if patch_response.status_code != 204:
        fail(f"TUS first chunk returned HTTP {patch_response.status_code}, expected 204")
    accepted_bytes = int(patch_response.headers.get("Upload-Offset", "-1"))
    if accepted_bytes != stop_after_accepted_bytes:
        fail(
            f"TUS first chunk accepted {accepted_bytes} bytes, "
            f"expected {stop_after_accepted_bytes}"
        )

    return upload_url


def write_result(result):
    result_path = os.environ.get("API2_SDK_EXAMPLE_RESULT")
    if not result_path:
        return

    with Path(result_path).open("w", encoding="utf-8") as result_file:
        json.dump(result, result_file, indent=2)
        result_file.write("\n")


def main():
    scenario = load_scenario()
    endpoint = required_env("TRANSLOADIT_ENDPOINT")
    client = Transloadit(
        auth_key=required_env("TRANSLOADIT_KEY"),
        auth_secret=required_env("TRANSLOADIT_SECRET"),
        service=endpoint,
    )

    create_response = scenario.get("prepared", {}).get("createResponse")
    if not isinstance(create_response, dict):
        fail("prepared.createResponse must be an object")
    upload = scenario.get("upload")
    if not isinstance(upload, dict):
        fail("upload must be an object")
    resume = upload.get("resume")
    if not isinstance(resume, dict):
        fail("upload.resume must be an object")

    context = {"createResponse": create_response, "scenario": scenario}
    content = scenario_bytes(upload)
    tus_url = str(resolve_value(upload["tusUrl"], context, "upload.tusUrl"))
    metadata = upload_metadata(upload, context)

    first_upload_url = create_interrupted_upload(
        tus_url,
        content,
        metadata,
        resume["stopAfterAcceptedBytes"],
    )

    # Remember the interrupted upload by fingerprint, like a TUS client URL storage would.
    stored_uploads = {resume["fingerprint"]: first_upload_url}
    previous_upload_count = len(stored_uploads)

    completed_assembly = client.resume_tus_upload(
        stored_uploads[resume["fingerprint"]],
        content,
        create_response["assembly_ssl_url"],
    )
    response_data(completed_assembly, "resumeTusUpload")

    if resume["removeFingerprintOnSuccess"]:
        del stored_uploads[resume["fingerprint"]]
    remaining_previous_upload_count = len(stored_uploads)

    write_result(
        {
            "firstUploadUrl": first_upload_url,
            "previousUploadCount": previous_upload_count,
            "remainingPreviousUploadCount": remaining_previous_upload_count,
            "uploadUrl": first_upload_url,
        }
    )

    print(
        "Python Transloadit SDK devdock scenario "
        f"{scenario['exampleInput']['scenarioId']} resumed {first_upload_url}"
    )


if __name__ == "__main__":
    main()
