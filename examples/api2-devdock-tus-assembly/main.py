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


def sdk_feature_call(scenario, feature_id):
    feature_calls = scenario.get("sdkFeatureCalls")
    if not isinstance(feature_calls, list):
        fail("sdkFeatureCalls must be a list")

    for index, feature_call in enumerate(feature_calls):
        if not isinstance(feature_call, dict):
            fail(f"sdkFeatureCalls[{index}] must be an object")
        if feature_call.get("featureId") != feature_id:
            continue
        if feature_call.get("kind") != "sdk-feature-call":
            fail(f"sdkFeatureCalls[{index}] must have kind 'sdk-feature-call'")
        return feature_call

    fail(f"scenario has no SDK feature call for feature {feature_id!r}")


def upload_tus_assembly_input(scenario):
    feature_call = sdk_feature_call(scenario, "uploadTusAssembly")
    input_values = feature_call.get("input")
    if not isinstance(input_values, dict):
        fail("sdkFeatureCalls.uploadTusAssembly.input must be an object")

    return input_values


def scenario_bytes(upload):
    content = upload.get("content")
    if not isinstance(content, str):
        fail("sdkFeatureCalls.uploadTusAssembly.input.upload.content must be a string")

    return content.encode("utf-8")


def upload_config(input_values):
    upload = input_values.get("upload")
    if not isinstance(upload, dict):
        fail("sdkFeatureCalls.uploadTusAssembly.input.upload must be an object")

    return {
        "content": scenario_bytes(upload),
        "fieldname": upload["fieldname"],
        "filename": upload["filename"],
        "user_meta": upload.get("user_meta") or {},
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

    input_values = upload_tus_assembly_input(scenario)
    upload = upload_config(input_values)
    completed_assembly, upload_url = client.upload_tus_assembly(
        input_values["file_count"],
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
