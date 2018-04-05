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


The built-in extension
----------------------

The ability to serialize the following types is provided by ASDF's built-in
extension:

* `dict`
* `list`
* `str`
* `int`
* `float`
* `complex`
* `numpy.ndarray`

The built-in extension is packaged with ASDF and is automatically used when
reading and writing files. Users can not control the use of the built-in
extension and in general they need not concern themselves with the details of
its implementation. However, it is useful to be aware that the built-in
extension is always in effect when reading and writing ASDF files.

Custom types
------------

For the purposes of this documentation, a "custom type" is any data type that
can not be serialized by the built-in extension.

In order for a particular custom type to be serialized, a special class called
a "tag type" (or "tag" for short) must be implemented. Each tag type defines
how the corresponding custom type will be serialized and deserialized. More
details on how tag types are implemented can be found in :ref:`extensions`.
Users should never have to refer to tag implementations directly; they simply
enable ASDF to recognize and process custom types.

In addition to tag types, each custom type must have a corresponding schema,
which is used for validation. The definition of the schema is closely tied to
the definition of the tag type. More details on schema validation can be found
in :ref:`schema_validation`.

All schemas and their associated tag types have versions that move in sync. The
version will change whenever a schemas (and therefore the tag type
implementation) changes.

Extensions
----------

In order for the tag types and schemas to be used by ASDF, they must be
packaged into an **extension** class. In general, the details of extensions are
transparent to users of ASDF. However, users need to be aware of extensions in
the following two scenarios:

* when storing custom data types to files to be written
* when reading files that contain custom data types

These scenarios require the use of custom extensions (the built-in extension is
always used). There are two ways to use custom extensions, which are detailed
below in :ref:`other_packages` and :ref:`explicit_extensions`.

Writing custom types to files
*****************************

ASDF is not capable of serializing any custom type unless an extension is
provided that defines how to serialize that type. Attempting to do so will
cause an error when trying to write the file. For details on writing custom tag
types and extensions, see :ref:`extensions`.

.. _reading_custom_types:

Reading files with custom types
*******************************

The ASDF software is capable of reading files that contain custom data types
even if the extension that was used to create the file is not present. However,
the extension is required in order to properly deserialize the original type.

If the necessary extension is **not** present, the custom data types will
simply appear in the tree as a nested combination of basic data types. The
structure of this data will mirror the structure of the schema used serialize
the custom type.

In this case, a warning will occur by default to indicate to the user that the
custom type in the file was not recognized and can not be deserialized. To
suppress these warnings, users should pass ``ignore_unrecognized_tag=True`` to
`asdf.open`.

Even if an extension for the custom type is present, it does not guarantee that
the type can be deserialized successfully. Instantiating the custom type may
involve additional software dependencies, which, if not present, will cause an
error when the type is deserialized. Users should be aware of the dependencies
that are required for instantiating custom types when reading ASDF files.

Custom types, extensions, and versioning
----------------------------------------

All tag types and schemas are versioned. This allows changes to tags and
schemas to be recorded, and it allows ASDF to define behavior with respect to
version compatibility.

Tag and schema versions may change for several reasons. One common reason is to
reflect a change to the API of the custom type that a tag represents. This
typically corresponds to an update to the version of the software that defines
that custom type.

Since ASDF is designed to be an archival file format, it attempts to maintain
backwards compatibility with all older tag and schema versions, at least when
reading files. However, there are some caveats, which are described below.

Reading files
*************

When ASDF encounters a tagged object in a file, it will compare the
version of the tag in the file with the version of the corresponding tag type
(if one is provided by an available extension).

In general, when reading files ASDF abides by the following principles:

* If a tag type is available and its version matches that of the tag in the
  file, ASDF will return an instance of the original custom type.
* If no corresponding tag type is found in any available extension, ASDF will
  return a basic data structure representing the type. A warning will occur
  unless the option ``ignore_unrecognized_tag=True`` was given. (see
  :ref:`reading_custom_types`).
* If a tag type is available but its version is **older** than that in the file
  (meaning that the file was written using a newer version of the tag type),
  ASDF will attempt to deserialize the tag using the existing tag type. If this
  fails, ASDF will return a basic data structure representing the type, and a
  warning will occur.
* If a tag type is available but its version is **newer** than that in the
  file, ASDF will attempt to deserialize the tag using the existing tag type.
  If this fails, ASDF will return a basic data structure representing the type,
  and a warning will occur.

In cases where the available tag type version does not match the version of the
tag in the file, warnings can be enabled by passing
``ignore_version_mismatch=False`` to `asdf.open`. These warnings are ignored by
default.

Writing files
*************

In general, ASDF makes no guarantee of being able to write older versions of
tag types.

Explicit version support
************************

Some tag types explicitly support reading only particular versions of the tag
and schema (see `asdf.CustomType.supported_versions`). In these cases,
deserialization is only possible if the version in the file matches one of the
explicitly supported versions. Otherwise, ASDF will return a basic data
structure representing the type, and a warning will occur.

Caveats
*******

While ASDF makes every attempt to deserialize stored objects even in the
case of a tag version mismatch, deserialization will not always be possible. In
most cases, if the versions do not match, ASDF will be able to return a basic
data structure representing the original type.

However, tag version mismatches often indicate a mismatch between the versions
of the software packages that define the type being serialized. In some cases,
these version incompatibilities may lead to errors when attempting to read a
file (especially when multiple tags/packages are involved). In these cases, the
best course of action is to try to install the necessary versions of the
packages (and extensions) involved.

.. _other_packages:

Extensions from other packages
------------------------------

Some external packages may define extensions that allow ASDF to recognize some
or all of the types that are defined by that package. Such packages may install
the extension class as part of the package itself (details for developers can
be found in :ref:`packaging_extensions`).

If the package installs its extension, then ASDF will automatically detect the
extension and use it when processing any files. No specific action is required
by the user in order to successfully read and write custom types defined by
the extension for that particular package.

Users can use the ``extensions`` command of the ``asdftool`` command line tool
in order to determine which packages in the current Python environment have
installed ASDF extensions:

.. code-block:: none

    $ asdftool extensions -s
    Extension Name: 'bizbaz' (from bizbaz 1.2.3) Class: bizbaz.io.asdf.extension.BizbazExtension
    Extension Name: 'builtin' (from asdf 2.0.0) Class: asdf.extension.BuiltinExtension

The output will always include the built-in extension, but may also display
other extensions from other packages, depending on what is installed.

.. _explicit_extensions:

Explicit use of extensions
--------------------------

Sometimes no packaged extensions are provided for the types you wish to
serialize. In this case, it is necessary to explicitly provide any necessary
extension classes when reading and writing files that contain custom types.

Both `asdf.open` and the `AsdfFile` constructor take an optional `extensions`
keyword argument to control which extensions are used when reading or creating
ASDF files.

Consider the following example where there exists a custom type
``MyCustomType`` that needs to be written to a file. An extension is defined
``MyCustomExtension`` that contains a tag type that can serialize and
deserialize ``MyCustomType``. Since ``MyCustomExtension`` is not installed by
any package, we will need to pass it directly to the `AsdfFile` constructor:

.. code-block:: python

    import asdf

    ...

    af = asdf.AsdfFile(extensions=MyCustomExtension())
    af.tree = {'thing': MyCustomType('foo') }
    # This call would cause an error if the proper extension was not
    # provided to the constructor
    af.write_to('custom.asdf')

Note that the extension class must actually be instantiated when it is passed
as the `extensions` argument.

To read the file, we pass the same extension to `asdf.open`:

.. code-block:: python

    import asdf

    af = asdf.open('custom.asdf', extensions=MyCustomExtension())

If necessary, it is also possible to pass a list of extension instances to
`asdf.open` and the `AsdfFile` constructor:

.. code-block:: python

    extensions = [MyCustomExtension(), AnotherCustomExtension()]
    af = asdf.AsdfFile(extensions=extensions)

Passing either a single extension instance or a list of extension instances to
either `asdf.open` or the `AsdfFile` constructor will not override any
extensions that are installed in the environment. Instead, the custom types
provided by the explicitly provided extensions will be added to the list of any
types that are provided by installed extensions.

Extension checking
------------------

When writing ASDF files using this software, metadata about the extensions that
were used to create the file will be added to the file itself. For extensions
that were provided with another software package, the metadata includes the
version of that package.

When reading files with extension metadata, ASDF can check whether the required
extensions are present before processing the file. If a required extension is
not present, or if the wrong version of a package that provides an extension is
installed, ASDF will issue a warning.

It is possible to turn these warnings into errors by using the
`strict_extension_check` parameter of `asdf.open`. If this parameter is set to
`True`, then opening the file will fail if the required extensions are missing.

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
for the types that they serialize.

Warnings and errors
-------------------

All schemas are versioned. Schema versions 

Discuss warning control using ``ignore_version_mismatch``.
The documentation on ``ignore_unrecognized_tag`` should be mentioned here but
detailed discussion probably belongs in the section about extensions.

Custom schemas
--------------

Versioning and Compatibility
============================

There are several different versions to keep in mind when discussing ASDF:

* Software package version
* ASDF standard version
* ASDF file format version
* Individual tag and schema versions


ASDF is designed to serve as an archival format.

Mention the use of the ``version`` argument in the constructor and the
``write_to`` function.


External References
===================

Array References
----------------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but users
of ``asdf`` can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

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

   with AsdfFile.open('target.asdf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.asdf#b'}

   ff.write_to('source.asdf')

.. asdf:: source.asdf

Calling `~asdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   with AsdfFile.open('source.asdf') as ff:
       ff.find_references()
       assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~asdf.AsdfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   with AsdfFile.open('source.asdf') as ff:
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

Array References
----------------

Saving history entries
======================

``asdf`` has a convenience method for notating the history of
transformations that have been performed on a file.

Given a `~asdf.AsdfFile` object, call
`~asdf.AsdfFile.add_history_entry`, given a description of the
change and optionally a description of the software (i.e. your
software, not ``asdf``) that performed the operation.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(256, 256)
   }

   ff = AsdfFile(tree)
   ff.add_history_entry(
       u"Initial random numbers",
       {u'name': u'asdf examples',
        u'author': u'John Q. Public',
        u'homepage': u'http://github.com/spacetelescope/asdf',
        u'version': u'0.1'})
   ff.write_to('example.asdf')

.. asdf:: example.asdf

Saving ASDF in FITS
===================

Sometimes you may need to store the structured data supported by ASDF
inside of a FITS file in order to be compatible with legacy tools that
support only FITS.  This can be achieved by including a special
extension with the name ``ASDF`` to the FITS file, containing the YAML
tree from an ASDF file.  The array tags within the ASDF tree point
directly to other binary extensions in the FITS file.

First, make a FITS file in the usual way with astropy.io.fits.  Here,
we are building a FITS file from scratch, but it could also have been
loaded from a file.

This FITS file has two image extensions, SCI and DQ respectively.

.. runcode::

    from astropy.io import fits

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='SCI'))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='DQ'))

Next we make a tree structure out of the data in the FITS file.
Importantly, we use the *same* arrays in the FITS HDUList and store
them in the tree.  By doing this, asdf will be smart enough to point
to the data in the regular FITS extensions.

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

Now we take both the FITS HDUList and the ASDF tree and create a
`~asdf.fits_embed.AsdfInFits` object.  It behaves identically to the
`~asdf.AsdfFile` object, but reads and writes this special
ASDF-in-FITS format.

.. runcode::

    from asdf import fits_embed

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to('embedded_asdf.fits')

.. runcode:: hidden

    from astropy.io import fits

    with fits.open('embedded_asdf.fits') as new_hdulist:
        with open('content.asdf', 'wb') as fd:
            fd.write(new_hdulist['ASDF'].data.tostring())

The special ASDF extension in the resulting FITS file looks like the
following.  Note that the data source of the arrays uses the ``fits:``
prefix to indicate that the data comes from a FITS extension.

.. asdf:: content.asdf

To load an ASDF-in-FITS file, first open it with ``astropy.io.fits``, and then
pass that HDU list to `~asdf.fits_embed.AsdfInFits`:


.. runcode::

    with fits.open('embedded_asdf.fits') as hdulist:
        with fits_embed.AsdfInFits.open(hdulist) as asdf:
            science = asdf.tree['model']['sci']


.. rubric:: Footnotes

.. [#wiki] https://en.wikipedia.org/wiki/Serialization
