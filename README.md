---
title: ASDF - Advanced Scientific Data Format
---
<!-- --8<-- [start:badges] -->
[![CI Status](https://github.com/asdf-format/asdf/workflows/ci.yml/badge.svg)](https://github.com/asdf-format/asdf/actions/workflows/ci.yml)
[![image](https://readthedocs.org/projects/asdf/badge/?version=latest)](https://asdf.readthedocs.io/en/latest/)
[![image](https://codecov.io/gh/asdf-format/asdf/branch/main/graphs/badge.svg)](https://codecov.io/gh/asdf-format/asdf)
<!-- --8<-- [start:zenodo] -->
[![image](https://zenodo.org/badge/18112754.svg)](https://zenodo.org/badge/latestdoi/18112754)
<!-- # --8<-- [end:zenodo] -->
[![image](https://img.shields.io/pypi/l/asdf.svg)](https://img.shields.io/pypi/l/asdf.svg)
<!-- --8<-- [end:badges] -->

<!-- --8<-- [start:summary] -->
The **A**dvanced **S**cientific **D**ata **F**ormat (ASDF) is a
next-generation interchange format for scientific data. This package
contains the Python implementation of the ASDF specification. More
information on the ASDF file format including the specification can be
found [here](https://asdf-standard.readthedocs.io).
<!-- --8<-- [end:summary] -->

The ASDF format has the following features:

- Hierarchical and human-readable metadata in [YAML](http://yaml.org)
  format
- Efficient binary array storage with support for memory mapping and
  flexible compression.
- Content validation using schemas (using [JSON
  Schema](http://json-schema.org))
- Native and transparent support for most basic Python data types, with
  an extension API to add support for any custom Python object.

<div id="end-summary-text">

ASDF is under active development [on
github](https://github.com/asdf-format/asdf). More information on
contributing can be found below.

</div>

# Overview

This section outlines basic use cases of the ASDF package for creating
and reading ASDF files.

## Creating a file

<div id="begin-create-file-text">

We're going to store several [`numpy`][numpy] arrays
and other data to an ASDF file. We do this by creating a "tree", which
is simply a [`dict`][dict], and we provide it as
input to the constructor of \`AsdfFile\`:

</div>

``` python
import asdf
import numpy as np

# Create some data
sequence = np.arange(100)
squares = sequence**2
random = np.random.random(100)

# Store the data in an arbitrarily nested dictionary
tree = {
    "foo": 42,
    "name": "Monty",
    "sequence": sequence,
    "powers": {"squares": squares},
    "random": random,
}

# Create the ASDF file object from our data tree
af = asdf.AsdfFile(tree)

# Write the data to a new file
af.write_to("example.asdf")
```

If we open the newly created file's metadata section, we can see some of
the key features of ASDF on display:

<div id="begin-example-asdf-metadata">

``` yaml
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
```

</div>

<div id="end-example-asdf-metadata">

The metadata in the file mirrors the structure of the tree that was
stored. It is hierarchical and human-readable. Notice that metadata has
been added to the tree that was not explicitly given by the user. Notice
also that the numerical array data is not stored in the metadata tree
itself. Instead, it is stored as binary data blocks below the metadata
section (not shown above).

</div>

<div id="end-create-file-text">

<div id="begin-compress-file">

It is possible to compress the array data when writing the file:

</div>

</div>

``` python
af.write_to("compressed.asdf", all_array_compression="zlib")
```

The built-in compression algorithms are `'zlib'`, and `'bzp2'`. The
`'lz4'` algorithm becomes available when the
[lz4](https://python-lz4.readthedocs.io/) package is installed. Other
compression algorithms may be available via extensions.

## Reading a file

<div id="begin-read-file-text">

To read an existing ASDF file, we simply use the top-level
[`open`][asdf.open] function of the
[`asdf`][asdf] package:

</div>

``` python
import asdf

af = asdf.open("example.asdf")
```

The [`open`][asdf.open] function also works as a context
handler:

``` python
with asdf.open("example.asdf") as af:
    ...
```

To get a quick overview of the data stored in the file, use the
top-level [`AsdfFile.info()`][asdf.AsdfFile.info] method:

```pycon
>>> import asdf
>>> af = asdf.open("example.asdf")
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
```

The [`AsdfFile`][asdf.AsdfFile] behaves like a Python
[`dict`][dict], and nodes are accessed like any
other dictionary entry:

```pycon
>>> af["name"]
'Monty'
>>> af["powers"]
{'squares': <array (unloaded) shape: [100] dtype: int64>}
```

Array data remains unloaded until it is explicitly accessed:

```pycon
>>> af["powers"]["squares"]
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
>>> np.equal(af["powers"]["squares"], expected).all()
True
```

Memory mapping can be enabled by providing `memmap=True` to \`open\`:

``` python
af = asdf.open("example.asdf", memmap=True)
```

<div id="end-read-file-text">

For more information and for advanced usage examples, see the
[documentation](http://asdf.readthedocs.io/en/latest/).

</div>

## Extending ASDF

Out of the box, the `asdf` package automatically serializes and
deserializes native Python types. It is possible to extend `asdf` by
implementing custom tags that correspond to custom user types. More
information on extending ASDF can be found in the [official
documentation](http://asdf.readthedocs.io/en/latest/#extending-asdf).

# Installation

<div id="begin-pip-install-text">

Stable releases of the ASDF Python package are registered [at
PyPi](https://pypi.python.org/pypi/asdf). The latest stable version can
be installed using `pip`:

</div>

    $ pip install asdf

<div id="begin-source-install-text">

The latest development version of ASDF is available from the `main`
branch [on github](https://github.com/asdf-format/asdf). To clone the
project:

</div>

    $ git clone https://github.com/asdf-format/asdf

To install:

    $ cd asdf
    $ pip install .

To install in [development
mode](https://packaging.python.org/tutorials/distributing-packages/#working-in-development-mode):

    $ pip install -e .

# Testing

<div id="begin-testing-text">

To install the test dependencies from a source checkout of the
repository:

</div>

    $ pip install -e ".[tests]"

To run the unit tests from a source checkout of the repository:

    $ pytest

It is also possible to run the test suite from an installed version of
the package.

    $ pip install "asdf[tests]"
    $ pytest --pyargs asdf

It is also possible to run the tests using
[nox](https://nox.thea.codes/).

    $ pip install nox

To list all available sessions:

    $ nox -l

To run a specific session:

    $ nox -s "core-3.12"  # Run core ASDF tests in Python 3.12

Groups of sessions can also be specified by tag:

    $ nox -t downstream  # Run all downstream sessions

# Documentation

More detailed documentation on this software package can be found
[here](https://asdf.readthedocs.io).

More information on the ASDF file format itself can be found
[here](https://asdf-standard.readthedocs.io).

> If you are looking for the **A**daptable **S**eismic **D**ata
> **F**ormat, information can be found
> [here](https://seismic-data.org/).

# License

ASDF is licensed under a BSD 3-clause style license. See
[LICENSE](https://github.com/asdf-format/asdf/blob/main/LICENSE) for the
[licenses
folder](https://github.com/asdf-format/asdf/tree/main/licenses) for
licenses for any included software.

# Contributing

We welcome feedback and contributions to the project. Contributions of
code, documentation, or general feedback are all appreciated. Please
follow the [contributing
guidelines](https://github.com/asdf-format/asdf/blob/main/CONTRIBUTING.rst)
to submit an issue or a pull request.

We strive to provide a welcoming community to all of our users by
abiding to the [Code of
Conduct](https://github.com/asdf-format/asdf?tab=coc-ov-file).
