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

    from transloadit.async_client import AsyncTransloadit

    async with AsyncTransloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET') as tl:
        response = await tl.get_assembly(assembly_id='abc')
        print(response.data['ok'])

        assembly = tl.new_assembly()
        assembly.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
        with open('PATH/TO/FILE.jpg', 'rb') as upload:
            assembly.add_file(upload)
            response = await assembly.create(wait=True, resumable=False)

If you do not use ``async with``, call ``await tl.aclose()`` when you are done with the session.

Examples
--------

For copy/paste runnable examples, take a look at `examples/`_.

The examples cover sync uploads, async uploads, resumable uploads, Template usage,
Template lifecycle management, and Smart CDN URL signing.

.. _examples/: https://github.com/transloadit/python-sdk/tree/HEAD/examples
