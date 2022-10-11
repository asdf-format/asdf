.. currentmodule:: asdf.config

=============
Configuration
=============

Version 2.8 of this library introduced a new mechanism, `AsdfConfig`, for setting
global configuration options.  Currently available options are limited, but we expect
to eventually move many of the ``AsdfFile.__init__`` and ``AsdfFile.write_to``
keyword arguments to `AsdfConfig`.

AsdfConfig and you
==================

The `AsdfConfig` class provides properties that can be adjusted to change the
behavior of the `asdf` library for all files.  For example, to disable schema validation
on read:

.. code-block:: pycon

    >>> import asdf
    >>> asdf.get_config().validate_on_read = False  # doctest: +SKIP

This will prevent validation on any subsequent call to `~asdf.open`.

Obtaining an AsdfConfig instance
--------------------------------

There are two methods available that give access to an `AsdfConfig` instance:
`~asdf.get_config` and `~asdf.config_context`.  The former simply returns
the currently active config:

.. code-block:: pycon

    >>> import asdf
    >>> asdf.get_config()
    <AsdfConfig
      array_inline_threshold: None
      default_version: 1.5.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: True
    >

The latter method, `~asdf.config_context`, returns a context manager that
yields a copy of the currently active config.  The copy is also returned by
subsequent calls to `~asdf.get_config`, but only until the context manager exits.
This allows for short-lived configuration changes that do not impact other code:

.. code-block:: pycon

    >>> import asdf
    >>> with asdf.config_context() as config:
    ...     config.validate_on_read = False
    ...     asdf.get_config()
    ...
    <AsdfConfig
      array_inline_threshold: None
      default_version: 1.5.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: False
    >
    >>> asdf.get_config()
    <AsdfConfig
      array_inline_threshold: None
      default_version: 1.5.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: True
    >

Special note to library maintainers
-----------------------------------

Libraries that use `asdf` are encouraged to only modify `AsdfConfig` within a
surrounding call to `~asdf.config_context`.  The downstream library will then
be able to customize `asdf`'s behavior without impacting other libraries or
clobbering changes made by the user.

Config options
==============

.. _config_options_array_inline_threshold:

array_inline_threshold
----------------------

The threshold number of array elements under which arrays are automatically stored
inline in the ASDF tree instead of in binary blocks.  If ``None``, array storage
type is not managed automatically.

Defaults to ``None``.

default_version
---------------

The default ASDF Standard version used for new files.  This can be overridden
on an individual file basis (using the version argument to ``AsdfFile.__init__``)
or set here to change the default for all new files created in the current session.

Defaults to the latest stable ASDF Standard version.

io_block_size
-------------

The buffer size used when reading and writing to the filesystem.  Users may wish
to adjust this value to improve I/O performance.  Set to -1 to use the preferred
block size for each file, as reported by st_blksize.

Defaults to -1.

legacy_fill_schema_defaults
---------------------------

Flag that controls filling default values from schemas for older versions of
the ASDF Standard.  This library used to remove nodes from the tree whose
values matched the default property in the schema.  That behavior was changed
in `asdf` 2.8, but in order to read files produced by older versions of the library,
default values must still be filled from the schema for ASDF Standard <= 1.5.0.

Set to False to disable filling default values from the schema for these
older ASDF Standard versions.  The flag has no effect for ASDF Standard >= 1.6.0.

Defaults to True.

validate_on_read
----------------

Flag that controls schema validation of the ASDF tree when opening files.  Users
who trust the source of their files may wish to disable validation on read to
improve performance.

Defaults to True.

Additional AsdfConfig features
==============================

`AsdfConfig` also provides methods for adding and removing plugins at runtime.
For example, the `AsdfConfig.add_resource_mapping` method can be used to register
a schema, which can then be used to validate a file:

.. code-block:: pycon

    >>> import asdf
    >>> content = b"""
    ... %YAML 1.1
    ... ---
    ... $schema: http://stsci.edu/schemas/yaml-schema/draft-01
    ... id: http://example.com/example-project/schemas/foo-1.0.0
    ... type: object
    ... properties:
    ...   foo:
    ...     type: string
    ... required: [foo]
    ... ...
    ... """
    >>> asdf.get_config().add_resource_mapping(
    ...     {"http://example.com/example-project/schemas/foo-1.0.0": content}
    ... )
    >>> af = asdf.AsdfFile(custom_schema="http://example.com/example-project/schemas/foo-1.0.0")
    >>> af.validate()
    Traceback (most recent call last):
    ...
    jsonschema.exceptions.ValidationError: 'foo' is a required property
    ...
    >>> af["foo"] = "bar"
    >>> af.validate()

See the `AsdfConfig` API documentation for more detail.
