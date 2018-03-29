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

.. include:: ../../README.rst
    :start-after: begin-create-file-text
    :end-before: end-create-file-text

Reading Files
=============

.. include:: ../../README.rst
    :start-after: begin-read-file-text
    :end-before: end-read-file-text
