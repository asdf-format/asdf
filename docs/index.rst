pyasdf Documentation
====================

``pyasdf`` is a tool for reading and writing Advanced Scientific Data
Format (ASDF) files.

Installation
------------

``pyasdf`` requires:

- `python <http://www.python.org/>`__ 2.6, 2.7, 3.3, 3.4 or 3.5.

- `numpy <http://www.numpy.org/>`__ 1.6 or later

- `jsonschema <http://python-jsonschema.readthedocs.org/>`__ 2.3.0 or later

- `pyyaml <http://pyyaml.org>`__ 3.10 or later

- `six <https://pypi.python.org/pypi/six>`__ 1.9.0 or later

Support for units, time, transform, wcs, or running the tests also
requires:

- `astropy <http://www.astropy.org/>`__ 1.1 or later


Getting Started
---------------

The fundamental data model in ASDF is the ``tree``, which is a nested
combination of basic data structures: dictionaries, lists, strings and
numbers.  In addition, ASDF understands how to handle other types,
such as Numpy arrays.

In the simplest example, you create a tree, and write it to a ASDF
file.  ``pyasdf`` handles saving the Numpy array as a binary block
transparently:

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {
     'author': 'John Doe',
     'my_array': np.random.rand(8, 8)
   }
   ff = AsdfFile(tree)
   ff.write_to("example.asdf")

.. asdf:: example.asdf

Other :ref:`examples` are provided below.

.. toctree::
  :maxdepth: 2

  pyasdf/examples.rst
  pyasdf/extensions.rst

Commandline tool
----------------

``pyasdf`` includes a command-line tool, ``asdftool`` that performs a
number of basic operations:

  - ``explode``: Convert a self-contained ASDF file into exploded form.

  - ``implode``: Convert an ASDF file in exploded form into a
    self-contained file.

  - ``to_yaml``: Inline all of the data in an ASDF file so that it is
    pure YAML.

  - ``defragment``: Remove unused blocks and extra space.

Run ``asdftool --help`` for more information.

See also
--------

- The `Advanced Scientific Data Format (ASDF) standard
  <http://asdf-standard.readthedocs.org/>`__

Reference/API
-------------

.. automodapi:: pyasdf

.. automodapi:: pyasdf.fits_embed
