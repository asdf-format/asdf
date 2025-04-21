.. currentmodule:: asdf

.. _overview:

********
Overview
********

Let's start by taking a look at a few basic ASDF use cases. This will introduce
you to some of the core features of ASDF and will show you how to get started
with using ASDF in your own projects.

To follow along with this tutorial, you will need to install the :mod:`asdf`
package. See :ref:`installation` for details.

Hello World
===========

At its core, ASDF is a way of saving nested data structures to YAML.  Here we
save a :class:`dict` with the key/value pair ``'hello': 'world'``.

.. runcode::

   from asdf import AsdfFile

   # Make the tree structure, and create a AsdfFile from it.
   tree = {'hello': 'world'}
   ff = AsdfFile(tree)
   ff.write_to("test.asdf")

   # You can also make the AsdfFile first, and modify its tree directly:
   ff = AsdfFile()
   ff.tree['hello'] = 'world'
   ff.write_to("test.asdf")

.. asdf:: test.asdf

Creating Files
==============

.. runcode:: hidden

    import asdf
    import numpy as np

    # Create some data
    sequence = np.arange(100)
    squares  = sequence**2
    random = np.random.random(100)

    # Store the data in an arbitrarily nested dictionary
    tree = {
        'foo': 42,
        'name': 'Monty',
        'sequence': sequence,
        'powers': { 'squares' : squares },
        'random': random
    }

    # Create the ASDF file object from our data tree
    af = asdf.AsdfFile(tree)

    # Write the data to a new file
    af.write_to('example.asdf')

.. include:: ../../README.rst
    :start-after: begin-create-file-text:
    :end-before: begin-example-asdf-metadata:

.. asdf:: example.asdf no_blocks

.. include:: ../../README.rst
    :start-after: end-example-asdf-metadata:
    :end-before: end-create-file-text:

A rendering of the binary data contained in the file can be found below. Observe that
the value of ``source`` in the metadata corresponds to the block number (e.g. ``BLOCK 0``)
of the block which contains the binary data.

.. asdf:: example.asdf no_header

.. include:: ../../README.rst
    :start-after: _begin-compress-file:
    :end-before: _end-compress-file:

.. _overview_reading:

Reading Files
=============

.. include:: ../../README.rst
    :start-after: begin-read-file-text:
    :end-before: end-read-file-text:
