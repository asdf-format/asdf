.. currentmodule:: asdf.config

=============
Configuration
=============

Version 2.8 of this library introduced a new mechanism, `AsdfConfig`, for setting
global configuration options.  Currently available options are limited, but we expect
to eventually move many of the `asdf.AsdfFile` and `asdf.AsdfFile.write_to`
keyword arguments to `AsdfConfig`.

Using AsdfConfig
================

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
      all_array_storage: None
      all_array_compression: input
      all_array_compression_kwargs: None
      default_array_save_base: True
      convert_unknown_ndarray_subclasses: False
      default_version: 1.6.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: True
      lazy_tree: False
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
      all_array_storage: None
      all_array_compression: input
      all_array_compression_kwargs: None
      default_array_save_base: True
      convert_unknown_ndarray_subclasses: False
      default_version: 1.6.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: False
      lazy_tree: False
    >
    >>> asdf.get_config()
    <AsdfConfig
      array_inline_threshold: None
      all_array_storage: None
      all_array_compression: input
      all_array_compression_kwargs: None
      default_array_save_base: True
      convert_unknown_ndarray_subclasses: False
      default_version: 1.6.0
      io_block_size: -1
      legacy_fill_schema_defaults: True
      validate_on_read: True
      lazy_tree: False
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

all_array_storage
-----------------

Use this storage type for all arrays within an ASDF file. Must be one of

- ``"internal"``
- ``"external"``
- ``"inline"``
- ``None``

If ``None`` a different storage type can be used for each array.
See `asdf.AsdfFile.set_array_storage` for more details.

Defaults to ``None``.

all_array_compression
---------------------

Use this compression type for all arrays within an ASDF file.
If ``"input"`` a different compression type can be used for each
array. See `asdf.AsdfFile.set_array_compression` for more details.

Defaults to ``"input"``.

all_array_compression_kwargs
----------------------------

Use these additional compression keyword arguments for all arrays
within an ASDF file. If ``None`` diffeerent keyword arguments
can be set for each array. See `asdf.AsdfFile.set_array_compression` for more details.

Defaults to ``None``.

.. _default_array_save_base:

default_array_save_base
-----------------------

If ``True`` (the default) when an array is saved, the bytes for the
"base" array that owns the memory will be stored as an ASDF block
(see `asdf.util.get_array_base`). This means that saving a small
"view" of a large array will result in the entire large array being
saved to the file.

If ``False`` bytes for different arrays (even if they are views of the
same memory) will be stored in different ASDF blocks.

.. _convert_unknown_ndarray_subclasses:

convert_unknown_ndarray_subclasses
----------------------------------

Convert otherwise unhandled instances of subclasses of ndarray into
ndarrays prior to serialization.

Previous extension code allowed AsdfTypes to convert instances of subclasses
of supported types. Internally, the handling of ndarrays has been moved
from an AsdfType to a Converter which does not support converting
instances of subclasses unless they are explicitly listed. This means
that code that previously relied on asdf converting instances of subclasses
of ndarray into an ndarray will need to be updated to define a Converter
for the ndarray subclass or to request that support be added directly
in asdf (for subclasses in existing asdf dependencies).

With this setting enabled, asdf will continue to convert instances
of subclasses of ndarray but will issue a warning when an instance is
converted. This currently defaults to ``False`` and issues
a deprecation warning if enabled. In a future version of asdf
this setting will be removed.

Defaults to ``False``.

default_version
---------------

The default ASDF Standard version used for new files.  This can be overridden
on an individual file basis (using the version argument to `asdf.AsdfFile`)
or set here to change the default for all new files created in the current session.

Defaults to the latest stable ASDF Standard version.

io_block_size
-------------

The buffer size used when reading and writing to the filesystem.  Users may wish
to adjust this value to improve I/O performance.  Set to -1 to use the system
provided default block size for each file.

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
    asdf._jsonschema.exceptions.ValidationError: 'foo' is a required property
    ...
    >>> af["foo"] = "bar"
    >>> af.validate()

See the `AsdfConfig` API documentation for more detail.
