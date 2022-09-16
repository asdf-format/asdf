.. currentmodule:: asdf.resource

.. _extending_resources:

===============================
Resources and resource mappings
===============================

In the terminology of this library, a "resource" is a sequence of bytes associated
with a URI.  Currently the two types of resources recognized by `asdf` are schemas
and extension manifests.  Both of these are YAML documents whose associated URI
is expected to match the ``id`` property of the document.

A "resource mapping" is an `asdf` plugin that provides access to
the content for a URI.  These plugins must implement the
`~collections.abc.Mapping` interface (a simple `dict` qualifies) and map
`str` URI keys to `bytes` values.  Resource mappings are installed into
the `asdf` library via one of two routes: the `AsdfConfig.add_resource_mapping <asdf.config.AsdfConfig.add_resource_mapping>`
method or the ``asdf.resource_mappings`` entry point.

Installing resources via AsdfConfig
===================================

The simplest way to isntall a resource into `asdf` is to add it at runtime using the
`AsdfConfig.add_resource_mapping <asdf.config.AsdfConfig.add_resource_mapping>` method.
For example, the following code istalls a schema for use with the `asdf.AsdfFile`
custom_schema argument:

.. code-block:: python

    import asdf

    content = b"""
    %YAML 1.1
    ---
    $schema: http://stsci.edu/schemas/yaml-schema/draft-01
    id: asdf://example.com/example-project/schemas/foo-1.0.0
    type: object
    properties:
      foo:
        type: string
    required: [foo]
    ...
    """

    asdf.get_config().add_resource_mapping(
        {"asdf://example.com/example-project/schemas/foo-1.0.0": content}
    )

The schema will now be available for validating files:

.. code-block:: python

    af = asdf.AsdfFile(custom_schema="asdf://example.com/example-project/schemas/foo-1.0.0")
    af.validate()  # Error, "foo" is missing

The DirectoryResourceMapping class
==================================

But what if we don't want to store our schemas in variables in the code?
Storing resources in a directory tree is a common use case, so `asdf` provides
a `~collections.abc.Mapping` implementation that reads schema content from
a filesystem.  This is the `DirectoryResourceMapping` class.

Consider these three schemas:

.. code-block:: yaml

    # foo-1.0.0.yaml
    id: asdf://example.com/example-project/schemas/foo-1.0.0
    # ...

    # bar-2.3.4.yaml
    id: asdf://example.com/example-project/nested/bar-2.3.4
    # ...

    # baz-8.1.1.yaml
    id: asdf://example.com/example-project/nested/baz-8.1.1
    # ...

which are arranged in the following directory structure::

    schemas
    ├─ foo-1.0.0.yaml
    ├─ README
    └─ nested
        ├─ bar-2.3.4.yaml
        └─ baz-8.1.1.yaml

Our goal is to install all schemas in the directory tree so that they
are available for use with `asdf`.  The `DirectoryResourceMapping` class
can do that for us, but we need to show it how to construct the schema URIs
from the file paths *without reading the id property from the files*.  This
requirement is a performance consideration; not all resources are used
in every session, and if `asdf` were to read and parse all available files
when plugins are loaded, the first call to `asdf.open` would be
intolerably slow.

We should configure `DirectoryResourceMapping` like this:

.. code-block:: python

    import asdf
    from asdf.resource import DirectoryResourceMapping

    mapping = DirectoryResourceMapping(
        "/path/to/schemas",
        "asdf://example.com/example-project/schemas/",
        recursive=True,
        filename_pattern="*.yaml",
        stem_filename=True,
    )

    asdf.get_config().add_resource_mapping(mapping)

The first argument is the path to the schemas directory on the filesystem.  The
second argument is the prefix that should be prepended to file paths
relative to that root when constructing the schema URIs.  The ``recursive``
argument tells the class to descend into the ``nested`` directory when
searching for schemas, ``filename_pattern`` is a glob pattern chosen to exclude
our README file, and ``stem_filename`` causes the class to drop the ``.yaml`` suffix
when constructing URIs.

We can test that our configuration is correct by asking `asdf` to read
and parse one of the schemas:

.. code-block:: python

    from asdf.schema import load_schema

    uri = "asdf://example.com/example-project/schemas/nested/bar-2.3.4.yaml"
    schema = load_schema(uri)
    assert schema["id"] == uri

.. _extending_resources_entry_points:

Installing resources via entry points
=====================================

The `asdf` package also offers an entry point for installing resource
mapping plugins.  This installs a package's resources automatically
without requiring calls to the AsdfConfig method.  The entry point is
called ``asdf.resource_mappings`` and expects to receive
a method that returns a list of `~collections.abc.Mapping` instances.

For example, let's say we're creating a package named ``asdf-foo-schemas``
that provides the same schemas described in the previous section.  Our
directory structure might look something like this::

    asdf-foo-schemas
    ├─ pyproject.toml
    └─ src
       └─ asdf_foo_schemas
          ├─ __init__.py
          ├─ integration.py
          └─ schemas
             ├─ __init__.py
             ├─ foo-1.0.0.yaml
             ├─ README
             └─ nested
                ├─ __init__.py
                ├─ bar-2.3.4.yaml
                └─ baz-8.1.1.yaml

``pyproject.toml`` is the preferred central configuration file for Python build and development systems.
However, it is also possible to write configuration to a ``setup.cfg`` file (used by
`setuptools <https://setuptools.pypa.io/en/latest/index.html>`_) placed in the root
directory of the project. This documentation will cover both options.

In ``integration.py``, we'll define the entry point method
and have it return a list with a single element, our `DirectoryResourceMapping`
instance:

.. code-block:: python

    # integration.py
    from pathlib import Path

    from asdf.resource import DirectoryResourceMapping


    def get_resource_mappings():
        # Get path to schemas directory relative to this file
        schemas_path = Path(__file__).parent / "schemas"
        mapping = DirectoryResourceMapping(
            schemas_path,
            "asdf://example.com/example-project/schemas/",
            recursive=True,
            filename_pattern="*.yaml",
            stem_filename=True,
        )
        return [mapping]

Then in ``pyproject.toml``, define an ``[project.entry-points]`` section (or ``[options.entry_points]`` in ``setup.cfg``)
that identifies the method as an ``asdf.resource_mappings`` entry point:

.. tab:: pyproject.toml

    .. code-block:: toml

        [project.entry-points]
        'asdf.resource_mappings' = { asdf_foo_schemas = 'asdf_foo_schemas.integration:get_resource_mappings' }

.. tab:: setup.cfg

    .. code-block:: ini

        [options.entry-points]
        asdf.resource_mappings =
            asdf_foo_schemas = asdf_foo_schemas.integration:get_resource_mappings

After installing the package, it should be possible to load one of our schemas
in a new session without any additional setup:

.. code-block:: python

    from asdf.schema import load_schema

    uri = "asdf://example.com/example-project/schemas/nested/bar-2.3.4.yaml"
    schema = load_schema(uri)
    assert schema["id"] == uri

Note that the package will need to be configured to include the
YAML files.  There are multiple ways to accomplish this, but one easy option
is to add ``[tool.setuptools.package-data]`` and ``[tool.setuptools.package-dir]`` sections to ``pyproject.toml``
(or ``[options.package_data]`` in ``setup.cfg``) requesting that all files with a ``.yaml`` extension be installed:

.. tab:: pyproject.toml

    .. code-block:: toml

        [tool.setuptools]
        packages = ["asdf_foo_schemas", "asdf_foo_schemas.resources"]

        [tool.setuptools.package-data]
        "asdf_foo_schemas.resources" = ["resources/**/*.yaml"]

        [tool.setuptools.package-dir]
        "" = "src"
        "asdf_foo_schemas.resources" = "resources"

.. tab:: setup.cfg

    .. code-block:: ini

        [options.package_data]
        * = *.yaml

Entry point performance considerations
--------------------------------------

For the good of `asdf` users everywhere, it's important that entry point
methods load as quickly as possible.  All resource URIs must be loaded
before reading an ASDF file, so any entry point method that lingers
will introduce a delay to the initial call to `asdf.open`.  For that reason,
we recommend to minimize the number of imports that occur in the module
containing the entry point method, particularly imports of modules outside
of the Python standard library or `asdf` itself.  When resources are stored
in a filesystem, it's also helpful to delay reading a file until its URI
is actually requested, which may not occur in a given session.  The
DirectoryResourceMapping class is implemented with this behavior.
