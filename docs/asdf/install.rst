.. _installation:

************
Installation
************

There are several different ways to install the ``asdf`` package. Each is
described in detail below.

Requirements
============

The ``asdf`` package has the following dependencies:

- `python <https://www.python.org/>`__  3.3 or later

- `numpy <https://www.numpy.org/>`__ 1.8 or later

- `jsonschema <https://python-jsonschema.readthedocs.io/>`__ 2.3.0 or later

- `pyyaml <https://pyyaml.org>`__ 3.10 or later

- `semantic_version <https://python-semanticversion.readthedocs.io/>`__ 2.3.1 or later

- `six <https://pypi.python.org/pypi/six>`__ 1.9.0 or later

Support for units, time, transform, wcs, or running the tests also
requires:

- `astropy <https://www.astropy.org/>`__ 3.0 or later

Optional support for `lz4 <https://en.wikipedia.org/wiki/LZ4_(compression_algorithm)>`__
compression is provided by:

- `lz4 <https://python-lz4.readthedocs.io/>`__ 0.10 or later

Also required for running the tests:

- `pytest-astropy <https://github.com/astropy/pytest-astropy>`__

Installing with pip
===================

.. include:: ../../README.rst
    :start-after: begin-pip-install-text
    :end-before: begin-source-install-text

Installing with conda
=====================

ASDF is also distributed as a `conda <https://conda.io/docs/>`__ package via
the `conda-forge <https://conda-forge.org/>`__ channel. It is also available
through the `astroconda <https://astroconda.readthedocs.io/en/latest/>`__
channel.

To install ``asdf`` within an existing conda environment::

    $ conda install -c conda-forge asdf

To create a new conda environment and install ``asdf``::

    $ conda create -n new-env-name -c conda-forge python asdf

Building from source
====================

.. include:: ../../README.rst
    :start-after: begin-source-install-text
    :end-before: end-source-install-text

Running the tests
=================

.. include:: ../../README.rst
    :start-after: begin-testing-text
    :end-before: end-testing-text
