"""Run the API2 contract TUS Assembly scenario against a devdock API2 server.

This example is intentionally checked into the SDK repository: it should read
the API/TUS facts from API2's injected scenario JSON and exercise public SDK
methods as normal user code would.
"""

import json
import os
from pathlib import Path

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


def file_count(scenario):
    feature = feature_step(scenario, "preparations", "createTusAssembly", "feature-call")
    input_values = list(feature["input"].values())
    if len(input_values) != 1:
        fail(f"{feature['featureId']} expected exactly one input value")

    return input_values[0]


def scenario_bytes(scenario):
    source = scenario["upload"]["source"]
    if source["kind"] != "bytes":
        fail(f"unsupported scenario source kind {source['kind']!r}")
    if source["encoding"] != "utf8":
        fail(f"unsupported scenario source encoding {source['encoding']!r}")
    return source["value"].encode("utf-8")


def upload_config(scenario):
    upload = scenario["upload"]
    return {
        "content": scenario_bytes(scenario),
        "fieldname": upload["fieldName"],
        "filename": upload["fileName"],
        "user_meta": upload.get("userMeta") or {},
    }


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

    upload = upload_config(scenario)
    completed_assembly, upload_url = client.upload_tus_assembly(
        file_count(scenario),
        upload["content"],
        upload["fieldname"],
        upload["filename"],
        upload["user_meta"],
    )
    status = response_data(completed_assembly, "uploadTusAssembly")
    write_result(status, status, upload_url)

    print(f"Python Transloadit SDK devdock scenario {scenario['scenarioId']} passed for {endpoint}")


if __name__ == "__main__":
    main()
