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
Cancellation waits for that upload batch, including retries, to finish before
releasing caller-owned files. Multipart cancellation drains active file reads.
Timeout and shutdown cleanup can therefore exceed the requested deadline; keep
file context managers open around the awaited call.

Client features
---------------

``AsyncTransloadit`` mirrors the existing synchronous client: Assembly creation,
retrieval, listing and cancellation; Template creation, retrieval, listing,
updates and deletion; monthly billing; and Smart CDN URL signing. Use the
Assembly helpers for multipart or resumable uploads and completion polling.
Await the async client's network methods; local factories and URL signing stay
synchronous.

Examples
--------

For copy/paste runnable examples, take a look at `examples/`_.

The examples cover sync uploads, async uploads, resumable uploads, Template usage,
sync and async Template lifecycle management, and Smart CDN URL signing.

.. _examples/: https://github.com/transloadit/python-sdk/tree/HEAD/examples
