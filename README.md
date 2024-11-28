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