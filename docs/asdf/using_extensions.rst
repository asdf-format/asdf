.. currentmodule:: asdf

****************
Using Extensions
****************


The built-in extension
======================

The ability to serialize the following types is provided by `asdf`'s built-in
extension:

* `dict`
* `list`
* `str`
* `int`
* `float`
* `complex`
* `numpy.ndarray`

The built-in extension is packaged with `asdf` and is automatically used when
reading and writing files. Users can not control the use of the built-in
extension and in general they need not concern themselves with the details of
its implementation. However, it is useful to be aware that the built-in
extension is always in effect when reading and writing ASDF files.

Custom types
============

For the purposes of this documentation, a "custom type" is any data type that
can not be serialized by the built-in extension.

In order for a particular custom type to be serialized, a special class called
a "converter" must be implemented. Each converter defines how the corresponding
custom type will be serialized and deserialized. More details on how converters
are implemented can be found in :ref:`extending_converters`. Users should never
have to refer to converter implementations directly; they simply enable `asdf` to
recognize and process custom types.

In addition to converters, each custom type may have a corresponding schema,
which is used for validation. The definition of the schema if present is closely
tied to the definition of the converter. More details on schema validation can
be found in :ref:`schema_validation`.

Schemas are generally versioned and change in sync with their associated converters.
The version number will increase whenever a schema (and therefore the converter
implementation) changes.

Extensions
==========

In order for the converters and schemas to be used by `asdf`, they must be
packaged into an **extension** class. In general, the details of extensions are
irrelevant to users of `asdf`. However, users need to be aware of extensions in
the following two scenarios:

* when storing custom data types to files to be written
* when reading files that contain custom data types

These scenarios require the use of custom extensions (the built-in extension is
always used). There are two ways to use custom extensions, which are detailed
below in :ref:`other_packages` and :ref:`explicit_extensions`.

Writing custom types to files
-----------------------------

`asdf` is not capable of serializing any custom type unless an extension is
provided that defines how to serialize that type. Attempting to do so will
cause an error when trying to write the file. For details on developing support
for custom types and extensions, see :ref:`extending_extensions`.

.. _reading_custom_types:

Reading files with custom types
-------------------------------

The `asdf` software is capable of reading files that contain custom data types
even if the extension that was used to create the file is not present. However,
the extension is required in order to properly deserialize the original type.

If the necessary extension is **not** present, the custom data types will
simply appear in the tree as a nested combination of basic data types. The
structure of this data will mirror the structure of the YAML objects in the
ASDF file.

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
========================================

Tags and schemas that follow best practices are versioned. This allows changes
to tags and schemas to be recorded, and it allows `asdf` to define behavior with
respect to version compatibility.

Tag and schema versions may change for several reasons. One common reason is to
reflect a change to the API of the custom type that a tag represents. This
typically corresponds to an update to the version of the software that defines
that custom type.

Since ASDF is designed to be an archival file format, extension authors are
encouraged to maintain backwards compatibility with all older tag versions.

Reading files
-------------

When `asdf` encounters a tagged object in a file, it will compare the URI of
the tag in the file with the list of tags handled by available converters.
The first matching converter will be selected to deserialize the object.  If
no such converters exist, the library will emit a warning and the object will
be presented to the user in its primitive form.

If multiple converters are present that both handle the same tag, the first
found by the library will be used.  Users may disable a converter by removing
its extension with the `~asdf.config.AsdfConfig.remove_extension` method.

Writing files
-------------

When writing a object to a file, `asdf` compares the object's type to the list
of types handled by available converters.  The first matching converter will
be selected to serialize the object.  If no such converters exist, the library
will raise an error.

If multiple converters are present that both handle the same type, the first
found by the library will be used.  Users may disable a converter by removing
its extension with the `~asdf.config.AsdfConfig.remove_extension` method.

.. _other_packages:

Extensions from other packages
==============================

Some external packages may define extensions that allow `asdf` to recognize some
or all of the types that are defined by that package. Such packages may install
the extension class as part of the package itself (details for developers can
be found in :ref:`extending_extensions_installing_entry_points`).

If the package installs its extension, then `asdf` will automatically detect the
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
==========================

Sometimes no packaged extensions are provided for the types you wish to
serialize. In this case, it is necessary to explicitly install any necessary
extension classes when reading and writing files that contain custom types.

The config object returned from `asdf.get_config` offers an `~asdf.config.AsdfConfig.add_extension`
method that can be used to install an extension for the remainder of the current
Python session.

Consider the following example where there exists a custom type
``MyCustomType`` that needs to be written to a file. An extension is defined
``MyCustomExtension`` that contains a converter that can serialize and
deserialize ``MyCustomType``. Since ``MyCustomExtension`` is not installed by
any package, we will need to manually install it:

.. code-block:: python

    import asdf

    ...

    asdf.get_config().add_extension(MyCustomExtension())
    af = asdf.AsdfFile()
    af.tree = {"thing": MyCustomType("foo")}
    # This call would cause an error if the proper extension was not
    # provided to the constructor
    af.write_to("custom.asdf")

Note that the extension class must actually be instantiated when it is passed
to `~asdf.config.AsdfConfig.add_extension`.

To read the file (in a new session) we again need to install the extension first:

.. code-block:: python

    import asdf

    asdf.get_config().add_extension(MyCustomExtension())
    af = asdf.open("custom.asdf")

.. _extension_checking:

Extension checking
==================

When writing ASDF files using this software, metadata about the extensions that
were used to create the file will be added to the file itself.  This includes
the extension's URI, which uniquely identifies a particular version of the
extension.

When reading files with extension metadata, `asdf` can check whether the required
extensions are present before processing the file. If a required extension is
not present, `asdf` will issue a warning.

It is possible to turn these warnings into errors by using the
``strict_extension_check`` parameter of `asdf.open`. If this parameter is set to
`True`, then opening the file will fail if any of the required extensions are missing.
