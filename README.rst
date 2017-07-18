|Build Status|

python-sdk
==========

A **Python** Integration for `Transloadit`_\ ’s file uploading and
encoding service.

Intro
-----

`Transloadit`_ is a service that helps you handle file uploads, resize,
crop and watermark your images, make GIFs, transcode your videos,
extract thumbnails, generate audio waveforms, and so much more. In
short, `Transloadit`_ is the Swiss Army Knife for your files.

This is a **Python** SDK to make it easy to talk to the `Transloadit`_
REST API.

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

    print assembly_response.data.get('assembly_id')

    # or
    print assembly_response.data['assembly_id']

Example
-------

For fully working examples, take a look at ```examples/```_.

Documentation
-------------

See `readthedocs`_ for full API documentation.

.. _Transloadit: https://transloadit.com
.. _``examples/``: https://github.com/transloadit/python-sdk/tree/master/examples
.. _readthedocs: https://transloadit.readthedocs.io

.. |Build Status| image:: https://travis-ci.org/transloadit/python-sdk.svg?branch=master
   :target: https://travis-ci.org/transloadit/python-sdk
