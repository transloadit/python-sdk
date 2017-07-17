[![Build Status](https://travis-ci.org/transloadit/python-sdk.svg?branch=master)](https://travis-ci.org/transloadit/python-sdk)

# python-sdk

A **Python** Integration for [Transloadit](https://transloadit.com)'s file uploading and encoding service.

## Intro

[Transloadit](https://transloadit.com) is a service that helps you handle file uploads, resize, crop and watermark your images, make GIFs, transcode your videos, extract thumbnails, generate audio waveforms, and so much more. In short, [Transloadit](https://transloadit.com) is the Swiss Army Knife for your files.

This is a **Python** SDK to make it easy to talk to the [Transloadit](https://transloadit.com) REST API.

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

print assembly_response.data.get('assembly_id')

# or
print assembly_response.data['assembly_id']
```

## Example

For fully working examples, take a look at [`examples/`](https://github.com/transloadit/python-sdk/tree/master/examples).

## Documentation

See [readthedocs](https://transloadit.readthedocs.io) for full API documentation.
