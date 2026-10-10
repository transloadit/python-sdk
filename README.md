[![Build status](https://github.com/transloadit/python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/transloadit/python-sdk/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/transloadit/python-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/transloadit/python-sdk)

# Transloadit python-sdk

A **Python** Integration for [Transloadit](https://transloadit.com)'s file uploading and encoding service.

## Intro

[Transloadit](https://transloadit.com) is a service that helps you handle file uploads, resize, crop and watermark your images, make GIFs, transcode your videos, extract thumbnails, generate audio waveforms, and so much more. In short, [Transloadit](https://transloadit.com) is the Swiss Army Knife for your files.

This is a **Python** SDK to make it easy to talk to the [Transloadit](https://transloadit.com) REST API.

Only Python 3.12+ versions are supported.

## Install

```bash
pip install pytransloadit
```

## Upgrading from 1.x to 2.0

Python 3.9, 3.10, and 3.11 are no longer supported. Upgrade your development,
CI, and deployment interpreters to Python 3.12 or newer before installing 2.0.
If you must keep an older interpreter, pin `pytransloadit<2` to stay on 1.x
(the latest 1.x release is 1.0.4).

2.0 requires `requests>=2.33,<3` and `urllib3>=2.7,<3`. Update any older
application pins or constraints and regenerate your lockfile before upgrading:

```bash
python -m pip install --upgrade 'pytransloadit>=2,<3'
```

The synchronous client API and imports remain compatible with 1.0.4 on supported
interpreters. SDK 2.0 adds the separate `AsyncTransloadit` client for asyncio
applications. The dependency refresh shipped in 1.0.4 does not require upgrading
to 2.0.

## Usage

```python
from transloadit import client

tl = client.Transloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET')
assembly = tl.new_assembly()
assembly.add_file(open('PATH/TO/FILE.jpg', 'rb'))
assembly.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
assembly_response = assembly.create(retries=5, wait=True)

print(assembly_response.data.get('assembly_id'))

# or
print(assembly_response.data['assembly_id'])
```

## Async usage

```python
import asyncio
import os
from transloadit.async_client import AsyncTransloadit

async def main():
    async with AsyncTransloadit(os.environ["TRANSLOADIT_KEY"], os.environ["TRANSLOADIT_SECRET"]) as tl:
        assembly = tl.new_assembly()
        assembly.add_step("resize", "/image/resize", {"width": 70, "height": 70})
        with open("PATH/TO/FILE.jpg", "rb") as upload:
            assembly.add_file(upload)
            response = await assembly.create(wait=True, resumable=False)
        print(response.data["ok"])

asyncio.run(main())
```

The async client keeps polling on `asyncio.sleep`. Resumable uploads still use the existing TUS client, but are offloaded with `asyncio.to_thread()` so the event loop stays responsive.

If you do not use `async with`, call `await tl.aclose()` when you are done with the session.

## API endpoint coverage

Both clients expose all **44 documented API operations**: Assemblies and SSE,
Templates, Template Credentials, auth keys and token issuance, DAM, statistics,
Billing, job slots, Assembly Notifications, and the six raw TUS operations.
See the [complete coverage table and generation instructions](docs/api-coverage.md).
The five DAM operations marked alpha retain that status. The 16 separate-product
routes deferred to 2.1 are tracked in [#60](https://github.com/transloadit/python-sdk/issues/60).

Ordinary GET methods take `params`, and other methods take `data`, as dictionaries
of the API's normalized request fields. Responses expose `.data`, `.status_code`
and `.headers`. For example, `await tl.list_auth_keys()` retrieves auth keys.
Check the endpoint reference for field names and required scopes. Signed requests
remain the default. To use a bearer token, pass
`bearer_token=token` to either client (the Auth Secret can be `None`).
`issue_bearer_token(data)` supports the contract's client-credentials,
authorization-code and refresh-token grants; omitted `grant_type` keeps the
client-credentials default. Tokens are not refreshed automatically.

SSE uses the returned Assembly `update_stream_url` and a context manager:

```python
# Inside an async function, after creating an Assembly:
async with tl.stream_assembly_status(created.data["update_stream_url"]) as events:
    async for event in events:
        print(event.event, event.data)
```

The sync equivalent uses `with` and `for`. Each event has `event`, parsed `data`,
`id`, `retry` and `terminal` attributes. Unknown events are delivered unchanged.
The stream stops on a terminal event; exiting the context, including cancellation,
closes the connection. A terminal event or disconnect does **not** establish
processing success: fetch `assembly_ssl_url` and inspect `ok`/`error`.
HTTP errors raise `transloadit.stream.StreamError` with `status_code`; streams
do not reconnect or replay automatically. Read inactivity defaults to 120 seconds,
and events are capped at 1 MiB; use `read_timeout` and `max_event_size` to adjust.

For low-level resumable control, `tus_options(assembly)` and
`create_upload(assembly, headers=..., body=...)` take the Assembly response, pairing
its `tus_url` with `assembly_ssl_url`. Successful creation exposes a validated
`.upload_url`, suitable for persisting and passing to `get_upload_offset`,
`patch_upload`, `download_upload` or `delete_upload`. Supply TUS fields such as
`Upload-Length` and `Upload-Offset` through `headers`, and supply base64-encoded
`filename` / `fieldname` entries in `Upload-Metadata` when creating uploads; the
client adds protocol defaults and the Assembly metadata. Downloads return bytes, including JSON-looking
files. These raw methods return HTTP errors as `Response` objects; inspect status
codes. The high-level Assembly/tuspy helpers still handle normal uploads and polling.

## Examples

For copy/paste runnable examples, take a look at
[`examples/`](https://github.com/transloadit/python-sdk/tree/HEAD/examples).

The examples cover sync uploads, async uploads, resumable uploads, Template usage,
sync and async Template lifecycle management, and Smart CDN URL signing.

## Documentation

See [readthedocs](https://transloadit.readthedocs.io) for full API documentation.

## Contributing

### Running tests

You can mirror our GitHub Actions setup locally by running the test matrix inside Docker:

```bash
scripts/test-in-docker.sh
```

This script will:

- build images for the Python versions we test in CI (3.12, 3.13, and 3.14)
- install Poetry, Node.js 24, and the Transloadit CLI
- pass credentials from `.env` (if present) so end-to-end tests can run against real Transloadit accounts

Signature parity tests use `npx transloadit smart_sig` under the hood, matching the reference implementation used by our other SDKs. Our GitHub Actions workflow also runs the E2E upload and quickstart examples against Python 3.14 on every push/PR using a dedicated Transloadit test account (wired through the `TRANSLOADIT_KEY` and `TRANSLOADIT_SECRET` secrets).

Pass `--python 3.14` (or set `PYTHON_VERSIONS`) to restrict the matrix, or append a custom command after `--`, for example `scripts/test-in-docker.sh -- pytest -k smartcdn`.

To exercise the optional end-to-end upload against a real Transloadit account, provide `TRANSLOADIT_KEY` and `TRANSLOADIT_SECRET` (via environment variables or `.env`) and set `PYTHON_SDK_E2E=1`:

```bash
PYTHON_SDK_E2E=1 scripts/test-in-docker.sh --python 3.14 -- pytest tests/test_e2e_upload.py tests/test_examples.py
```

The tests upload `chameleon.jpg`, run the copy/paste quickstart examples, and assert on the live assembly results.

If you have a global installation of `poetry`, you can run the tests with:

```bash
poetry run pytest --cov=transloadit tests
```

If you can't use a global installation of `poetry`, e.g. when using Nix Home Manager, you can create a Python virtual environment and install Poetry there:

```bash
python -m venv .venv && source .venv/bin/activate && pip install poetry && poetry install
```

Then to run the tests:

```bash
source .venv/bin/activate && poetry run pytest --cov=transloadit tests
```

Generate a coverage report with:

```bash
poetry run pytest --cov=transloadit --cov-report=html tests
```

Then view the coverage report locally by opening `htmlcov/index.html` in your browser.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local development, testing, and release instructions.
