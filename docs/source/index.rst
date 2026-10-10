.. transloadit documentation master file, created by
   sphinx-quickstart on Sat Jul 15 15:25:58 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to transloadit's Python SDK documentation!
==================================================

|Build Status|

.. |Build Status| image:: https://github.com/transloadit/python-sdk/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/transloadit/python-sdk/actions/workflows/ci.yml

`Transloadit`_ is a service that helps you handle file uploads, resize,
crop and watermark your images, make GIFs, transcode your videos,
extract thumbnails, generate audio waveforms, and so much more. In
short, `Transloadit`_ is the Swiss Army Knife for your files.

This is a **Python** SDK to make it easy to talk to the `Transloadit`_
REST API.

Only Python 3.12+ versions are supported.

.. _Transloadit: https://transloadit.com

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   transloadit



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Quickstart
==========

Install
-------

.. code:: bash

    pip install pytransloadit

Upgrading from 1.x to 2.0
-------------------------

Python 3.9, 3.10, and 3.11 are no longer supported. Upgrade development,
CI, and deployment interpreters to Python 3.12 or newer before installing 2.0.
If you must keep an older interpreter, pin ``pytransloadit<2`` to stay on 1.x
(the latest 1.x release is 1.0.4).

2.0 requires ``requests>=2.33,<3`` and ``urllib3>=2.7,<3``. Update older
application pins or constraints and regenerate your application lockfile.

.. code:: bash

    python -m pip install --upgrade 'pytransloadit>=2,<3'

The synchronous client API and imports remain compatible with 1.0.4 on supported
interpreters. SDK 2.0 adds the separate ``AsyncTransloadit`` client for asyncio
applications. The dependency refresh shipped in 1.0.4 does not require upgrading
to 2.0.

Usage
-----

.. code:: python

    from transloadit import client

    tl = client.Transloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET')
    assembly = tl.new_assembly()
    assembly.add_file(open('PATH/TO/FILE.jpg', 'rb'))
    assembly.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
    assembly_response = assembly.create(retries=5, wait=True)

    print(assembly_response.data.get('assembly_id'))

    # or
    print(assembly_response.data['assembly_id'])

Async usage
-----------

.. code:: python

    import asyncio
    import os
    from transloadit.async_client import AsyncTransloadit

    async def main():
        async with AsyncTransloadit(os.environ['TRANSLOADIT_KEY'], os.environ['TRANSLOADIT_SECRET']) as tl:
            assembly = tl.new_assembly()
            assembly.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
            with open('PATH/TO/FILE.jpg', 'rb') as upload:
                assembly.add_file(upload)
                response = await assembly.create(wait=True, resumable=False)
            print(response.data['ok'])

    asyncio.run(main())

If you do not use ``async with``, call ``await tl.aclose()`` when you are done with the session.
Resumable uploads through tuspy run in a worker thread; polling uses ``asyncio.sleep``.

Endpoint coverage
-----------------

Both clients implement all 44 documented operations: 38 API2 endpoints plus six
raw TUS operations. See the `coverage table`_ for methods, HTTP routes, alpha
stages and the pinned contract generation/check procedure. The 16 separate-product
storage/device/OAuth routes are tracked for 2.1 in `issue 60`_.

GET methods accept normalized API fields in ``params``; other ordinary methods
accept ``data``. Creation and replacement of Assemblies also accept ``extra_data``
and ``files``. Requests are signed by default; pass ``bearer_token`` to use an
existing token. ``issue_bearer_token`` also supports authorization-code and refresh
flows. Automatic refresh is not performed.

``stream_assembly_status`` takes the returned ``update_stream_url`` and is used
with ``with`` / ``async with``. Iterate its events with ``for`` / ``async for``;
the context closes the connection on exit or cancellation. Unknown events remain
available to callers. Terminal events and disconnects do not imply success:
fetch the final Assembly Status and inspect ``ok`` / ``error``. HTTP failures
raise ``transloadit.stream.StreamError``. Read inactivity defaults to 120 seconds
and event size to 1 MiB, adjustable through ``read_timeout`` / ``max_event_size``.
There is no automatic reconnect or replay.

For raw TUS, pass the Assembly response to ``tus_options`` / ``create_upload``.
Creation pairs ``tus_url`` and ``assembly_ssl_url`` and returns a validated
``upload_url`` alongside the response. Persist that URL for offset queries,
append, download and deletion. Pass protocol headers with ``headers`` and upload
bytes with ``body``. Include base64-encoded ``filename`` / ``fieldname`` entries in
``Upload-Metadata`` when creating uploads. The client adds the Assembly metadata.
Downloads always return bytes. Raw methods return HTTP errors
as Response objects; inspect their status. Existing high-level upload helpers
still manage normal uploads and polling.

.. _coverage table: https://github.com/transloadit/python-sdk/blob/asyncio-v2/docs/api-coverage.md
.. _issue 60: https://github.com/transloadit/python-sdk/issues/60

Examples
--------

For copy/paste runnable examples, take a look at `examples/`_.

The examples cover sync uploads, async uploads, resumable uploads, Template usage,
sync and async Template lifecycle management, and Smart CDN URL signing.

.. _examples/: https://github.com/transloadit/python-sdk/tree/HEAD/examples
