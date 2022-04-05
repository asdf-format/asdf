ASDF - Advanced Scientific Data Format
======================================

.. image:: https://github.com/asdf-format/asdf/workflows/CI/badge.svg
    :target: https://github.com/asdf-format/asdf/actions
    :alt: CI Status

.. image:: https://github.com/asdf-format/asdf/workflows/s390x/badge.svg
    :target: https://github.com/asdf-format/asdf/actions
    :alt: s390x Status

.. image:: https://github.com/asdf-format/asdf/workflows/Downstream/badge.svg
    :target: https://github.com/asdf-format/asdf/actions
    :alt: Downstream CI Status

.. image:: https://readthedocs.org/projects/asdf/badge/?version=latest
    :target: https://asdf.readthedocs.io/en/latest/

.. image:: https://codecov.io/gh/asdf-format/asdf/branch/master/graphs/badge.svg
    :target: https://codecov.io/gh/asdf-format/asdf

.. image:: https://img.shields.io/pypi/l/asdf.svg
    :target: https://img.shields.io/pypi/l/asdf.svg

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
    :target: https://github.com/pre-commit/pre-commit
    :alt: pre-commit

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://pycqa.github.io/isort/


|

.. _begin-summary-text:

The **A**\ dvanced **S**\ cientific **D**\ ata **F**\ ormat (ASDF) is a
next-generation interchange format for scientific data. This package
contains the Python implementation of the ASDF Standard. More
information on the ASDF Standard itself can be found
`here <https://asdf-standard.readthedocs.io>`__.

The ASDF format has the following features:

* A hierarchical, human-readable metadata format (implemented using `YAML
  <http://yaml.org>`__)
* Numerical arrays are stored as binary data blocks which can be memory
  mapped. Data blocks can optionally be compressed.
* The structure of the data can be automatically validated using schemas
  (implemented using `JSON Schema <http://json-schema.org>`__)
* Native Python data types (numerical types, strings, dicts, lists) are
  serialized automatically
* ASDF can be extended to serialize custom data types

.. _end-summary-text:

ASDF is under active development `on github
<https://github.com/asdf-format/asdf>`__. More information on contributing
can be found `below <#contributing>`__.

Overview
--------

This section outlines basic use cases of the ASDF package for creating
and reading ASDF files.

Creating a file
~~~~~~~~~~~~~~~

.. _begin-create-file-text:

We're going to store several `numpy` arrays and other data to an ASDF file. We
do this by creating a "tree", which is simply a `dict`, and we provide it as
input to the constructor of `AsdfFile`:

.. code:: python

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

If we open the newly created file, we can see some of the key features
of ASDF on display:

::

    #ASDF 1.0.0
    #ASDF_STANDARD 1.2.0
    %YAML 1.1
    %TAG ! tag:stsci.edu:asdf/
    --- !core/asdf-1.1.0
    asdf_library: !core/software-1.0.0 {author: The ASDF Developers, homepage: 'http://github.com/asdf-format/asdf',
      name: asdf, version: 2.0.0}
    history:
      extensions:
      - !core/extension_metadata-1.0.0
        extension_class: asdf.extension.BuiltinExtension
        software: {name: asdf, version: 2.0.0}
    foo: 42
    name: Monty
    powers:
      squares: !core/ndarray-1.0.0
        source: 1
        datatype: int64
        byteorder: little
        shape: [100]
    random: !core/ndarray-1.0.0
      source: 2
      datatype: float64
      byteorder: little
      shape: [100]
    sequence: !core/ndarray-1.0.0
      source: 0
      datatype: int64
      byteorder: little
      shape: [100]
    ...

The metadata in the file mirrors the structure of the tree that was stored. It
is hierarchical and human-readable. Notice that metadata has been added to the
tree that was not explicitly given by the user. Notice also that the numerical
array data is not stored in the metadata tree itself. Instead, it is stored as
binary data blocks below the metadata section (not shown here).

It is possible to compress the array data when writing the file:

.. code:: python

    af.write_to('compressed.asdf', all_array_compression='zlib')

The built-in compression algorithms are ``'zlib'``, and ``'bzp2'``.  The
``'lz4'`` algorithm becomes available when the `lz4 <https://python-lz4.readthedocs.io/>`__ package
is installed.  Other compression algorithms may be available via extensions.

.. _end-create-file-text:

Reading a file
~~~~~~~~~~~~~~

.. _begin-read-file-text:

To read an existing ASDF file, we simply use the top-level `open` function of
the `asdf` package:

.. code:: python

    import asdf

    af = asdf.open('example.asdf')

The `open` function also works as a context handler:

.. code:: python

    with asdf.open('example.asdf') as af:
        ...

To get a quick overview of the data stored in the file, use the top-level
`AsdfFile.info()` method:

.. code:: python

    >>> import asdf
    >>> af = asdf.open('example.asdf')
    >>> af.info()
    root (AsdfObject)
    ├─asdf_library (Software)
    │ ├─author (str): The ASDF Developers
    │ ├─homepage (str): http://github.com/asdf-format/asdf
    │ ├─name (str): asdf
    │ └─version (str): 2.8.0
    ├─history (dict)
    │ └─extensions (list)
    │   └─[0] (ExtensionMetadata)
    │     ├─extension_class (str): asdf.extension.BuiltinExtension
    │     └─software (Software)
    │       ├─name (str): asdf
    │       └─version (str): 2.8.0
    ├─foo (int): 42
    ├─name (str): Monty
    ├─powers (dict)
    │ └─squares (NDArrayType): shape=(100,), dtype=int64
    ├─random (NDArrayType): shape=(100,), dtype=float64
    └─sequence (NDArrayType): shape=(100,), dtype=int64

The `AsdfFile` behaves like a Python `dict`, and nodes are accessed like
any other dictionary entry:

.. code:: python

    >>> af['name']
    'Monty'
    >>> af['powers']
    {'squares': <array (unloaded) shape: [100] dtype: int64>}

Array data remains unloaded until it is explicitly accessed:

.. code:: python

    >>> af['powers']['squares']
    array([   0,    1,    4,    9,   16,   25,   36,   49,   64,   81,  100,
            121,  144,  169,  196,  225,  256,  289,  324,  361,  400,  441,
            484,  529,  576,  625,  676,  729,  784,  841,  900,  961, 1024,
           1089, 1156, 1225, 1296, 1369, 1444, 1521, 1600, 1681, 1764, 1849,
           1936, 2025, 2116, 2209, 2304, 2401, 2500, 2601, 2704, 2809, 2916,
           3025, 3136, 3249, 3364, 3481, 3600, 3721, 3844, 3969, 4096, 4225,
           4356, 4489, 4624, 4761, 4900, 5041, 5184, 5329, 5476, 5625, 5776,
           5929, 6084, 6241, 6400, 6561, 6724, 6889, 7056, 7225, 7396, 7569,
           7744, 7921, 8100, 8281, 8464, 8649, 8836, 9025, 9216, 9409, 9604,
           9801])

    >>> import numpy as np
    >>> expected = [x**2 for x in range(100)]
    >>> np.equal(af['powers']['squares'], expected).all()
    True

By default, uncompressed data blocks are memory mapped for efficient
access. Memory mapping can be disabled by using the ``copy_arrays``
option of `open` when reading:

.. code:: python

    af = asdf.open('example.asdf', copy_arrays=True)

.. _end-read-file-text:

For more information and for advanced usage examples, see the
`documentation <#documentation>`__.

Extending ASDF
~~~~~~~~~~~~~~

Out of the box, the ``asdf`` package automatically serializes and
deserializes native Python types. It is possible to extend ``asdf`` by
implementing custom tags that correspond to custom user types. More
information on extending ASDF can be found in the `official
documentation <http://asdf.readthedocs.io/en/latest/#extending-asdf>`__.

Installation
------------

.. _begin-pip-install-text:

Stable releases of the ASDF Python package are registered `at
PyPi <https://pypi.python.org/pypi/asdf>`__. The latest stable version
can be installed using ``pip``:

::

    $ pip install asdf

.. _begin-source-install-text:

The latest development version of ASDF is available from the ``master`` branch
`on github <https://github.com/asdf-format/asdf>`__. To clone the project:

::

    $ git clone https://github.com/asdf-format/asdf

To install:

::

    $ cd asdf
    $ pip install .

To install in `development
mode <https://packaging.python.org/tutorials/distributing-packages/#working-in-development-mode>`__::

    $ pip install -e .

.. _end-source-install-text:

Testing
-------

.. _begin-testing-text:

To install the test dependencies from a source checkout of the repository:

::

    $ pip install -e ".[tests]"

To run the unit tests from a source checkout of the repository:

::

    $ pytest

It is also possible to run the test suite from an installed version of
the package.

::

    $ pip install "asdf[tests]"
    $ pytest --pyargs asdf

It is also possible to run the tests using `tox
<https://tox.readthedocs.io/en/latest/>`__.

::

   $ pip install tox

To list all available environments:

::

   $ tox -va

To run a specific environment:

::

   $ tox -e <envname>


.. _end-testing-text:

Documentation
-------------

More detailed documentation on this software package can be found
`here <https://asdf.readthedocs.io>`__.

More information on the ASDF Standard itself can be found
`here <https://asdf-standard.readthedocs.io>`__.

There are two mailing lists for ASDF:

* `asdf-users <https://groups.google.com/forum/#!forum/asdf-users>`_
* `asdf-developers <https://groups.google.com/forum/#!forum/asdf-developers>`_

    If you are looking for the **A**\ daptable **S**\ eismic **D**\ ata
    **F**\ ormat, information can be found
    `here <https://seismic-data.org/>`__.

Contributing
------------

We welcome feedback and contributions to the project. Contributions of
code, documentation, or general feedback are all appreciated. Please
follow the `contributing guidelines <CONTRIBUTING.md>`__ to submit an
issue or a pull request.

We strive to provide a welcoming community to all of our users by
abiding to the `Code of Conduct <CODE_OF_CONDUCT.md>`__.
