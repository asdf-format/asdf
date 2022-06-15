.. _installation:

************
Installation
************

There are several different ways to install the `asdf` package. Each is
described in detail below.

Requirements
============

The `asdf` package has several dependencies which are listed in the project's
build configuration (``setup.cfg`` / ``pyproject.toml``).  All dependencies are available on pypi and will be automatically
installed along with `asdf`.

Support for units, time, and transform tags requires an implementation of these
types.  One recommended option is the `astropy <https://www.astropy.org/>`__ package.

Optional support for `lz4 <https://en.wikipedia.org/wiki/LZ4_(compression_algorithm)>`__
compression is provided by the `lz4 <https://python-lz4.readthedocs.io/>`__ package.

Installing with pip
===================

.. include:: ../../README.rst
    :start-after: begin-pip-install-text:
    :end-before: begin-source-install-text:

Installing with conda
=====================

`asdf` is also distributed as a `conda <https://conda.io/docs/>`__ package via
the `conda-forge <https://conda-forge.org/>`__ channel. It is also available
through the `astroconda <https://astroconda.readthedocs.io/en/latest/>`__
channel.

To install `asdf` within an existing conda environment::

    $ conda install -c conda-forge asdf

To create a new conda environment and install `asdf`::

    $ conda create -n new-env-name -c conda-forge python asdf

Building from source
====================

.. include:: ../../README.rst
    :start-after: begin-source-install-text:
    :end-before: end-source-install-text:

Running the tests
=================

.. include:: ../../README.rst
    :start-after: begin-testing-text:
    :end-before: end-testing-text:
