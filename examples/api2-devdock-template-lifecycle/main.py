"""Run the API2 contract Template lifecycle scenario against a devdock API2 server.

This example is intentionally checked into the SDK repository: it should read
the API facts from API2's injected scenario JSON and exercise public SDK
methods as normal user code would.
"""

import json
import os
import time
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


def require_template_id(data, operation):
    template_id = data.get("id") or data.get("template_id")
    if not template_id:
        fail(f"{operation} returned no template id: {data!r}")
    return template_id


def template_content(content):
    if not isinstance(content, dict):
        fail(f"template content must be an object: {content!r}")

    rendered = dict(content.get("additionalProperties") or {})
    rendered["steps"] = content["steps"]

    return rendered


def template_payload(name, config):
    require_signature_auth = 1 if config["requireSignatureAuth"] else 0
    return {
        "name": name,
        "require_signature_auth": require_signature_auth,
        "template": template_content(config["content"]),
    }


def response_flag(data, *names):
    for name in names:
        if name in data:
            value = data[name]
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return value != 0
            if isinstance(value, str):
                return value.lower() in ("1", "true", "yes")
    return False


def template_result(data):
    content = data.get("content") or data.get("template") or {}
    if not isinstance(content, dict):
        fail(f"template response content must be an object: {content!r}")

    return {
        "content": content,
        "id": data.get("id") or data.get("template_id"),
        "name": data.get("name") or data.get("template_name"),
        "requireSignatureAuth": response_flag(
            data,
            "require_signature_auth",
            "requireSignatureAuth",
        ),
    }


def list_count(data):
    count = data.get("count")
    if isinstance(count, int):
        return count

    items = data.get("items")
    if isinstance(items, list):
        return len(items)

    fail(f"template list response did not contain a count or items list: {data!r}")


def deleted_get_result(response):
    data = response.data
    if not isinstance(data, dict):
        return False, ""

    error_code = data.get("error")
    if isinstance(error_code, str) and error_code:
        return False, error_code

    return response.status_code is not None and response.status_code < 400, ""


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

    template_name = f"{scenario['template']['namePrefix']}-{time.time_ns()}"
    template_id = None
    delete_template = True

    try:
        created = response_data(
            client.create_template(template_payload(template_name, scenario["template"])),
            "createTemplate",
        )
        template_id = require_template_id(created, "createTemplate")

        fetched = response_data(client.get_template(template_id), "getTemplate")
        listed = response_data(
            client.list_templates({"pagesize": scenario["list"]["pageSize"]}),
            "listTemplates",
        )

        updated_template_name = f"{template_name}{scenario['update']['nameSuffix']}"
        response_data(
            client.update_template(
                template_id,
                template_payload(updated_template_name, scenario["update"]),
            ),
            "updateTemplate",
        )
        updated = response_data(client.get_template(template_id), "getTemplate updated")

        response_data(client.delete_template(template_id), "deleteTemplate")
        delete_template = False

        deleted_get_succeeded, deleted_error_code = deleted_get_result(client.get_template(template_id))

        write_result(
            {
                "deletedErrorCode": deleted_error_code,
                "deletedGetSucceeded": deleted_get_succeeded,
                "fetched": template_result(fetched),
                "listCount": list_count(listed),
                "templateId": template_id,
                "templateName": template_name,
                "updated": template_result(updated),
                "updatedTemplateName": updated_template_name,
            }
        )
    finally:
        if template_id and delete_template:
            client.delete_template(template_id)

    print(f"Python Transloadit SDK devdock scenario {scenario['scenarioId']} passed for {endpoint}")


if __name__ == "__main__":
    main()
