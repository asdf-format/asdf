# What's New

## 6.0.0

Asdf 6.0.0 removes some deprecated API and changes a few default settings.

### Removed API

- Reading non-seekable files is no longer supported. Users should implement a buffer to allow seeking during read.
- Reading file objects that aren't instances of  [`io.IOBase`][] are no longer supported. Users should wrap non-`io.IOBase` objects in a supported class.

### New Defaults

- [`AsdfConfig.validate_on_read`][asdf.config.AsdfConfig.validate_on_read] now defaults to `False`. This means that opening an ASDF file will no longer automatically trigger validation against schemas that match tags within the file. Users are encouraged to either call [`AsdfFile.validate`][asdf.AsdfFile.validate] on the opened `AsdfFile` instance or re-enable `AsdfConfig.validate_on_read`.
- [`AsdfConfig.warn_on_failed_conversion`][asdf.config.AsdfConfig.warn_on_failed_conversion] now defaults to `True`. Files that are not fully supported by the user environment (especially those that contain nested unknown tags) can often lead to errors during [`asdf.open`][]. With this new default these errors are converted to warnings and users can still access the raw, unconverted file contents.
- [`AsdfConfig.default_array_save_base`][asdf.config.AsdfConfig.default_array_save_base] now defaults to `False`. With this new default, adding a view of a larger numpy array will trigger asdf to save the contents of the view in an ASDF block (instead of the contents of the larger array). Users who wish to save views of other arrays can either re-enable this option or use [`AsdfFile.set_array_save_base`][asdf.AsdfFile.set_array_save_base] for each view.


## 5.0.0

Asdf 5.0.0 removes some deprecated API.

### Removed API

- The `refresh_extension_manager` argument is no longer supported for [`AsdfFile.schema_info`][asdf.AsdfFile.schema_info] and [`AsdfFile.info`][asdf.AsdfFile.info]. There should be no need for forced refreshing.
- The `url_mapping` argument to `asdf.schema.get_validator` was removed. This was a leftover from the legacy extension API and is no longer needed.
- The `resolver` argument to [`asdf.schema.load_schema`][asdf.schema.load_schema] was removed. This was a leftover from the legacy extension API and is no longer needed.
- `AsdfConfig.convert_unknown_ndarray_subclasses` is removed. Please implement a [`asdf.extension.Converter`][] for any subclasses.
- Opening of "http://" and "https://" uris now requires fsspec to be installed.
- The bundled `pytest_asdf` plugin was removed. Please install `pytest-asdf-plugin` for a replacement.

## 4.0.0

Hi! Asdf 4.0.0 is a new major version including:

- [removal of deprecated API][whats-new-4.0.0-removed]
- [changes to a few key defaults][whats-new-4.0.0-defaults]

[](){ #whats-new-4.0.0-removed }
### Removed API

- The `copy_arrays` argument for `asdf.open` and `AsdfFile` has been removed and replaced by `memmap` (`memmap == not copy_arrays`).
- `ignore_version_mismatch` has had no effect since asdf 3.0.0 and was removed.
- the [`asdf.util`][] submodule had several unused functions removed:
  - `filepath_to_url`, see `pathlib.Path.as_uri` as an alternative
  - `is_primitive`, use `isinstance`
  - `iter_subclasses`, use `object.__subclasses__`
  - `minversion`, see `astropy.utils.minversion`
  - `resolve_name`, see `astropy.utils.resolve_name`
  - `human_list`, use `pprint` or your own string formatting
- `versioning.AsdfSpec`, see [`asdf.versioning.AsdfVersion`][] comparisons
- `asdf.testing.helpers.format_tag`, use your own string formatting
- `AsdfFile.version_map`, could have been removed with the legacy extension API
- `AsdfFile.resolve_and_inline`, use [`AsdfFile.resolve_references`][asdf.AsdfFile.resolve_references] and `all_array_storage=="inline"`
- `asdf.asdf`, the public items in this submodule are all in the top level [`asdf`][] module
- `asdf.asdf.SerializationContext`, available at [`asdf.extension.SerializationContext`][]
- `asdf.stream`, see [`asdf.tags.core.Stream`][]
- `ignore_implicit_conversion` has been removed (see `whats_new_4.0.0_implicit_conversion` below)
- providing a tag uri within a schema `$ref` will no longer resolve to the schema uri associated with that tag

[](){ #whats-new-4.0.0-defaults }
### New Defaults

#### Memory mapping disabled by default

Calls to `asdf.open()` and `AsdfFile()` will now default to `memmap=False`, disabling memory mapping of arrays by default.

#### ASDF standard version

By default asdf 4.0.0 will write files that use the 1.6.0 version of the ASDF standard. This change should be transparent and all files that use the older standards are readable. If you wish to write files using the 1.5.0 (or older) ASDF standard you can provide a version to [`AsdfFile.write_to`][asdf.AsdfFile.write_to] or change [`asdf.config.AsdfConfig.default_version`][asdf.config.AsdfConfig.default_version].

In addition to new schemas and tags ASDF standard 1.6.0 comes with a few other changes (scheduled for this version).

- Opening files will no longer trigger [`AsdfFile.fill_defaults`][asdf.AsdfFile.fill_defaults].
- Mapping keys are restricted to str, int, bool See *[YAML Subset][yaml_subset]*.

[](){ #whats-new-4.0.0-validation }
#### Validation

Several operations no longer automatically trigger tree validation. These changes were made to limit the number of times a tree is validated to allow incremental construction of trees and to improve performance.

- providing a tree to `AsdfFile.__init__` no longer triggers validation
- calling [`AsdfFile.resolve_references`][asdf.AsdfFile.resolve_references] no longer triggers validation
- assigning a new tree to [`AsdfFile.tree`][asdf.AsdfFile.tree] no longer triggers validation

!!! note
	Validation can be triggered with [`AsdfFile.validate`][asdf.AsdfFile.validate] and will occur when writing to a file (or reading if `AsdfConfig.validate_on_read` is enabled).

#### Find References

Similar to [Validation][whats-new-4.0.0-validation] several operations no longer automatically trigger [`AsdfFile.find_references`][asdf.AsdfFile.find_references]:

- [`asdf.open`][] does not trigger [`AsdfFile.find_references`][asdf.AsdfFile.find_references]
- providing a tree (or [`AsdfFile`][asdf.AsdfFile]) to `AsdfFile.__init__` no longer triggers [`AsdfFile.find_references`][asdf.AsdfFile.find_references]

!!! note
	[`AsdfFile.find_references`][asdf.AsdfFile.find_references] is only for JSON pointer references which are most useful for external references. YAML anchors and aliases are automatically resolved.

#### Implicit Conversion

In older asdf versions `namedtuple` instances were automatically converted to lists when written to a file. When read back in the `namedtuple` was not reconstructed and instead these objects were returned as lists. With asdf 4.0.0 this "implicit conversion" is no longer performed which allows extensions to implement converters for `namedtuple` instances.

#### Unknown NDArray Subclasses

In asdf 3.0.0 a config attribute was added `AsdfConfig.convert_unknown_ndarray_subclasses` that was enabled by default (to retain the behavior of the removed legacy extension that handled ndarrays).

In asdf 4.0.0 this setting is disabled by default and issues a deprecation warning when enabled. In an upcoming version of asdf this setting will be removed.

See `convert_unknown_ndarray_subclasses` for more details.

## 3.0.0

Asdf 3.0.0 is the first major asdf release since 2018.

Thank you to all the [contributors](https://github.com/asdf-format/asdf/graphs/contributors)!

### Removed features

The following deprecated features are removed in asdf 3.0.0:

- [AsdfInFits][asdf-in-fits-deprecation]
- [Legacy Extensions][legacy-extension-deprecation]

Please see the links above or *[Deprecations](deprecations.md)* for more details.

### New features

As asdf now only supports new-style [extensions](extending/extensions.md) several new features were added to allow these extensions to retain all the functionality of the now removed type system.

Converters can now [defer][extending-converters-deferral] conversion allowing a different converter to handle serailizing an object. This is useful if a subclass instance can be safely converted to a superclass during serialization. See *[Deferring to another converter][extending-converters-deferral]* for an example and more information.

Converters can now access [ASDF block storage][extending-converters-block-storage] during serialization and deserialization. See *[Block storage][extending-converters-block-storage]* for examples and more information.

Converters have always been "strict" about tag version mismatches (returning 'raw' objects if a specific tag version is not supported). This "strictness" now extends to all objects handled by asdf. As all known asdf extensions have already migrated to converters this should pose no issue for users. Please [open an issue](https://github.com/asdf-format/asdf/issues) if you run into any difficulty.

### Internal changes

2.15.1 included internally a version of jsonschema. See the [jsonschema][whats-new-2.15.1-jsonschema] sub-section of the [2.15.1][whats-new-2.15.1] section for more details. Asdf 3.0.0 drops jsonschema as a dependency. If your software requires jsonschema be sure to add it to your dependencies.

To accomplish the above improvements to asdf extensions, a major rewrite of the ASDF block management code was required. During this rewrite `AsdfBlockIndexWarning` was added which users will see if they open an ASDF file with an invalid block index. Re-saving the file (or removing the optional block index) is often sufficient to fix the file so it no longer issues the warning when opened.

### Upcoming changes

With the release of asdf 3.0.0 the developers are beginning work on 3.1.0 and 4.0.0. One major change being considered for asdf 4.0.0 is the disabling of memory mapping as the default option when as ASDF file is opened. Memory mapping can offer significant performance gains but also increases the chance for gnarly errors like segfaults and corrupt data. Please let us know if this change would impact your use of asdf in the newly opened [asdf discussions](https://github.com/asdf-format/asdf/discussions)

In an attempt to construct a coherent api, asdf 3.1 (and additional minor versions) will likely contain new deprecations in an effort to reorganize and clean up the api. If you are using features that are not currently listed in the User API or Developer API documentation please open an issue. This will help us to know what functions should be preserved, what requires a deprecation prior to removal and which of our un-documented (non-public) features can be removed without a deprecation.

[](){ #whats-new-2.15.1 }
## 2.15.1

[](){ #whats-new-2.15.1-jsonschema }
### jsonschema

Asdf 2.15.1 includes internally a version of jsonschema 4.17.3. This inclusion was done to deal with incompatible changes in jsonschema 4.18.

Many libraries that use asdf import jsonschema to allow catching of `ValidationError` instances that might be raised during schema validation. Prior to asdf 2.15 this error type was not part of the public asdf API. For 2.15 and later users are expected to import `ValidationError` from [`asdf.exceptions`][] (instead of jsonschema directly).

To further ease the transition, asdf will, when possible, use exceptions imported from any installed version of jsonschema. This means that when the asdf internal jsonschema raises a `ValidationError` on a system where jsonschema was separately installed, the internal jsonschema will attempt to use `ValidationError` from the installed version. This should allow code that catches exceptions imported from jsonschema to continue to work with no changes. However, asdf cannot guarantee compatibility with future installed jsonschema versions and users are encouraged to update their code to import `ValidationError` from [`asdf.exceptions`][].

Finally, asdf is temporarily keeping jsonschema as a dependency as many libraries expected this to be installed by asdf. We expect to drop this requirement soon (likely in 3.0.0) and this change might occur in a minor or even patch version.
