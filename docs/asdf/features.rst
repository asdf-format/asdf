.. currentmodule:: asdf

*************
Core Features
*************

This section discusses the core features of the ASDF data format, and provides
examples and use cases that are specific to the Python implementation.

Data Model
==========

The fundamental data object in ASDF is the ``tree``, which is a nested
combination of basic data structures: dictionaries, lists, strings and numbers.
In Python, these types correspond to :class:`dict`, :class:`list`,
:class:`str`, and :class:`int`, :class:`float`, and :class:`complex`,
respectively. The top-level tree object behaves like a Python dictionary and
supports arbitrary nesting of data structures. For simple examples of creating
and reading trees, see :ref:`overview`.

.. note::

   The ASDF Standard imposes a maximum size of 52 bits for integer literals in
   the tree (see `the docs <https://asdf-standard.readthedocs.io/en/latest/known_limits.html#literal-integer-values-in-the-tree>`_
   for details and justification). Attempting to store a larger value will
   result in a validation error.

   Integers and floats of up to 64 bits can be stored inside of :mod:`numpy`
   arrays (see below).

   For arbitrary precision integer support, see `IntegerType`.


One of the key features of ASDF is its ability to serialize :mod:`numpy`
arrays. This is discussed in detail in :ref:`array-data`.

While the core ASDF package supports serialization of basic data types and
Numpy arrays, its true power comes from its ability to be extended to support
serialization of a wide range of custom data types. Details on using ASDF
extensions can be found in :ref:`using_extensions`. Details on creating custom
ASDF extensions to support custom data types can be found in :ref:`extensions`.

.. _array-data:

Array Data
==========

Much of ASDF's power and convenience comes from its ability to represent
multidimensional array data. The :mod:`asdf` Python package provides native
support for :mod:`numpy` arrays.

.. toctree::
    :maxdepth: 2

    arrays

.. _using_extensions:

Using extensions
================

According to Wikipedia, serialization "is the process of translating data
structures or object state into a format that can be stored...and reconstructed
later" [#wiki]_.

The power of ASDF is that it provides the ability to store, or serialize, the
state of Python objects into a *human-readable* data format. The state of those
objects can later be restored by another program in a process called
deserialization.

While ASDF is capable of serializing basic Python types and Numpy arrays out of
the box, it can also be extended to serialize arbitrary custom data types. This
section discusses the extension mechanism from a user's perspective. For
documentation on creating extensions, see :ref:`extensions`.

Even though this particular implementation of ASDF necessarily serializes
Python data types, in theory an ASDF implementation in another language could
read the resulting file and reconstruct an analogous type in that language.
Conversely, this implementation can read ASDF files that were written by other
implementations of ASDF as long as the proper extensions are available.

.. toctree::
    :maxdepth: 2

    using_extensions 

.. _schema_validation:

Schema validation
=================

Schema validation is used to determine whether an ASDF file is well formed. All
ASDF files must conform to the schemas defined by the `ASDF Standard
<https://asdf-standard.readthedocs.io/en/latest/>`_. Schema validation occurs
when reading ASDF files (using `asdf.open`), and also when writing them out
(using `AsdfFile.write_to` or `AsdfFile.update`).

Schema validation also plays a role when using custom extensions (see
:ref:`using_extensions` and :ref:`extensions`). Extensions must provide schemas
for the types that they serialize. When writing a file with custom types, the
output is validated against the schemas corresponding to those types. If the
appropriate extension is installed when reading a file with custom types, then
the types will be validated against the schemas provided by the corresponding
extension.

.. _custom-schemas:

Custom schemas
--------------

Every ASDF file is validated against the ASDF Standard, and also against any
schemas provided by custom extensions. However, it is sometimes useful for
particular applications to impose additional restrictions when deciding whether
a given file is valid or not.

For example, consider an application that processes digital image data. The
application expects the file to contain an image, and also some metadata about
how the image was created. The following example schema reflects these
expectations:

.. code:: yaml

    %YAML 1.1
    ---
    $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
    id: "http://stsci.edu/schemas/asdf/core/asdf-1.1.0"

    tag: "tag:stsci.edu:asdf/core/asdf-1.1.0"
    type: object
    properties:
      image:
        description: An ndarray containing image data.
        $ref: "ndarray-1.0.0"

      metadata:
        type: object
        description: Metadata about the image
        properties:
          time:
            description: |
              A timestamp for when the image was created, in UTC.
            type: string
            format: date-time
          resolution:
            description: |
              A 2D array representing the resolution of the image (N x M).
            type: array
            items:
              type: integer
              number: 2

    required: [image, metadata]
    additionalProperties: true

This schema restricts the kinds of files that will be accepted as valid to
those that contain a top-level ``image`` property that is an ``ndarray``, and
a top-level ``metadata`` property that contains information about the time the
image was taken and the resolution of the image. Note that the schema uses the
same ``id`` and ``tag`` as the `top-level core schema`_ from the ASDF Standard.
This is because it is validating the file at the top level, but is imposing
restrictions beyond what is normally required for an ASDF file.

In order to use this schema for a secondary validation pass, we pass the
`custom_schema` argument to either `asdf.open` or the `AsdfFile` constructor.
Assume that the schema file lives in ``image_schema.yaml``, and we wish to
open a file called ``image.asdf``. We would open the file with the following
code:

.. code::

    import asdf
    af = asdf.open('image.asdf', custom_schema='image_schema.yaml')

Similarly, if we wished to use this schema when creating new files:

.. code::

    new_af = asdf.AsdfFile(custom_schema='image_schema.yaml')
    ...

.. _top-level core schema:
    https://github.com/spacetelescope/asdf-standard/blob/master/schemas/stsci.edu/asdf/core/asdf-1.1.0.yaml

.. _version_and_compat:

Versioning and Compatibility
============================

There are several different versions to keep in mind when discussing ASDF:

* The software package version
* The ASDF Standard version
* The ASDF file format version
* Individual tag and schema versions

Each ASDF file contains information about the various versions that were used
to create the file. The most important of these are the ASDF Standard version
and the ASDF file format version. A particular version of the ASDF software
package will explicitly provide support for a specific combination of these
versions.

Tag and schema versions are also important for serializing and deserializing
data types that are stored in ASDF files. A detailed discussion of tag and
schema versions from a user perspective can be found in
:ref:`custom_type_versions`.

Since ASDF is designed to serve as an archival format, the software attempts to
provide backwards compatibility when reading older versions of the ASDF
Standard and ASDF file format. However, since deserializing ASDF types
sometimes requires other software packages, backwards compatibility is often
contingent on the available versions of such software packages.

In general, forward compatibility with newer versions of the ASDF Standard and
ASDF file format is not supported by the software. However, if newer tag and
schema versions are detected, the software will attempt to process them.

When creating new ASDF files, it is possible to control the version of the file
format that is used. This can be specified by passing the `version` argument to
either the `AsdfFile` constructor when the file object is created, or to the
`AsdfFile.write_to` method when it is written. By default, the latest version
of the file format will be used. Note that this option has no effect on the
versions of tag types from custom extensions.

External References
===================

Tree References
---------------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but users
of ``asdf`` can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

   import asdf
   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.arange(0, 10),
       'b': np.arange(10, 20)
   }

   target = AsdfFile(tree)
   target.write_to('target.asdf')

.. asdf:: target.asdf

Then we will reference those arrays in a couple of different ways.
First, we'll load the source file in Python and use the
`make_reference` method to generate a reference to array ``a``.
Second, we'll work at the lower level by manually writing a JSON
Pointer to array ``b``, which doesn't require loading or having access
to the target file.

.. runcode::

   ff = AsdfFile()

   with asdf.open('target.asdf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.asdf#b'}

   ff.write_to('source.asdf')

.. asdf:: source.asdf

Calling `~asdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   with asdf.open('source.asdf') as ff:
       ff.find_references()
       assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~asdf.AsdfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   with asdf.open('source.asdf') as ff:
       ff.resolve_references()
       ff.write_to('resolved.asdf')

.. asdf:: resolved.asdf

A similar feature provided by YAML, anchors and aliases, also provides
a way to support references within the same file.  These are supported
by asdf, however the JSON Pointer approach is generally favored because:

   - It is possible to reference elements in another file

   - Elements are referenced by location in the tree, not an
     identifier, therefore, everything can be referenced.

Anchors and aliases are handled automatically by ``asdf`` when the
data structure is recursive.  For example here is a dictionary that is
included twice in the same tree:

.. runcode::

    d = {'foo': 'bar'}
    d['baz'] = d
    tree = {'d': d}

    ff = AsdfFile(tree)
    ff.write_to('anchors.asdf')

.. asdf:: anchors.asdf

.. _array-references:

Array References
----------------

ASDF files can refer to array data that is stored in other files using the
`ExternalArrayReference` type.

External files need not be ASDF files: ASDF is completely agnostic as to the
format of the external file. The ASDF external array reference does not define
how the external data file will be resolved; in fact it does not even check for
the existence of the external file. It simply provides a way for ASDF files to
refer to arrays that exist in external files.

Creating an external array reference is simple. Only four pieces of information
are required:

* The name of the external file. Since ASDF does not itself resolve the file or
  check for its existence, the format of the name is not important. In most
  cases the name will be a path relative to the ASDF file itself, or a URI
  for a network resource.
* The data type of the array data. This is a string representing any valid
  `numpy.dtype`.
* The shape of the data array. This is a tuple representing the dimensions of
  the array data.
* The array data ``target``. This is either an integer or a string that
  indicates to the user something about how the data array should be accessed
  in the external file. For example, if there are multiple data arrays in the
  external file, the ``target`` might be an integer index. Or if the external
  file is an ASDF file, the ``target`` might be a string indicating the key to
  use in the external file's tree. The value and format of the ``target`` field
  is completely arbitrary since ASDF will not use it itself.

As an example, we will create a reference to an external CSV file. We will
assume that one of the rows of the CSV file contains the array data we care
about:

.. runcode::

    import asdf

    csv_data_row = 10 # The row of the CSV file containing the data we want
    csv_row_size = 100 # The size of the array
    extref = asdf.ExternalArrayReference('data.csv', csv_data_row, "int64", (csv_row_size,))

    tree = {'csv_data': extref}
    af = asdf.AsdfFile(tree)
    af.write_to('external_array.asdf')

.. asdf:: external_array.asdf

When reading a file containing external references, the user is responsible for
using the information in the `ExternalArrayReference` type to open the external
file and retrieve the associated array data.

Saving history entries
======================

``asdf`` has a convenience method for notating the history of transformations
that have been performed on a file.

Given a `~asdf.AsdfFile` object, call `~asdf.AsdfFile.add_history_entry`, given
a description of the change and optionally a description of the software (i.e.
your software, not ``asdf``) that performed the operation.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(32, 32)
   }

   ff = AsdfFile(tree)
   ff.add_history_entry(
       "Initial random numbers",
       {'name': 'asdf examples',
        'author': 'John Q. Public',
        'homepage': 'http://github.com/spacetelescope/asdf',
        'version': '0.1'})
   ff.write_to('example.asdf')

.. asdf:: example.asdf

ASDF automatically saves history metadata about the extensions that were used
to create the file. This information is used when opening files to determine if
the proper extensions are installed (see :ref:`extension_checking` for more
details).

.. _asdf-in-fits:

Saving ASDF in FITS
===================

.. note::

    This section is about packaging entire ASDF files inside of
    `FITS data format <https://en.wikipedia.org/wiki/FITS>`_ files. This is
    probably only of interest to astronomers. Making use of this feature
    requires the `astropy` package to be installed.

Sometimes you may need to store the structured data supported by ASDF inside of
a FITS file in order to be compatible with legacy tools that support only FITS.

First, create an `~astropy.io.fits.HDUList` object using `astropy.io.fits`.
Here, we are building an `~astropy.io.fits.HDUList` from scratch, but it could
also have been loaded from an existing file.

We will create a FITS file that has two image extensions, SCI and DQ
respectively.

.. runcode::

    from astropy.io import fits

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='SCI'))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='DQ'))

Next we make a tree structure out of the data in the FITS file.  Importantly,
we use the *same* array references in the FITS `~astropy.io.fits.HDUList` and
store them in the tree. By doing this, ASDF will automatically refer to the
data in the regular FITS extensions.

.. runcode::

    tree = {
        'model': {
            'sci': {
                'data': hdulist['SCI'].data,
            },
            'dq': {
                'data': hdulist['DQ'].data,
            }
        }
    }

Now we take both the FITS `~astropy.io.fits.HDUList` and the ASDF tree and
create an `AsdfInFits` object.

.. runcode::

    from asdf import fits_embed

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to('embedded_asdf.fits')

.. runcode:: hidden

    from astropy.io import fits

    with fits.open('embedded_asdf.fits') as new_hdulist:
        with open('content.asdf', 'wb') as fd:
            fd.write(new_hdulist['ASDF'].data.tostring())

The special ASDF extension in the resulting FITS file contains the following
data.  Note that the data source of the arrays uses the ``fits:`` prefix to
indicate that the data comes from a FITS extension:

.. asdf:: content.asdf

To load an ASDF-in-FITS file, simply open it using `asdf.open`. The returned
value will be an `AsdfInFits` object, which can be used in the same way as any
other `AsdfFile` object.

.. runcode::

    with asdf.open('embedded_asdf.fits') as asdf_in_fits:
        science = asdf_in_fits.tree['model']['sci']


.. rubric:: Footnotes

.. [#wiki] https://en.wikipedia.org/wiki/Serialization
