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
interpreters. Asyncio support is tracked separately in
`#57 <https://github.com/transloadit/python-sdk/pull/57>`_ and can land in a later
2.x minor release. The dependency refresh shipped in 1.0.4 does not require
upgrading to 2.0.

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

Example
-------

For fully working examples, take a look at `examples/`_.

.. _examples/: https://github.com/transloadit/python-sdk/tree/HEAD/examples
