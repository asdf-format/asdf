# Overview

Let's start by taking a look at a few basic ASDF use cases. This will
introduce you to some of the core features of ASDF and will show you how
to get started with using ASDF in your own projects.

To follow along with this tutorial, you will need to install the `asdf`
package. See `installation` for details.

## Hello World

At its core, ASDF is a way of saving nested data structures to YAML.
Here we save a `dict` with the key/value pair `'hello': 'world'`.

```pycon
>>> from asdf import AsdfFile

>>> # Make the tree structure, and create a AsdfFile from it.
>>> tree = {'hello': 'world'}
>>> ff = AsdfFile(tree)
>>> ff.write_to("test.asdf")

>>> # You can also make the AsdfFile first, and modify its tree directly:
>>> ff = AsdfFile()
>>> ff.tree['hello'] = 'world'
>>> ff.write_to("test.asdf")

```

``` yaml
#ASDF 1.0.0
#ASDF_STANDARD 1.6.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.1.0
asdf_library: !core/software-1.0.0 {author: The ASDF Developers, homepage: 'http://github.com/asdf-format/asdf',
  name: asdf, version: 5.3.0}
history:
  extensions:
  - !core/extension_metadata-1.0.0
    extension_class: asdf.extension._manifest.ManifestExtension
    extension_uri: asdf://asdf-format.org/core/extensions/core-1.6.0
    manifest_software: !core/software-1.0.0 {name: asdf_standard, version: 1.5.0}
    software: !core/software-1.0.0 {name: asdf, version: 5.3.0}
hello: world
...
```

## Creating Files

We're going to store several [`numpy`][numpy] arrays
and other data to an ASDF file. We do this by creating a "tree", which
is simply a [`dict`][dict], and we provide it as
input to the constructor of \`AsdfFile\`:

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

``` yaml
#ASDF 1.0.0
#ASDF_STANDARD 1.6.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.1.0
asdf_library: !core/software-1.0.0 {author: The ASDF Developers, homepage: 'http://github.com/asdf-format/asdf',
  name: asdf, version: 5.3.0}
history:
  extensions:
  - !core/extension_metadata-1.0.0
    extension_class: asdf.extension._manifest.ManifestExtension
    extension_uri: asdf://asdf-format.org/core/extensions/core-1.6.0
    manifest_software: !core/software-1.0.0 {name: asdf_standard, version: 1.5.0}
    software: !core/software-1.0.0 {name: asdf, version: 5.3.0}
foo: 42
name: Monty
powers:
  squares: !core/ndarray-1.1.0
    source: 1
    datatype: int64
    byteorder: little
    shape: [100]
random: !core/ndarray-1.1.0
  source: 2
  datatype: float64
  byteorder: little
  shape: [100]
sequence: !core/ndarray-1.1.0
  source: 0
  datatype: int64
  byteorder: little
  shape: [100]
...
```

The metadata in the file mirrors the structure of the tree that was
stored. It is hierarchical and human-readable. Notice that metadata has
been added to the tree that was not explicitly given by the user. Notice
also that the numerical array data is not stored in the metadata tree
itself. Instead, it is stored as binary data blocks below the metadata
section (not shown above).

A rendering of the binary data contained in the file can be found below.
Observe that the value of `source` in the metadata corresponds to the
block number (e.g. `BLOCK 0`) of the block which contains the binary
data.

It is possible to compress the array data when writing the file:

``` python
af.write_to("compressed.asdf", all_array_compression="zlib")
```

The built-in compression algorithms are `'zlib'`, and `'bzp2'`. The
`'lz4'` algorithm becomes available when the
[lz4](https://python-lz4.readthedocs.io/) package is installed. Other
compression algorithms may be available via extensions.

## Reading Files

To read an existing ASDF file, we simply use the top-level
[`open`][asdf.open] function of the
[`asdf`][asdf] package:

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
>>> import asdf  # doctest: +SKIP
>>> af = asdf.open("example.asdf")  # doctest: +SKIP
>>> af.info()  # doctest: +SKIP
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
>>> af["name"]  # doctest: +SKIP
'Monty'
>>> af["powers"]  # doctest: +SKIP
{'squares': <array (unloaded) shape: [100] dtype: int64>}
```

Array data remains unloaded until it is explicitly accessed:

```pycon
>>> af["powers"]["squares"]  # doctest: +SKIP
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

>>> import numpy as np  # doctest: +SKIP
>>> expected = [x**2 for x in range(100)]  # doctest: +SKIP
>>> np.equal(af["powers"]["squares"], expected).all()  # doctest: +SKIP
True
```

Memory mapping can be enabled by providing `memmap=True` to \`open\`:

``` python
af = asdf.open("example.asdf", memmap=True)
```
