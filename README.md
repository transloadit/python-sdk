[![Build status](https://github.com/transloadit/python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/transloadit/python-sdk/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/transloadit/python-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/transloadit/python-sdk)

# Transloadit python-sdk

A **Python** Integration for [Transloadit](https://transloadit.com)'s file uploading and encoding service.

## Intro

[Transloadit](https://transloadit.com) is a service that helps you handle file uploads, resize, crop and watermark your images, make GIFs, transcode your videos, extract thumbnails, generate audio waveforms, and so much more. In short, [Transloadit](https://transloadit.com) is the Swiss Army Knife for your files.

This is a **Python** SDK to make it easy to talk to the [Transloadit](https://transloadit.com) REST API.

Only Python 3.9+ versions are supported.

## Install

```bash
pip install pytransloadit
```

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

## Example

For fully working examples, take a look at [`examples/`](https://github.com/transloadit/python-sdk/tree/HEAD/examples).

## Documentation

See [readthedocs](https://transloadit.readthedocs.io) for full API documentation.

## Contributing

### Running tests

You can mirror our GitHub Actions setup locally by running the test matrix inside Docker:

```bash
scripts/test-in-docker.sh
```

This script will:

- build images for the Python versions we test in CI (3.9–3.13)
- install Poetry, Node.js 20, and the Transloadit CLI
- pass credentials from `.env` (if present) so end-to-end tests can run against real Transloadit accounts

Signature parity tests use `npx transloadit smart_sig` under the hood, matching the reference implementation used by our other SDKs.

Pass `--python 3.12` (or set `PYTHON_VERSIONS`) to restrict the matrix, or append a custom command after `--`, for example `scripts/test-in-docker.sh -- pytest -k smartcdn`.

To exercise the optional end-to-end upload against a real Transloadit account, provide `TRANSLOADIT_KEY` and `TRANSLOADIT_SECRET` (via environment variables or `.env`) and set `PYTHON_SDK_E2E=1`:

```bash
PYTHON_SDK_E2E=1 scripts/test-in-docker.sh --python 3.12 -- pytest tests/test_e2e_upload.py
```

The test uploads `chameleon.jpg`, resizes it, and asserts on the live assembly results. It respects `TRANSLOADIT_HOST` and `TRANSLOADIT_REGION` overrides when present.

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
