.. currentmodule:: asdf.extension

.. _extending_extensions:

==========
Extensions
==========

An ASDF "extension" is a supplement to the core ASDF specification that
describes additional YAML tags or binary block compressors which
may be used when writing files.  In this library, extensions implement the
`Extension` interface and can be installed manually
by the user or automatically by a package using Python's entry points
mechanism.

Extension features
==================

Basics
------

Every extension to ASDF must be uniquely identified by a URI; this URI is
written to the file's metadata when the extension is used and allows
software to determine if the necessary extensions are installed when the file
is read.  An ASDF extension implementation intended for use with this library
must, at a minimum, implement the `Extension` interface and
provide its URI as a property:

.. code-block:: python

    from asdf.extension import Extension

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"

Note that this is an "empty" extension that does not extend the library in
any meaningful way; other attributes must be implemented to actually
support additional tags and/or compressors.  Read on for a description of the rest
of the Extension interface.

Additional tags
---------------

In order to implement support for additional YAML tags, an Extension subclass
must provide both a list of relevant tags and a list of `Converter`
instances that translate objects with those tags to and from YAML.  These lists
are provided in the ``tags`` and ``converters`` properties, respectively:

.. code-block:: python

    from asdf.extension import Extension, Converter

    class FooConverter(Converter):
        # ...

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        tags = ["asdf://example.com/example-project/tags/foo-1.0.0"]
        converters = [FooConverter()]

The implementation of a Converter is a topic unto itself and is discussed in
detail in :ref:`extending_converters`.

The Extension implemented above will happily convert between ``foo-1.0.0``
tagged YAML objects and the appropriate Python representation, but it will
not perform any schema validation.  In order to associate the tag with
a schema, we'll need to provide a `TagDefinition` object
instead of just a string:

.. code-block:: python

    from asdf.extension import Extension, Converter, TagDefinition

    class FooConverter(Converter):
        # ...

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        tags = [
            TagDefinition(
                "asdf://example.com/example-project/tags/foo-1.0.0",
                schema_uri="asdf://example.com/example-project/schemas/foo-1.0.0",
            )
        ]
        converters = [FooConverter()]

.. _extending_extensions_compressors:

Additional block compressors
----------------------------

Binary block compressors implement the `Compressor` interface
and are included in an extension via the ``compressors`` property:

.. code-block:: python

    from asdf.extension import Extension, Compressor

    class FooCompressor(Compressor):
        # ...

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        compressors = [FooCompressor()]

See :ref:`extending_compressors` for details on implementing the Compressor interface.

Additional YAML tag handles
---------------------------

The YAML format permits use of "tag handles" as shorthand prefixes
in tags.  For example, these two YAML files are equivalent:

.. code-block:: yaml

    %YAML 1.1
    ---
    value: !<asdf://example.com/example-project/tags/foo-1.0.0>
      # etc
    ...

.. code-block:: yaml

    %YAML 1.1
    %TAG !example! asdf://example.com/example-project/tags/
    ---
    value: !example!foo-1.0.0
      # etc
    ...

In both cases the ``value`` object has tag asdf://example.com/example-project/tags/foo-1.0.0,
but in the second example the tag is abbreviated as ``!example!foo-1.0.0`` through use of
a handle.  This has no impact on the interpretation of the file but can make the raw ASDF
tree easier to read for humans.

Tag handles can be defined in the ``yaml_tag_handles`` property of an extension:

.. code-block:: python

    from asdf.extension import Extension

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        yaml_tag_handles = {
            "!example!": "asdf://example.com/example-project/tags/"
        }

ASDF Standard version requirement
---------------------------------

Some extensions may only work with specific version(s) of the ASDF
Standard -- for example, the schema associated with one of an extension's
tags may reference specific versions of ASDF core tags.  This requirement
can be expressed as a PEP 440 version specifier in an Extension's
``asdf_standard_requirement`` property:

.. code-block:: python

    from asdf.extension import Extension

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        asdf_standard_requirement = ">= 1.2.0, < 1.5.0"

Now the extension will only be used with ASDF Standard 1.3.0 and 1.4.0 files.

Legacy class names
------------------

Previous versions of this library referred to extensions by their Python class
names instead of by URI.  These class names were written to ASDF file metadata
and allowed the library to warn users when an extension used to write the file
was not available on read.  Now the extension URI is written to the metadata, but
to prevent warnings when reading older files, extension authors can provide
an additional list of class names that previously identified the extension:

.. code-block:: python

    from asdf.extension import Extension

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"
        legacy_class_names = [
            "foo_package.extensions.FooExtension",
        ]

.. _exposing_extension_object_internals:

Making converted object's contents visible to `info` and `search`
-----------------------------------------------------------------

If the object produced by the extension supports a class method
`.__asdf_traverse__` then it can be used by those tools to expose the contents
of the object. That method should accept no arguments and return either a
dict of attributes and their values, or a list if the object itself is
list-like.

.. _extending_extensions_installing:

Installing an extension
=======================

Once an extension is implemented, it must be installed so that the `asdf`
library knows to use it.  There are two options for installing an extension:
manually per session using `~asdf.config.AsdfConfig`, or automatically
for every session using the ``asdf.extensions`` entry point

.. _extending_extensions_installing_asdf_config:

Installing extensions via AsdfConfig
------------------------------------

The simplest way to install an extension is to add it at runtime using the
`AsdfConfig.add_extension <asdf.config.AsdfConfig.add_extension>` method.
For example, the following code defines and installs a minimal extension:

.. code-block:: python

    import asdf
    from asdf.extension import Extension

    class FooExtension(Extension):
        extension_uri = "asdf://example.com/example-project/extensions/foo-1.0.0"

    asdf.get_config().add_extension(FooExtension())

Now the extension will be available when working with ASDF files, but only
for the duration of the current Python session.

.. _extending_extensions_installing_entry_points:

Installing extensions via entry points
--------------------------------------

The `asdf` package also offers an entry point for installing extensions
This registers a package's extensions automatically on package install
without requiring calls to the AsdfConfig method.  The entry point is
called ``asdf.extensions`` and expects to receive a method that returns
a list of ``Extension`` instances.

For example, let's say we're creating a package named ``asdf-foo-extension``
that provides the not-particularly-useful ``FooExtension`` from the previous
section.  We'll need to define an entry point method that returns a list
containing an instance of ``FooExtension``:

.. code-block:: python

    def get_extensions():
        return [FooExtension()]

We'll assume that method is located in the module ``asdf_foo_extension.integration``.

Next, in the package's ``pyproject.toml``, define a ``[project.entry-points]`` section (or ``[options.entry_points]`` in
``setup.cfg``) that identifies the method as an ``asdf.extensions`` entry point:

.. tab:: pyproject.toml

    .. code-block:: toml

        [project.entry-points]
        'asdf.extensions' = { asdf_foo_extension = 'asdf_foo_extension.integration:get_extensions' }

.. tab:: setup.cfg

    .. code-block:: ini

        [options.entry_points]
        asdf.extensions =
            asdf_foo_extension = asdf_foo_extension.integration:get_extensions

After installing the package, the extension should be automatically available in any
new Python session.

Entry point performance considerations
--------------------------------------

For the good of `asdf` users everywhere, it's important that entry point
methods load as quickly as possible.  All extensions must be loaded before
reading an ASDF file, so any entry point method that lingers will introduce a delay
to the initial call to `asdf.open`.  For that reason, we recommend that extension
authors minimize the number of imports that occur in the module containing
the entry point method, particularly imports of modules outside of the
Python standard library or `asdf` itself.

.. _extending_extensions_manifest:

Populating an extension from a manifest
=======================================

An "extension manifest" is a language-independent description of an ASDF extension (little 'e')
that includes information such as the extension URI, list of tags, ASDF Standard
requirement, etc.  Instructions on writing a manifest can be found in
:ref:`extending_manifests`, but once written, we'll still need a Python Extension (big 'E')
whose content mirrors the manifest. Rather than duplicate that information in Python code,
we recommend use of the `ManifestExtension` class, which reads a manifest
and maps its content to the appropriate Extension interface properties.

Assuming the manifest is installed as a resource (see :ref:`extending_resources`), an extension
instance can be created using the ``from_uri`` factory method:

.. code-block:: python

    from asdf.extension import ManifestExtension

    extension = ManifestExtension.from_uri("asdf://example.com/example-project/manifests/foo-1.0.0")

Compressors and converters can be included in the extension by adding them as keyword arguments:

.. code-block:: python

    from asdf.extension import ManifestExtension

    extension = ManifestExtension.from_uri(
        "asdf://example.com/example-project/manifests/foo-1.0.0",
        converters=[FooConverter()],
        compressors=[FooCompressor()],
    )

The extension may then be installed by one of the two methods described above.

Warning on ManifestExtension and entry points
---------------------------------------------

When implementing a package that automatically installs a ManifestExtension, we'll need to
utilize both the ``asdf.resource_mappings`` entry point (to install the manifest) and
the ``asdf.extensions`` entry point (to install the extension).  Because the manifest must be
installed before the extension can be instantiated, it's easy to end up trapped in an import
loop.  For example, this seemingly innocuous set of entry point methods cannot be successfully
loaded:

.. code-block:: python

    from asdf.extension import ManifestExtension

    RESOURCES = {
        "asdf://example.com/example-project/manifests/foo-1.0.0": open("foo-1.0.0.yaml").read()
    }

    def get_resource_mappings():
        return [RESOURCES]

    EXTENSION = ManifestExtension.from_uri("asdf://example.com/example-project/manifests/foo-1.0.0")

    def get_extensions():
        return [EXTENSION]

When the module is imported, ``ManifestExtension.from_uri`` asks the `asdf` library to load
all available resources so that it can retrieve the manifest content.  But loading the resources
requires importing this module to get at the ``get_resource_mappings`` method, so now we're stuck!

The solution is to instantiate the ManifestExtension inside of its entry point method:

.. code-block:: python

    def get_extensions():
        return [
            ManifestExtension.from_uri("asdf://example.com/example-project/manifests/foo-1.0.0")
        ]

This is not as inefficient as it might seem, since the `asdf` library only calls the method once
and reuses a cached result thereafter.
