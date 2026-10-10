#!/usr/bin/env python3
"""Generate SDK methods from the pinned, unmodified API2 public contract.

No network or API2 checkout is needed for generation/checking. To update the pin,
pass --api2-root and --ref (a reviewed, committed producer revision).
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import pprint
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "contracts/api2-contract.json.gz"
LOCK = ROOT / "contracts/api2-contract.lock.json"
START = "    # <api2-generated-endpoints>"
END = "    # </api2-generated-endpoints>"
# Python compatibility names only. HTTP facts always come from the contract.
NAMES = {
    "create-template-credential": "create_template_credentials",
    "get-template-credential": "get_template_credentials",
    "update-template-credential": "update_template_credentials",
    "delete-template-credential": "delete_template_credentials",
    "options": "tus_options",
}
PARAMETERS = {
    "templateIdOrName": "template_id",
    "templateCredentialId": "identifier",
}


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).replace("-", "_").lower()


def method_name(operation):
    name = operation["id"].split(".", 1)[1]
    return NAMES.get(name, snake(name))


def schema(contract, ref):
    return contract["contract"]["schemas"][ref["$ref"].split("json-schema:", 1)[1]]


def render_method(operation, dispatch, exchange, contract, asynchronous):
    name = method_name(operation)
    method = operation["method"].lower()
    request = exchange["request"]
    params = []
    body = []
    await_ = "await " if asynchronous else ""
    def_ = "async def" if asynchronous else "def"
    path = operation["canonicalPath"]
    if dispatch.get("destination", {}).get("kind") == "status-stream":
        def_ = "def"  # Both return a managed stream, used with (async) with.
        params = ["stream_url", "*", "read_timeout=120", "max_event_size=1048576"]
        body = ["return self.request.stream_status(stream_url, read_timeout=read_timeout, max_event_size=max_event_size)"]
    elif request["kind"] == "protocol":
        arg = "assembly" if dispatch["destination"]["kind"] == "tus-collection" else "upload_url"
        params = [arg, "headers=None"]
        if request["body"]["kind"] == "binary":
            params.append("body=None")
        payload = "body" if request["body"]["kind"] == "binary" else "None"
        body = [f'return {await_}self.request.tus({operation["id"]!r}, {arg}, headers=headers, body={payload})']
    elif request["kind"] == "form":
        if "byFormField" not in dispatch["auth"]:
            raise ValueError(f"Unsupported form auth for {operation['id']}")
        params = ["data=None"]
        body = [f"return {await_}self.request.issue_bearer_token(data)"]
    elif name in {"get_assembly", "cancel_assembly"}:
        params = ["assembly_id=None", "assembly_url=None"]
        if method == "get":
            params.append("params=None")
        body = [
            'if not (assembly_id or assembly_url):',
            '    raise ValueError("Either assembly_id or assembly_url is required.")',
            'url = assembly_url if assembly_url else f"/assemblies/{self._quote_path_segment(assembly_id)}"',
            f'return {await_}self._request_assembly_url(url, {method.upper()!r}' + (", params=params)" if method == "get" else ")"),
        ]
    else:
        if request["kind"] != "normalized-params" and dispatch["auth"]["kind"] != "none":
            raise ValueError(f"Unsupported transport for {operation['id']}")
        path_params = re.findall(r"\{([^}]+)\}", path)
        for field in path_params:
            if field == "billYearMonth":
                params.extend(["month: int", "year: int"])
                path = path.replace("{billYearMonth}", "{year}-{month:02d}")
                continue
            arg = PARAMETERS.get(field, snake(field))
            params.append(f"{arg}: str")
            body.append(f"{arg} = require_path_id({arg}, {arg!r})")
            path = path.replace("{" + field + "}", "{self._quote_path_segment(" + arg + ")}")
        arg = "params" if method == "get" else "data"
        params.append(f"{arg}=None")
        call_args = [f"{arg}={arg}"]
        if request.get("transport", {}).get("additionalFields") == "form-fields-and-binary-files":
            params.extend(["extra_data=None", "files=None"])
            call_args.extend(["extra_data=extra_data", "files=files"])
        path_literal = ("f" if path_params else "") + repr(path)
        # Unauthenticated endpoint queries are ordinary query fields, not signed params.
        if dispatch["auth"]["kind"] == "none":
            body.append(f"return {await_}self.request.public({method.upper()!r}, {path_literal}, {', '.join(call_args)})")
        else:
            body.append(f"return {await_}self.request.{method}({path_literal}, {', '.join(call_args)})")
    summary = contract["apiReference"]["messages"][operation["summaryTextId"]]["source"]
    summary = summary.replace('"""', r'\"\"\"')
    doc = [summary, "", f"Contract operation: {operation['id']}."]
    if operation.get("stage"):
        doc += [f"Stage: {operation['stage']}; this API may change."]
    if request["kind"] == "protocol":
        doc += ["Pass protocol headers using headers; binary downloads return bytes."]
    if name == "stream_assembly_status":
        doc += ["Use with a context manager. Terminal events do not imply Assembly success."]
    lines = [f"    {def_} {name}(self, {', '.join(params)}):", '        """']
    lines += ["        " + line if line else "" for line in doc]
    lines += ['        """'] + ["        " + line for line in body]
    return "\n".join(lines)


def generate(contract, lock):
    operations = contract["apiReference"]["operations"]
    dispatches = {op["id"]: op for op in contract["contract"]["operations"]}
    if len({op["id"] for op in operations}) != len(operations):
        raise ValueError("Duplicate documented operation")
    if len({method_name(op) for op in operations}) != len(operations):
        raise ValueError("Duplicate Python method name")
    facts = {"operations": {}, "protocols": {}}
    outputs = {}
    for asynchronous, filename in [(False, "client.py"), (True, "async_client.py")]:
        blocks = []
        for operation in sorted(operations, key=lambda op: op["id"]):
            dispatch = dispatches[operation["id"]]
            exchange = contract["contract"]["exchanges"][dispatch["exchangeId"]]
            blocks.append(render_method(operation, dispatch, exchange, contract, asynchronous))
            facts["operations"][operation["id"]] = {
                "method": operation["method"].upper(), "path": operation["canonicalPath"],
                "python_method": method_name(operation), "stage": operation.get("stage"),
            }
            if exchange["request"]["kind"] == "protocol":
                headers = schema(contract, exchange["request"]["headers"])
                alternatives = headers.get("anyOf", [headers])
                defaults = None
                for alternative in alternatives:
                    values = {key: value["const"] for key, value in alternative.get("properties", {}).items()
                              if key in alternative.get("required", []) and "const" in value}
                    defaults = values if defaults is None else {k: v for k, v in defaults.items() if values.get(k) == v}
                facts["protocols"][operation["id"]] = {
                    "method": operation["method"].upper(), "destination": dispatch["destination"]["kind"],
                    "defaults": defaults,
                    "binary_response": any(r["bodyKind"] == "binary" for r in exchange["responses"]),
                }
            if "byFormField" in dispatch["auth"]:
                facts["token_auth"] = dispatch["auth"]["byFormField"]
            for response in exchange["responses"]:
                if response["bodyKind"] == "event-stream":
                    facts["stream_events"] = response["events"]
        path = ROOT / "transloadit" / filename
        text = path.read_text(encoding="utf-8")
        start, tail = text.split(START, 1)
        _, end = tail.split(END, 1)
        outputs[path] = start + START + "\n    # Generated by scripts/generate_endpoints.py; edit the generator, not this block.\n\n" + "\n\n".join(blocks) + "\n" + END + end
    facts["capability"] = {k: v for k, v in contract["capabilityPolicy"].items() if k != "routes"}
    facts["capability"]["routes"] = [
        {key: route[key] for key in ("kind", "path", "parameters")}
        for route in contract["capabilityPolicy"]["routes"]
    ]
    outputs[ROOT / "transloadit/_contract.py"] = "# Generated by scripts/generate_endpoints.py. Do not edit.\nCONTRACT = " + pprint.pformat(facts, width=100, sort_dicts=True) + "\n"
    rows = ["| Operation | HTTP request | Sync / async method | Stage |", "| --- | --- | --- | --- |"]
    for operation in sorted(operations, key=lambda op: op["id"]):
        rows.append(f"| `{operation['id']}` | `{operation['method'].upper()} {operation['canonicalPath']}` | `{method_name(operation)}` | {operation.get('stage', '')} |")
    coverage = ROOT / "docs/api-coverage.md"
    text = coverage.read_text(encoding="utf-8")
    start, tail = text.split("<!-- generated-coverage -->", 1)
    _, end = tail.split("<!-- /generated-coverage -->", 1)
    outputs[coverage] = start + "<!-- generated-coverage -->\n" + "\n".join(rows) + "\n<!-- /generated-coverage -->" + end
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--api2-root", type=Path)
    parser.add_argument("--ref")
    args = parser.parse_args()
    if args.api2_root or args.ref:
        if args.check or not (args.api2_root and args.ref):
            parser.error("Pin updates require --api2-root and --ref, without --check")
        revision = subprocess.check_output(["git", "-C", str(args.api2_root), "rev-parse", args.ref + "^{commit}"], text=True).strip()
        source_path = "api2/generated/contracts/v1/contract.json"
        raw = subprocess.check_output(["git", "-C", str(args.api2_root), "show", f"{revision}:{source_path}"])
        PIN.write_bytes(gzip.compress(raw, mtime=0))
        LOCK.write_text(json.dumps({"repository": "https://github.com/transloadit/api2", "revision": revision, "path": source_path,
                                    "sha256": hashlib.sha256(raw).hexdigest()}, indent=2) + "\n", encoding="utf-8", newline="\n")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    raw = gzip.decompress(PIN.read_bytes())
    if hashlib.sha256(raw).hexdigest() != lock["sha256"]:
        raise SystemExit("Pinned API2 contract hash mismatch")
    contract = json.loads(raw)
    if contract["formatVersion"] != 1 or contract["format"] != "transloadit-public-dispatch-contract":
        raise SystemExit("Unsupported API2 contract format")
    stale = []
    for path, text in generate(contract, lock).items():
        expected = text.encode("utf-8")
        if args.check:
            if not path.exists() or path.read_bytes() != expected:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_bytes(expected)
    if stale:
        raise SystemExit("Generated endpoints are stale: " + ", ".join(stale))
    print(f"{'Checked' if args.check else 'Generated'} {len(contract['apiReference']['operations'])} operations for sync and async clients")


if __name__ == "__main__":
    main()
