"""Run the API2 contract TUS Assembly scenario against a devdock API2 server.

This example is intentionally checked into the SDK repository: it should read
the API/TUS facts from API2's injected scenario JSON and exercise public SDK
methods as normal user code would.
"""

import json
import os
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from transloadit.client import Transloadit
from tusclient import client as tus


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


def read_path(value, path_parts, label):
    current = value
    for part in path_parts:
        if isinstance(current, list) and isinstance(part, int):
            if part >= len(current):
                fail(f"{label} path {path_parts!r} index {part} is out of range")
            current = current[part]
            continue

        if isinstance(current, dict) and isinstance(part, str):
            if part not in current:
                fail(f"{label} path {path_parts!r} is missing key {part!r}")
            current = current[part]
            continue

        fail(f"{label} path {path_parts!r} cannot read {part!r} from {current!r}")

    return current


def resolve_value(value_spec, context, label):
    if "value" in value_spec:
        return value_spec["value"]

    source = value_spec.get("source")
    if not isinstance(source, dict):
        fail(f"{label} value spec has no literal value or source")

    root = source.get("root")
    if root not in context:
        fail(f"{label} value source root {root!r} is unavailable")

    path_parts = source.get("path") or []
    if not isinstance(path_parts, list):
        fail(f"{label} value source path must be a list")

    return read_path(context[root], path_parts, label)


def response_data(response, operation):
    data = response.data
    if not isinstance(data, dict):
        fail(f"{operation} returned non-JSON data: {data!r}")
    if data.get("error"):
        fail(f"{operation} returned {data.get('error')}: {data.get('message')}")
    return data


def feature_step(scenario, collection_name, feature_id, kind):
    steps = scenario.get(collection_name)
    if not isinstance(steps, list):
        fail(f"{collection_name} must be a list")

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            fail(f"{collection_name}[{index}] must be an object")
        if step.get("featureId") != feature_id:
            continue
        if step.get("kind") != kind:
            fail(f"{collection_name}[{index}] must have kind {kind!r}")
        return step

    fail(f"scenario has no {collection_name} step for feature {feature_id!r}")


def create_assembly(client, scenario):
    feature = feature_step(scenario, "preparations", "createTusAssembly", "feature-call")
    input_values = list(feature["input"].values())
    if len(input_values) != 1:
        fail(f"{feature['featureId']} expected exactly one input value")

    response = client.create_tus_assembly(input_values[0])
    data = response_data(response, feature["featureId"])
    for required_path in feature["requiredResponsePaths"]:
        value = read_path(data, required_path, feature["featureId"])
        if value is None or value == "":
            fail(f"{feature['featureId']} returned empty value at {required_path!r}")
    return data


def scenario_bytes(scenario):
    source = scenario["upload"]["source"]
    if source["kind"] != "bytes":
        fail(f"unsupported scenario source kind {source['kind']!r}")
    if source["encoding"] != "utf8":
        fail(f"unsupported scenario source encoding {source['encoding']!r}")
    return source["value"].encode("utf-8")


def upload_metadata(scenario, create_response):
    context = {"createResponse": create_response, "scenario": scenario}
    metadata = {}
    for field in scenario["upload"]["metadata"]:
        metadata[field["name"]] = str(resolve_value(field["value"], context, field["name"]))
    return metadata


def upload_with_tus(scenario, create_response):
    context = {"createResponse": create_response, "scenario": scenario}
    endpoint_url = str(resolve_value(scenario["upload"]["tusUrl"], context, "tusUrl"))
    content = scenario_bytes(scenario)
    chunk_size = len(content) if scenario["upload"]["chunkSize"] == "full-file" else None
    if chunk_size is None:
        fail(f"unsupported chunk size policy {scenario['upload']['chunkSize']!r}")

    uploader = tus.TusClient(endpoint_url).uploader(
        file_stream=BytesIO(content),
        chunk_size=chunk_size,
        metadata=upload_metadata(scenario, create_response),
        retries=scenario["upload"]["retries"],
    )
    uploader.upload()
    if not uploader.url:
        fail("TUS upload did not expose an upload URL")
    if uploader.offset != len(content):
        fail(f"TUS upload offset {uploader.offset}, expected {len(content)}")
    return uploader.url


def render_path_template(template_config, context, label):
    rendered = template_config["template"]
    for name, value_spec in template_config["replacements"].items():
        value = resolve_value(value_spec, context, f"{label}.{name}")
        rendered = rendered.replace("{" + name + "}", quote(str(value), safe=""))

    if "{" in rendered or "}" in rendered:
        fail(f"{label} still has unresolved placeholders: {rendered}")

    return rendered


def wait_for_assembly(client, scenario, create_response):
    feature = feature_step(scenario, "observations", "waitForAssembly", "feature-poll")
    context = {"createResponse": create_response, "scenario": scenario}
    wait_input = render_path_template(feature["input"], context, feature["featureId"])
    return response_data(client.wait_for_assembly(wait_input), feature["featureId"])


def write_result(create_response, status, upload_url):
    result_path = os.environ.get("API2_SDK_EXAMPLE_RESULT")
    if not result_path:
        return

    with Path(result_path).open("w", encoding="utf-8") as result_file:
        json.dump(
            {
                "createResponse": create_response,
                "status": status,
                "uploadUrl": upload_url,
            },
            result_file,
            indent=2,
        )
        result_file.write("\n")


def main():
    scenario = load_scenario()
    endpoint = required_env("TRANSLOADIT_ENDPOINT")
    client = Transloadit(
        auth_key=required_env("TRANSLOADIT_KEY"),
        auth_secret=required_env("TRANSLOADIT_SECRET"),
        service=endpoint,
    )

    create_response = create_assembly(client, scenario)
    upload_url = upload_with_tus(scenario, create_response)
    status = wait_for_assembly(client, scenario, create_response)
    write_result(create_response, status, upload_url)

    print(f"Python Transloadit SDK devdock scenario {scenario['scenarioId']} passed for {endpoint}")


if __name__ == "__main__":
    main()
