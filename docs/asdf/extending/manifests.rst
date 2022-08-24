.. _extending_manifests:

===================
Extension manifests
===================

An extension "manifest" is a YAML document that defines an extension
in a language-independent way.  Use of a manifest is recommended for
ASDF extensions that are intended to be implemented by ASDF libraries
in multiple languages, so that other implementers do not need to go
spelunking through Python code to discover the tags and schemas that
are included in the extension.  This library provides support for
automatically populating a `~asdf.extension.Extension` object from
a manifest; see :ref:`extending_extensions_manifest` for more information.

Anatomy of a manifest
=====================

Here is an example of a simple manifest that describes an extension
with one tag and schema:

.. code-block:: yaml
    :linenos:

    %YAML 1.1
    ---
    id: asdf://example.com/example-project/manifests/example-1.0.0
    extension_uri: asdf://example.com/example-project/extensions/example-1.0.0
    title: Example extension 1.0.0
    description: Tags for example objects.
    asdf_standard_requirement:
        gte: 1.3.0
        lt: 1.5.0
    tags:
      - tag_uri: asdf://example.com/example-project/tags/foo-1.0.0
        schema_uri: asdf://example.com/example-project/schemas/foo-1.0.0
    ...

.. code-block:: yaml
    :lineno-start: 3

    id: asdf://example.com/example-project/manifests/example-1.0.0

The ``id`` property contains the URI that uniquely identifies our manifest.  This
URI is how we'll refer to the manifest document's content when using the `asdf`
library.

.. code-block:: yaml
    :lineno-start: 4

    extension_uri: asdf://example.com/example-project/extensions/example-1.0.0

The ``extension_uri`` property contains the URI of the extension that the manifest
describes.  This is the URI written to ASDF file metadata to document that an
extension was used when writing the file.

.. code-block:: yaml
    :lineno-start: 5

    title: Example extension 1.0.0
    description: Tags for example objects.

``title`` and ``description`` are optional documentation properties.

.. code-block:: yaml
    :lineno-start: 7

    asdf_standard_requirement:
        gte: 1.3.0
        lt: 1.5.0

The optional ``asdf_standard_requirement`` property describes the
ASDF Standard versions that are compatible with this extension.  The
``gte`` and ``lt`` properties are used here to restrict ASDF Standard
versions to greater-than-or-equal 1.3.0 and less-than 1.5.0, respectively.
``gt`` and ``lte`` properties are also available.

.. code-block:: yaml
    :lineno-start: 10

    tags:
      - tag_uri: asdf://example.com/example-project/tags/foo-1.0.0
        schema_uri: asdf://example.com/example-project/schemas/foo-1.0.0

The ``tags`` property contains a list of objects, each representing a new
tag that the extension brings to ASDF.  The ``tag_uri`` property contains
the tag itself, while the (optional, but recommended) ``schema_uri``
property contains the URI of a schema that can be used to validate objects
with that tag.  Tag objects may also include ``title`` and ``description``
documentation properties.

Validating a manifest
=====================

This library includes a schema, ``asdf://asdf-format.org/core/schemas/extension_manifest-1.0.0``,
that can be used to validate a manifest document:

.. code-block:: python

    import asdf
    import yaml

    schema = asdf.schema.load_schema(
        "asdf://asdf-format.org/core/schemas/extension_manifest-1.0.0"
    )
    manifest = yaml.safe_load(open("path/to/manifests/example-1.0.0.yaml").read())
    asdf.schema.validate(manifest, schema=schema)
