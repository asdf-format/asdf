.. currentmodule:: asdf

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

.. _custom_type_versions:

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

.. _extension_checking:

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
