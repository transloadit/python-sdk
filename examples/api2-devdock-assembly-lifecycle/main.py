"""Run the API2 contract Assembly lifecycle scenario against a devdock API2 server.

This example is intentionally checked into the SDK repository: it should read
the API facts from API2's injected scenario JSON and exercise public SDK
methods as normal user code would.
"""

import json
import os
from pathlib import Path
from time import sleep

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


def assembly_result(data):
    return {
        "assemblyId": data.get("assembly_id") or data.get("assemblyId") or data.get("id"),
        "assemblySslUrl": data.get("assembly_ssl_url") or data.get("assemblySslUrl"),
        "assemblyUrl": data.get("assembly_url") or data.get("assemblyUrl"),
        "ok": data.get("ok"),
    }


def list_items(data):
    items = data.get("items")
    if isinstance(items, list):
        return items

    assemblies = data.get("assemblies")
    if isinstance(assemblies, list):
        return assemblies

    fail(f"assembly list response did not contain items or assemblies: {data!r}")


def list_count(data):
    count = data.get("count")
    if isinstance(count, int):
        return count

    return len(list_items(data))


def item_assembly_id(item):
    if not isinstance(item, dict):
        return None

    return item.get("assembly_id") or item.get("assemblyId") or item.get("id")


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

    created = response_data(
        client.create_tus_assembly(scenario["assembly"]["fileCount"]),
        "createTusAssembly",
    )
    created_result = assembly_result(created)
    assembly_id = created_result["assemblyId"]
    assembly_url = created_result["assemblySslUrl"]
    if not assembly_id:
        fail(f"createTusAssembly returned no assembly id: {created!r}")
    if not assembly_url:
        fail(f"createTusAssembly returned no assembly_ssl_url: {created!r}")

    cancel_on_exit = True

    try:
        fetched = response_data(
            client.get_assembly(assembly_url=assembly_url),
            "getAssemblyStatus",
        )
        # The Assembly list is eventually consistent: the API acknowledges creation before
        # the list storage row lands, so poll briefly until the created Assembly shows up.
        listed = response_data(
            client.list_assemblies(
                {
                    "assembly_id": assembly_id,
                    "pagesize": scenario["list"]["pageSize"],
                }
            ),
            "listAssemblies",
        )
        listed_items = list_items(listed)
        for _attempt in range(20):
            if any(item_assembly_id(item) == assembly_id for item in listed_items):
                break
            sleep(0.5)
            listed = response_data(
                client.list_assemblies(
                    {
                        "assembly_id": assembly_id,
                        "pagesize": scenario["list"]["pageSize"],
                    }
                ),
                "listAssemblies",
            )
            listed_items = list_items(listed)
        cancelled = response_data(
            client.cancel_assembly(assembly_url=assembly_url),
            "cancelAssembly",
        )
        cancel_on_exit = False

        write_result(
            {
                "cancelled": assembly_result(cancelled),
                "created": created_result,
                "fetched": assembly_result(fetched),
                "listContainsCreated": any(
                    item_assembly_id(item) == assembly_id for item in listed_items
                ),
                "listCount": list_count(listed),
            }
        )
    finally:
        if cancel_on_exit:
            client.cancel_assembly(assembly_url=assembly_url)

    print(
        "Python Transloadit SDK devdock scenario "
        f"{scenario['scenarioId']} canceled Assembly {assembly_id}"
    )


if __name__ == "__main__":
    main()
