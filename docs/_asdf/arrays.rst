.. currentmodule:: asdf

**********
Array Data
**********


Saving arrays
=============

Beyond the basic data types of dictionaries, lists, strings and numbers, the
most important thing ASDF can save is arrays.  It's as simple as putting a
:mod:`numpy` array somewhere in the tree.  Here, we save an 8x8 array of random
floating-point numbers (using `numpy.random.rand`).  Note that the resulting
YAML output contains information about the structure (size and data type) of
the array, but the actual array content is in a binary block.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {'my_array': np.random.rand(8, 8)}
   ff = AsdfFile(tree)
   ff.write_to("array.asdf")

.. note::

   In the file examples below, the first YAML part appears as it
   appears in the file.  Binary blocks are not shown as they are not
   human-readable.

.. code:: yaml

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
   my_array: !core/ndarray-1.1.0
     source: 0
     datatype: float64
     byteorder: little
     shape: [8, 8]
   ...

See :ref:`overview_reading` for a description of how to open this file.


Sharing of data
===============

Arrays that are views on the same data automatically share the same
data in the file.  In this example an array and a subview on that same
array are saved to the same file, resulting in only a single block of
data being saved.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   subset = my_array[2:4,3:6]
   tree = {
       'my_array': my_array,
       'subset':   subset
   }
   ff = AsdfFile(tree)
   ff.write_to("array_with_subset.asdf")

For circumstances where this is undesirable (such as saving
a small view of a large array) this can be disabled by setting
`asdf.config.AsdfConfig.default_array_save_base` (to set the default behavior)
or `asdf.AsdfFile.set_array_save_base` to control the behavior for
a specific array.

.. code:: yaml

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
   my_array: !core/ndarray-1.1.0
     source: 0
     datatype: float64
     byteorder: little
     shape: [8, 8]
   subset: !core/ndarray-1.1.0
     source: 0
     datatype: float64
     byteorder: little
     shape: [2, 3]
     offset: 152
     strides: [64, 8]
   ...

Saving inline arrays
====================

For small arrays, you may not care about the efficiency of a binary
representation and just want to save the array contents directly in the YAML
tree.  The `~asdf.AsdfFile.set_array_storage` method can be used to set the
storage type of the associated data. The allowed values are ``internal``,
``external``, and ``inline``.

- ``internal``: The default.  The array data will be
  stored in a binary block in the same ASDF file.

- ``external``: Store the data in a binary block in a separate ASDF file (also
  known as "exploded" format, which discussed below in :ref:`exploded`).

- ``inline``: Store the data as YAML inline in the tree.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)
   ff.set_array_storage(my_array, 'inline')
   ff.write_to("inline_array.asdf")

.. code:: yaml

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
   my_array: !core/ndarray-1.1.0
     data:
     - [0.37364029001505683, 0.32162730726994515, 0.5174687024953414, 0.6819358522124768,
       0.31545084462136797, 0.45336717886535716, 0.8766200166261489, 0.5351125807423055]
     - [0.21313738755058198, 0.08678080629794094, 0.262603440816942, 0.08050589478748083,
       0.137419316524092, 0.57123203453451, 0.40074196097349324, 0.849757947165214]
     - [0.23667849260250273, 0.024930741318300198, 0.9758526963943653, 0.03298431078548114,
       0.31662774377786995, 0.68377308750848, 0.790290072359762, 0.5050720750955217]
     - [0.7378502143845163, 0.8893229877547028, 0.5351249751905818, 0.0022624182357939837,
       0.7506228371871324, 0.9551597691023826, 0.1693896122914036, 0.8246100314570424]
     - [0.647505181978522, 0.33308226013000286, 0.8135005179839472, 0.8404212344059925,
       0.1562139195022587, 0.13503673673258954, 0.5874265747778596, 0.8032211348819358]
     - [0.42912361221963025, 0.12376484161537937, 0.650502918744316, 0.4687943836977091,
       0.38574705081654814, 0.195267928717743, 0.16493413972136817, 0.6627050583885223]
     - [0.4327563083511644, 0.7236790063915097, 0.22216584584793642, 0.10166807219644336,
       0.33464193496267347, 0.6941406199202252, 0.6329950377636102, 0.07729054807086944]
     - [0.12793926460863403, 0.9588116248796417, 0.2001139992410388, 0.48143125131473163,
       0.47964972042078724, 0.12156604005269112, 0.23365466431734938, 0.7703204892145835]
     datatype: float64
     shape: [8, 8]
   ...

Alternatively, it is possible to use the ``all_array_storage`` parameter of
`AsdfFile.write_to` and `AsdfFile.update` to control the storage
format of all arrays in the file.

.. code::

    # This controls the output format of all arrays in the file
    ff.write_to("all_inline.asdf", all_array_storage='inline')

For automatic management of the array storage type based on number of elements,
see :ref:`config_options_array_inline_threshold`.

.. _exploded:

Saving external arrays
======================

ASDF files may also be saved in "exploded form", which creates multiple files
corresponding to the following data items:

- One ASDF file containing only the header and tree.

- *n* ASDF files, each containing a single array data block.

Exploded form is useful in the following scenarios:

- Over a network protocol, such as HTTP, a client may only need to
  access some of the blocks.  While reading a subset of the file can
  be done using HTTP ``Range`` headers, it still requires one (small)
  request per block to "jump" through the file to determine the start
  location of each block.  This can become time-consuming over a
  high-latency network if there are many blocks.  Exploded form allows
  each block to be requested directly by a specific URI.

- An ASDF writer may stream a table to disk, when the size of the table
  is not known at the outset.  Using exploded form simplifies this,
  since a standalone file containing a single table can be iteratively
  appended to without worrying about any blocks that may follow it.

To save a block in an external file, set its block type to
``'external'``.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)

   # On an individual block basis:
   ff.set_array_storage(my_array, 'external')
   ff.write_to("external.asdf")

   # Or for every block:
   ff.write_to("external.asdf", all_array_storage='external')

.. code:: yaml

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
   my_array: !core/ndarray-1.1.0
     source: external0000.asdf
     datatype: float64
     byteorder: little
     shape: [8, 8]
   ...

Streaming array data
====================

In certain scenarios, you may want to stream data to disk, rather than
writing an entire array of data at once.  For example, it may not be
possible to fit the entire array in memory, or you may want to save
data from a device as it comes in to prevent data loss.  The ASDF
specification allows exactly one streaming block per file where the size of
the block isn't included in the block header, but instead is
implicitly determined to include all of the remaining contents of the
file.  By definition, it must be the last block in the file.

To use streaming, rather than including a Numpy array object in the
tree, you include a `asdf.tags.core.Stream` object which sets up the structure
of the streamed data, but will not write out the actual content.  The
file handle's ``write`` method is then used to manually write out the
binary data.

.. runcode::

   from asdf import AsdfFile
   from asdf.tags.core import Stream
   import numpy as np

   tree = {
       # Each "row" of data will have 128 entries.
       'my_stream': Stream([128], np.float64)
   }

   ff = AsdfFile(tree)
   with open('stream.asdf', 'wb') as fd:
       ff.write_to(fd)
       # Write 100 rows of data, one row at a time.  ``write``
       # expects the raw binary bytes, not an array, so we use
       # ``tobytes()``.
       for i in range(100):
           fd.write(np.array([i] * 128, np.float64).tobytes())

.. code:: yaml

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
   my_stream: !core/ndarray-1.1.0
     source: -1
     datatype: float64
     byteorder: little
     shape: ['*', 128]
   ...

When reading a file with a streamed block the streamed block will
be treated as a normal non-streamed block. It may be useful to enable
:ref:`memory_mapping` if the corresponding block is too large to hold in memory.

A case where streaming may be useful is when converting large data sets from a
different format into ASDF. In these cases it would be impractical to hold all
of the data in memory as an intermediate step. Consider the following example
that streams a large CSV file containing rows of integer data and converts it
to numpy arrays stored in ASDF:

.. code::

    import csv
    import numpy as np
    from asdf import AsdfFile
    from asdf.tags.core import Stream

    tree = {
        # We happen to know in advance that each row in the CSV has 100 ints
        'data': Stream([100], np.int64)
    }

    ff = AsdfFile(tree)
    # open the output file handle
    with open('new_file.asdf', 'wb') as fd:
        ff.write_to(fd)
        # open the CSV file to be converted
        with open('large_file.csv', 'r') as cfd:
            # read each line of the CSV file
            reader = csv.reader(cfd)
            for row in reader:
                # convert each row to a numpy array
                array = np.array([int(x) for x in row], np.int64)
                # write the array to the output file handle
                fd.write(array.tobytes())

Compression
===========

Individual blocks in an ASDF file may be compressed.

.. warning::

    Files created by ``asdf`` versions prior to ``5.2.1`` used an incorrect method of computing
    checksums for compressed blocks. This bug was fixed in ``5.2.1``.
    As a result files created by ``asdf<=5.2.0`` may fail block checksum validation with ``asdf>=5.2.1`` and vice-versa.

    By default ``asdf`` does not verify block checksums when reading a file so this change does not
    impact anyone already using the default configuration.
    If you encounter validation errors while reading a file created by an older or newer ``asdf`` version
    you will need to disable validation by setting ``validate_checksums=False`` in `asdf.open`.


`zlib <http://www.zlib.net/>`__ and `bzip2 <http://www.bzip.org>`__
are included in every asdf install. Passing one of these 4 character
codes as ``all_array_compression`` to `asdf.AsdfFile.write_to` will
compress all blocks with the corresponding algorithm:

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(32, 32),
       'b': np.random.rand(64, 64)
   }

   target = AsdfFile(tree)
   target.write_to('target.asdf', all_array_compression='zlib')
   target.write_to('target.asdf', all_array_compression='bzp2')

.. code:: yaml

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
   a: !core/ndarray-1.1.0
     source: 0
     datatype: float64
     byteorder: little
     shape: [32, 32]
   b: !core/ndarray-1.1.0
     source: 1
     datatype: float64
     byteorder: little
     shape: [64, 64]
   ...

The `lz4 <https://en.wikipedia.org/wiki/LZ_4>`__ compression algorithm is also
supported, but requires the optional
`lz4 <https://python-lz4.readthedocs.io/>`__ package in order to work.

Similarly, `asdf.config` can be used to configure compression of all
blocks by setting `asdf.config.AsdfConfig.all_array_compression`.

`asdf.AsdfFile.set_array_compression` can be used to set the compression
for a specific block. Similarly `asdf.AsdfFile.get_array_compression` can
be used to get the compression for a specific block.

.. code:: python

   import asdf
   import numpy as np

   af = asdf.AsdfFile({"arr": np.arange(42)})
   af.set_array_compression(af["arr"], "lz4")
   assert af.get_array_compression(af["arr"]) == "lz4"

When reading a file with compressed blocks, the blocks will be automatically
decompressed when accessed. If a file with compressed blocks is read and then
written out again, by default the new file will use the same compression as the
original file. This behavior can be overridden by explicitly providing a
different compression algorithm when writing the file out again.

.. code::

    import asdf

    # Open a file with some compression
    af = asdf.open('compressed.asdf')

    # Use the same compression when writing out a new file
    af.write_to('same.asdf')

    # Or specify the (possibly different) algorithm to use when writing out
    af.write_to('different.asdf', all_array_compression='lz4')

.. _memory_mapping:

Memory mapping
==============

When enabled, array data can be memory mapped using `numpy.memmap`. This
allows for the efficient use of memory even when reading files with very large
arrays. When memory mapping is enabled array data access must occur while
the corresponding file is open. This is most easily done using a ``with``
context.

.. code::

    import asdf

    with asdf.open('my_data.asdf', memmap=True) as af:
        # array data can be accessed since the with above
        # will keep my_data.asdf open
        print(af["my_array"][0])

Attempting to access memory mapped array data after the corresponding
file has been closed will result in an error.

.. warning::

   If a file is opened with memory mapping and write access
   any changes to the array data will change the corresponding file.
