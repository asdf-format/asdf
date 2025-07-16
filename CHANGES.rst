4.3.0 (2025-07-16)
==================

Bugfix
------

- When ``lazy_load=False`` use ``ndarray`` instances for arrays (instead of
  ``NDArrayType``). (`#1929 <https://github.com/asdf-format/asdf/pull/1929>`_)
- Fix issue where custom schema provided to ``AsdfFile`` was ignored on
  ``write_to``. (`#1931 <https://github.com/asdf-format/asdf/pull/1931>`_)


Doc
---

- Expand extension documentation to cover tag vs ref, converter tag wildcards,
  versioning and user documentation to cover get/set_array_compression. (`#1938
  <https://github.com/asdf-format/asdf/pull/1938>`_)


Feature
-------

- Add ``dump`` ``load`` ``dumps`` and ``loads`` functions. (`#1930
  <https://github.com/asdf-format/asdf/pull/1930>`_)


Removal
-------

- Deprecate ``resolver`` argument to ``asdf.schema.load_schema``. Arbitrary
  mapping of uris is no longer supported. Instead register all uris with
  resources using the resource manager. (`#1934
  <https://github.com/asdf-format/asdf/pull/1934>`_)
- Deprecate ``refresh_extension_manager`` argument to ``info``, ``schema_info``
  and ``SearchResult.schema_info``. (`#1935
  <https://github.com/asdf-format/asdf/pull/1935>`_)
- Deprecate ``url_mapping`` argument to ``get_validator``. Arbitrary mapping of
  urls is no longer supported. (`#1936
  <https://github.com/asdf-format/asdf/pull/1936>`_)
- Deprecate use of ``ndim``, ``max_ndim`` and ``datatype`` validators for
  non-ndarray objects. Please define a custom validator if this is needed for a
  non-ndarray object. (`#1937
  <https://github.com/asdf-format/asdf/pull/1937>`_)


4.2.0 (2025-05-30)
==================

Bugfix
------

- Allow extra keywords in structured datatype validation. (`#1901
  <https://github.com/asdf-format/asdf/pull/1901>`_)
- yield instead of raise ValidationError in validate_datatype to allow use in
  schema combiners (`#1904 <https://github.com/asdf-format/asdf/pull/1904>`_)
- Support recursive tagged nodes in load_yaml. (`#1907
  <https://github.com/asdf-format/asdf/pull/1907>`_)
- Allow non-null bytes before the first byte. (`#1918
  <https://github.com/asdf-format/asdf/pull/1918>`_)
- Fix deepcopy of lazy tree. (`#1922
  <https://github.com/asdf-format/asdf/pull/1922>`_)


Doc
---

- Improve documentation based on review feedback. (`#1913
  <https://github.com/asdf-format/asdf/pull/1913>`_)


Feature
-------

- Optionally use fsspec for urls (like those for s3 resources) provided to
  asdf.open. (`#1906 <https://github.com/asdf-format/asdf/pull/1906>`_)
- Load block index with CSafeLoader if available. (`#1920
  <https://github.com/asdf-format/asdf/pull/1920>`_)


Removal
-------

- Deprecate opening http uris unless fsspec is installed. (`#1906
  <https://github.com/asdf-format/asdf/pull/1906>`_)


4.1.0 (2025-01-31)
==================

Bugfix
------

- Improve ``schema_info`` handling of schemas with combiners (allOf, anyOf,
  etc). (`#1875 <https://github.com/asdf-format/asdf/pull/1875>`_)
- While walking schema for info/search/schema_info walk into nodes with
  __asdf_traverse__
  if the parent node has a schema. (`#1884
  <https://github.com/asdf-format/asdf/pull/1884>`_)
- Don't infinitely loop on recursive lists during info/search/schema_info.
  (`#1884 <https://github.com/asdf-format/asdf/pull/1884>`_)
- Use extension_manager of associated AsdfFile in info/search/schema_info.
  (`#1884 <https://github.com/asdf-format/asdf/pull/1884>`_)
- Only use ANSI format codes when supported by stdout. (`#1884
  <https://github.com/asdf-format/asdf/pull/1884>`_)


Doc
---

- Fix typos in search documentation. (`#1880
  <https://github.com/asdf-format/asdf/pull/1880>`_)
- updates docs theme to be consistent with asdf subprojects (`#1897
  <https://github.com/asdf-format/asdf/pull/1897>`_)


Feature
-------

- Add ``Converter.to_info`` to allow customizing ``info`` output. (`#1884
  <https://github.com/asdf-format/asdf/pull/1884>`_)


4.0.0 (2024-11-19)
==================

Feature
-------

- Switch default ASDF standard to 1.6.0. (`#1744
  <https://github.com/asdf-format/asdf/pull/1744>`_)
- Raise RuntimeError if a Convert subclass supports multiple tags but doesn't
  implement select_tag. (`#1853
  <https://github.com/asdf-format/asdf/pull/1853>`_)


General
-------

- Set ``memmap=False`` to default for ``asdf.open`` and ``AsdfFile.__init__``.
  (`#1801 <https://github.com/asdf-format/asdf/pull/1801>`_)


Removal
-------

- remove ``copy_arrays`` (replaced by ``memmap``) (`#1800
  <https://github.com/asdf-format/asdf/pull/1800>`_)
- Remove deprecated API. See docs for full details. (`#1852
  <https://github.com/asdf-format/asdf/pull/1852>`_)
- Switch default convert_unknown_ndarray_subclasses to False and issue
  deprecation warning if it is enabled. (`#1858
  <https://github.com/asdf-format/asdf/pull/1858>`_)


3.5.0 (2024-10-02)
==================

Bugfix
------

- Allow ``asdf.util.load_yaml`` to handle recursive objects (`#1825
  <https://github.com/asdf-format/asdf/pull/1825>`_)


Doc
---

- added issue links to changelog entries (`#1827
  <https://github.com/asdf-format/asdf/pull/1827>`_)
- Change asdf standard changelog entries to notes to ease transition to
  towncrier (`#1830 <https://github.com/asdf-format/asdf/pull/1830>`_)


General
-------

- fix changelog checker to remove brackets (`#1828
  <https://github.com/asdf-format/asdf/pull/1828>`_)


Removal
-------

- Deprecate ``ignore_version_mismatch``. This option has done nothing since
  asdf 3.0.0 and will be removed in an upcoming asdf version (`#1819
  <https://github.com/asdf-format/asdf/pull/1819>`_)


3.4.0 (2024-08-04)
==================

- Fix issue where roundtripping a masked array with no masked values removes the mask [`#1803 <https://github.com/asdf-format/asdf/issues/1803>`_]

- Use a custom exception ``AsdfSerializationError`` to indicate when an object in the
  tree fails to be serialized by asdf (and by yaml). This exception currently inherits
  from ``yaml.representer.RepresenterError`` to provide backwards compatibility. However
  this inheritance may be dropped in a future asdf version. Please migrate to the new
  ``AsdfSerializationError``. [`#1809 <https://github.com/asdf-format/asdf/issues/1809>`_]

- Drop ``importlib_metadata`` as a dependency on Python 3.12 and newer [`#1810 <https://github.com/asdf-format/asdf/issues/1810>`_]

- Bumped minimal requirement on ``attrs`` from ``20.1.0`` to ``22.2.0`` [`#1815 <https://github.com/asdf-format/asdf/issues/1815>`_]

3.3.0 (2024-07-12)
==================

- Fix ``__asdf_traverse__`` for non-tagged objects [`#1739 <https://github.com/asdf-format/asdf/issues/1739>`_]

- Deprecate ``asdf.testing.helpers.format_tag`` [`#1774 <https://github.com/asdf-format/asdf/issues/1774>`_]

- Deprecate ``asdf.versioning.AsdfSpec`` [`#1774 <https://github.com/asdf-format/asdf/issues/1774>`_]

- Deprecate ``asdf.util.filepath_to_url`` use ``pathlib.Path.to_uri`` [`#1735 <https://github.com/asdf-format/asdf/issues/1735>`_]

- Record package providing manifest for extensions used to write
  a file and ``AsdfPackageVersionWarning`` when installed extension/manifest
  package does not match that used to write the file [`#1758 <https://github.com/asdf-format/asdf/issues/1758>`_]

- Fix bug where a dictionary containing a key ``id`` caused
  any contained references to fail to resolve [`#1716 <https://github.com/asdf-format/asdf/issues/1716>`_]

- Issue a ``AsdfManifestURIMismatchWarning`` during write if a used
  extension was created from a manifest registered with a uri that
  does not match the id in the manifest [`#1785 <https://github.com/asdf-format/asdf/issues/1785>`_]

- Allow converters to provide types as strings that can
  resolve to public classes (even if the class is implemented
  in a private module). [`#1654 <https://github.com/asdf-format/asdf/issues/1654>`_]

- Add options to control saving the base array when saving array views
  controlled via ``AsdfConfig.default_array_save_base``,
  ``AsdfFile.set_array_save_base`` and
  ``SerializationContext.set_array_save_base`` [`#1753 <https://github.com/asdf-format/asdf/issues/1753>`_]

- Deprecate ``ignore_implicit_conversion`` and "implicit conversion" [`#1724 <https://github.com/asdf-format/asdf/issues/1724>`_]

- Add ``lazy_tree`` option to ``asdf.open`` and ``asdf.config``
  to allow lazy deserialization of ASDF tagged tree nodes to
  custom objects. [`#1733 <https://github.com/asdf-format/asdf/issues/1733>`_]

- Deprecate ``copy_arrays`` in favor of ``memmap`` [`#1797 <https://github.com/asdf-format/asdf/issues/1797>`_]

3.2.0 (2024-04-05)
==================

- Deprecate ``AsdfFile.version_map`` [`#1745 <https://github.com/asdf-format/asdf/issues/1745>`_]

- Fix ``numpy.ma.MaskedArray`` saving for numpy 2.x [`#1769 <https://github.com/asdf-format/asdf/issues/1769>`_]

- Add ``float16`` support [`#1692 <https://github.com/asdf-format/asdf/issues/1692>`_]

- Removed unused ``asdf-unit-schemas`` dependency [`#1767 <https://github.com/asdf-format/asdf/issues/1767>`_]


3.1.0 (2024-02-27)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Cleanup ``asdf.util`` including deprecating: ``human_list``
  ``resolve_name`` ``minversion`` and ``iter_subclasses`` [`#1688 <https://github.com/asdf-format/asdf/issues/1688>`_]

- Deprecate validation on ``AsdfFile.tree`` assignment. Please
  use ``AsdfFile.validate`` to validate the tree [`#1691 <https://github.com/asdf-format/asdf/issues/1691>`_]

- Deprecate validation during ``AsdfFile.resolve_references``. Please
  use ``AsdfFile.validate`` to validate the tree [`#1691 <https://github.com/asdf-format/asdf/issues/1691>`_]

- Deprecate ``asdf.asdf`` and ``AsdfFile.resolve_and_inline`` [`#1690 <https://github.com/asdf-format/asdf/issues/1690>`_]

- Deprecate automatic calling of ``AsdfFile.find_references`` during
  ``AsdfFile.__init__`` and ``asdf.open`` [`#1708 <https://github.com/asdf-format/asdf/issues/1708>`_]

- Allow views of memmapped arrays to keep the backing mmap
  open to avoid segfaults [`#1668 <https://github.com/asdf-format/asdf/issues/1668>`_]

- Introduce ``memmap`` argument to ``asdf.open`` that
  overrides ``copy_arrays`` with documentation that describes
  that the default for ``memmap`` when ``copy_arrays``
  is removed in an upcoming asdf release will be ``False`` and
  asdf will no longer by-default memory map arrays. [`#1667 <https://github.com/asdf-format/asdf/issues/1667>`_]

- Introduce ``asdf.util.load_yaml`` to load just the YAML contents
  of an ASDF file (with the option ``tagged`` to load the contents
  as a tree of ``asdf.tagged.Tagged`` instances to preserve tags) [`#1700 <https://github.com/asdf-format/asdf/issues/1700>`_]

- Require pytest 7+ and update asdf pytest plugin to be compatible
  with the current development version of pytest (8.1) [`#1731 <https://github.com/asdf-format/asdf/issues/1731>`_]

- Eliminate the use of the legacy ``tmpdir`` fixture in favor of
  the new ``tmp_path`` fixture for temporary directory creation. [`#1759 <https://github.com/asdf-format/asdf/issues/1759>`_]

- Remove conversion of warnings to errors in asdf pytest plugin. This
  prevented other warning filters (like those provided with ``-W``)
  from working. If you want these warnings to produce errors you can
  now add your own warning filter [`#1757 <https://github.com/asdf-format/asdf/issues/1757>`_]

- Only show ``str`` representation during ``info`` and ``search``
  if it contains a single line (and does not fail)  [`#1748 <https://github.com/asdf-format/asdf/issues/1748>`_]


3.0.1 (2023-10-30)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Fix bug in ``asdftool diff`` for arrays within a list [`#1672 <https://github.com/asdf-format/asdf/issues/1672>`_]
- For ``info`` and ``search`` show ``str`` representation of childless
  (leaf) nodes if ``show_values`` is enabled  [`#1687 <https://github.com/asdf-format/asdf/issues/1687>`_]
- Deprecate ``asdf.util.is_primitive`` [`#1687 <https://github.com/asdf-format/asdf/issues/1687>`_]


3.0.0 (2023-10-16)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Drop support for ASDF-in-FITS. [`#1288 <https://github.com/asdf-format/asdf/issues/1288>`_]
- Add ``all_array_storage``, ``all_array_compression`` and
  ``all_array_compression_kwargs`` to ``asdf.config.AsdfConfig`` [`#1468 <https://github.com/asdf-format/asdf/issues/1468>`_]
- Move built-in tags to converters (except ndarray and integer). [`#1474 <https://github.com/asdf-format/asdf/issues/1474>`_]
- Add block storage support to Converter [`#1508 <https://github.com/asdf-format/asdf/issues/1508>`_]
- Remove deprecated legacy extension API [`#1464 <https://github.com/asdf-format/asdf/issues/1464>`_]
- Fix issue opening files that don't support ``fileno`` [`#1557 <https://github.com/asdf-format/asdf/issues/1557>`_]
- Allow Converters to defer conversion to other Converters
  by returning ``None`` in ``Converter.select_tag`` [`#1561 <https://github.com/asdf-format/asdf/issues/1561>`_]
- Remove deprecated tests.helpers [`#1597 <https://github.com/asdf-format/asdf/issues/1597>`_]
- Remove deprecated load_custom_schema [`#1596 <https://github.com/asdf-format/asdf/issues/1596>`_]
- Remove deprecated TagDefinition.schema_uri [`#1595 <https://github.com/asdf-format/asdf/issues/1595>`_]
- Removed deprecated AsdfFile.open and deprecated asdf.open
  AsdfFile.write_to and AsdfFile.update kwargs [`#1592 <https://github.com/asdf-format/asdf/issues/1592>`_]
- Fix ``AsdfFile.info`` loading all array data [`#1572 <https://github.com/asdf-format/asdf/issues/1572>`_]
- Blank out AsdfFile.tree on close [`#1575 <https://github.com/asdf-format/asdf/issues/1575>`_]
- Move ndarray to a converter, add ``convert_unknown_ndarray_subclasses``
  to ``asdf.config.AsdfConfig``, move ``asdf.Stream`` to
  ``asdf.tags.core.Stream``, update block storage support for
  Converter and update internal block API [`#1537 <https://github.com/asdf-format/asdf/issues/1537>`_]
- Remove deprecated resolve_local_refs argument to load_schema [`#1623 <https://github.com/asdf-format/asdf/issues/1623>`_]
- Move IntegerType to converter and drop cache of converted values. [`#1527 <https://github.com/asdf-format/asdf/issues/1527>`_]
- Remove legacy extension API [`#1637 <https://github.com/asdf-format/asdf/issues/1637>`_]
- Fix bug that left out the name of the arrays that differed
  for ``asdftool diff`` comparisons [`#1652 <https://github.com/asdf-format/asdf/issues/1652>`_]

2.15.2 (2023-09-29)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Add support for python 3.12 [`#1641 <https://github.com/asdf-format/asdf/issues/1641>`_]

2.15.1 (2023-08-07)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Drop Python 3.8 support [`#1556 <https://github.com/asdf-format/asdf/issues/1556>`_]
- Drop NumPy 1.20, 1.21 support [`#1568 <https://github.com/asdf-format/asdf/issues/1568>`_]
- Convert numpy scalars to python types during yaml encoding
  to handle NEP51 changes for numpy 2.0 [`#1605 <https://github.com/asdf-format/asdf/issues/1605>`_]
- Vendorize jsonschema 4.17.3 [`#1591 <https://github.com/asdf-format/asdf/issues/1591>`_]
- Drop jsonschema as a dependency [`#1614 <https://github.com/asdf-format/asdf/issues/1614>`_]

2.15.0 (2023-03-28)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Require numpy<1.25 for python 3.8 [`#1327 <https://github.com/asdf-format/asdf/issues/1327>`_]
- Add AsdfProvisionalAPIWarning to warn developers of new features that
  may undergo breaking changes but are likely to be included as stable
  features (without this warning) in a future version of ASDF [`#1295 <https://github.com/asdf-format/asdf/issues/1295>`_]
- Add AsdfDeprecationWarning to AsdfFile.blocks [`#1336 <https://github.com/asdf-format/asdf/issues/1336>`_]
- Document policy for ASDF release cycle including when support for ASDF versions
  end. Also document dependency support policy. [`#1323 <https://github.com/asdf-format/asdf/issues/1323>`_]
- Update lower pins on ``numpy`` (per release policy), ``packaging``, and ``pyyaml`` to
  ones that we can successfully build and test against. [`#1360 <https://github.com/asdf-format/asdf/issues/1360>`_]
- Provide more informative filename when failing to open a file [`#1357 <https://github.com/asdf-format/asdf/issues/1357>`_]
- Add new plugin type for custom schema validators. [`#1328 <https://github.com/asdf-format/asdf/issues/1328>`_]
- Add AsdfDeprecationWarning to ``asdf.types.CustomType`` [`#1359 <https://github.com/asdf-format/asdf/issues/1359>`_]
- Throw more useful error when provided with a path containing an
  extra leading slash [`#1356 <https://github.com/asdf-format/asdf/issues/1356>`_]
- Add AsdfDeprecationWarning to AsdfInFits. Support for reading and
  writing ASDF in fits files is being moved to `stdatamodels
  <https://github.com/spacetelescope/stdatamodels>`_. [`#1337 <https://github.com/asdf-format/asdf/issues/1337>`_]
- Add AsdfDeprecationWarning to asdf.resolver [`#1362 <https://github.com/asdf-format/asdf/issues/1362>`_]
- Add AsdfDeprecationWarning to asdf.tests.helpers.assert_extension_correctness [`#1388 <https://github.com/asdf-format/asdf/issues/1388>`_]
- Add AsdfDeprecationWarning to asdf.type_index [`#1403 <https://github.com/asdf-format/asdf/issues/1403>`_]
- Add warning to use of asdftool extract and remove-hdu about deprecation
  and impending removal [`#1411 <https://github.com/asdf-format/asdf/issues/1411>`_]
- Deprecate AsdfFile attributes that use the legacy extension api [`#1417 <https://github.com/asdf-format/asdf/issues/1417>`_]
- Add AsdfDeprecationWarning to asdf.types [`#1401 <https://github.com/asdf-format/asdf/issues/1401>`_]
- deprecate default_extensions, get_default_resolver and
  get_cached_asdf_extension_list in asdf.extension [`#1409 <https://github.com/asdf-format/asdf/issues/1409>`_]
- move asdf.types.format_tag to asdf.testing.helpers.format_tag [`#1433 <https://github.com/asdf-format/asdf/issues/1433>`_]
- Deprecate AsdfExtenion, AsdfExtensionList, BuiltinExtension [`#1429 <https://github.com/asdf-format/asdf/issues/1429>`_]
- Add AsdfDeprecationWarning to asdf_extensions entry point [`#1361 <https://github.com/asdf-format/asdf/issues/1361>`_]
- Deprecate asdf.tests.helpers [`#1440 <https://github.com/asdf-format/asdf/issues/1440>`_]
- respect umask when determining file permissions for written files [`#1451 <https://github.com/asdf-format/asdf/issues/1451>`_]
- rename master branch to main [`#1479 <https://github.com/asdf-format/asdf/issues/1479>`_]

2.14.4 (2022-03-17)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- require jsonschema<4.18 [`#1487 <https://github.com/asdf-format/asdf/issues/1487>`_]

2.14.3 (2022-12-15)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Use importlib_metadata for all python versions [`#1260 <https://github.com/asdf-format/asdf/issues/1260>`_]
- Fix issue #1268, where update could fail to clear memmaps for some files [`#1269 <https://github.com/asdf-format/asdf/issues/1269>`_]
- Bump asdf-transform-schemas version [`#1278 <https://github.com/asdf-format/asdf/issues/1278>`_]

2.14.2 (2022-12-05)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Fix issue #1256, where ``enum`` could not be used on tagged objects. [`#1257 <https://github.com/asdf-format/asdf/issues/1257>`_]

2.14.1 (2022-11-23)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Fix issue #1239, close memmap with asdf file context [`#1241 <https://github.com/asdf-format/asdf/issues/1241>`_]
- Add ndarray-1.1.0 and integer-1.1.0 support [`#1250 <https://github.com/asdf-format/asdf/issues/1250>`_]

2.14.0 (2022-11-22)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Update citation. [`#1184 <https://github.com/asdf-format/asdf/issues/1184>`_]
- Add search support to `~asdf.AsdfFile.schema_info`. [`#1187 <https://github.com/asdf-format/asdf/issues/1187>`_]
- Add `asdf.search.AsdfSearchResult` support for `~asdf.AsdfFile.schema_info` and
  `~asdf.search.AsdfSearchResult.schema_info` method. [`#1197 <https://github.com/asdf-format/asdf/issues/1197>`_]
- Use forc ndarray flag to correctly test for fortran array contiguity [`#1206 <https://github.com/asdf-format/asdf/issues/1206>`_]
- Unpin ``jsonschema`` version and fix ``jsonschema`` deprecation warnings. [`#1185 <https://github.com/asdf-format/asdf/issues/1185>`_]
- Replace ``pkg_resources`` with ``importlib.metadata``. [`#1199 <https://github.com/asdf-format/asdf/issues/1199>`_]
- Fix default validation for jsonschema 4.10+ [`#1203 <https://github.com/asdf-format/asdf/issues/1203>`_]
- Add ``asdf-unit-schemas`` as a dependency, for backwards compatibility. [`#1210 <https://github.com/asdf-format/asdf/issues/1210>`_]
- Remove stray toplevel packages ``docker`` ``docs`` and ``compatibility_tests`` from wheel [`#1214 <https://github.com/asdf-format/asdf/issues/1214>`_]
- Close files opened during a failed call to asdf.open [`#1221 <https://github.com/asdf-format/asdf/issues/1221>`_]
- Modify generic_file for fsspec compatibility [`#1226 <https://github.com/asdf-format/asdf/issues/1226>`_]
- Add fsspec http filesystem support [`#1228 <https://github.com/asdf-format/asdf/issues/1228>`_]
- Memmap whole file instead of each array [`#1230 <https://github.com/asdf-format/asdf/issues/1230>`_]
- Fix issue #1232 where array data was duplicated during resaving of a fits file [`#1234 <https://github.com/asdf-format/asdf/issues/1234>`_]

2.13.0 (2022-08-19)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Add ability to pull information from schema about asdf file data, using `~asdf.AsdfFile.schema_info`
  method. [`#1167 <https://github.com/asdf-format/asdf/issues/1167>`_]

2.12.1 (2022-08-17)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Overhaul of the ASDF documentation to make it more consistent and readable. [`#1142 <https://github.com/asdf-format/asdf/issues/1142>`_, `#1152 <https://github.com/asdf-format/asdf/issues/1152>`_]
- Update deprecated instances of ``abstractproperty`` to ``abstractmethod`` [`#1148 <https://github.com/asdf-format/asdf/issues/1148>`_]
- Move build configuration into ``pyproject.toml`` [`#1149 <https://github.com/asdf-format/asdf/issues/1149>`_, `#1155 <https://github.com/asdf-format/asdf/issues/1155>`_]
- Pin ``jsonschema`` to below ``4.10.0``. [`#1171 <https://github.com/asdf-format/asdf/issues/1171>`_]

2.12.0 (2022-06-06)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Added ability to display title as a comment in using the
  ``info()`` functionality. [`#1138 <https://github.com/asdf-format/asdf/issues/1138>`_]
- Add ability to set asdf-standard version for schema example items. [`#1143 <https://github.com/asdf-format/asdf/issues/1143>`_]

2.11.2 (2022-08-17)
==================-

- Backport ``jsonschema`` pin to strictly less than 4.10.1. [`#1175 <https://github.com/asdf-format/asdf/issues/1175>`_]

2.11.1 (2022-04-15)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Update minimum astropy version to 5.0.4. [`#1133 <https://github.com/asdf-format/asdf/issues/1133>`_]

2.11.0 (2022-03-15)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Update minimum jsonschema version to 4.0.1. [`#1105 <https://github.com/asdf-format/asdf/issues/1105>`_]

2.10.1 (2022-03-02)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Bugfix for circular build dependency for asdf. [`#1094 <https://github.com/asdf-format/asdf/issues/1094>`_]

- Fix small bug with handling multiple schema uris per tag. [`#1095 <https://github.com/asdf-format/asdf/issues/1095>`_]

2.10.0 (2022-02-17)
==================-

.. note::
    The ASDF Standard is at v1.6.0

- Replace asdf-standard submodule with pypi package. [`#1079 <https://github.com/asdf-format/asdf/issues/1079>`_]

2.9.2 (2022-02-07)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Fix deprecation warnings stemming from the release of pytest 7.0.0. [`#1075 <https://github.com/asdf-format/asdf/issues/1075>`_]

- Fix bug in pytest plugin when schemas are not in a directory named "schemas". [`#1076 <https://github.com/asdf-format/asdf/issues/1076>`_]

2.9.1 (2022-02-03)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Fix typo in testing module ``__init__.py`` name. [`#1071 <https://github.com/asdf-format/asdf/issues/1071>`_]

2.9.0 (2022-02-02)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Added the capability for tag classes to provide an interface
  to asdf info functionality to obtain information about the
  class attributes rather than appear as an opaque class object.
  [`#1052 <https://github.com/asdf-format/asdf/issues/1052>`_ `#1055 <https://github.com/asdf-format/asdf/issues/1055>`_]

- Fix tag listing when extension is not fully implemented. [`#1034 <https://github.com/asdf-format/asdf/issues/1034>`_]

- Drop support for Python 3.6. [`#1054 <https://github.com/asdf-format/asdf/issues/1054>`_]

- Adjustments to compression plugin tests and documentation. [`#1053 <https://github.com/asdf-format/asdf/issues/1053>`_]

- Update setup.py to raise error if "git submodule update --init" has
  not been run. [`#1057 <https://github.com/asdf-format/asdf/issues/1057>`_]

- Add ability for tags to correspond to multiple schema_uri, with an
  implied allOf among the schema_uris. [`#1058 <https://github.com/asdf-format/asdf/issues/1058>`_, `#1069 <https://github.com/asdf-format/asdf/issues/1069>`_]

- Add the URL of the file being parsed to ``SerializationContext``. [`#1065 <https://github.com/asdf-format/asdf/issues/1065>`_]

- Add ``asdf.testing.helpers`` module with simplified versions of test
  helpers previously available in ``asdf.tests.helpers``. [`#1067 <https://github.com/asdf-format/asdf/issues/1067>`_]

2.8.3 (2021-12-13)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Fix more use of 'python' where 'python3' is intended. [`#1033 <https://github.com/asdf-format/asdf/issues/1033>`_]

2.8.2 (2021-12-06)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Update documentation to reflect new 2.8 features. [`#998 <https://github.com/asdf-format/asdf/issues/998>`_]

- Fix array compression for non-native byte order [`#1010 <https://github.com/asdf-format/asdf/issues/1010>`_]

- Fix use of 'python' where 'python3' is intended. [`#1026 <https://github.com/asdf-format/asdf/issues/1026>`_]

- Fix schema URI resolving when the URI prefix is also
  claimed by a legacy extension. [`#1029 <https://github.com/asdf-format/asdf/issues/1029>`_]

- Remove 'name' and 'version' attributes from NDArrayType
  instances. [`#1031 <https://github.com/asdf-format/asdf/issues/1031>`_]

2.8.1 (2021-06-09)
==================

- Fix bug in block manager when a new block is added to an existing
  file without a block index. [`#1000 <https://github.com/asdf-format/asdf/issues/1000>`_]

2.8.0 (2021-05-12)
==================

.. note::
    The ASDF Standard is at v1.6.0

- Add ``yaml_tag_handles`` property to allow definition of custom yaml
  ``%TAG`` handles in the asdf file header. [`#963 <https://github.com/asdf-format/asdf/issues/963>`_]

- Add new resource mapping API for extending asdf with additional
  schemas. [`#819 <https://github.com/asdf-format/asdf/issues/819>`_, `#828 <https://github.com/asdf-format/asdf/issues/828>`_, `#843 <https://github.com/asdf-format/asdf/issues/843>`_, `#846 <https://github.com/asdf-format/asdf/issues/846>`_]

- Add global configuration mechanism. [`#819 <https://github.com/asdf-format/asdf/issues/819>`_, `#839 <https://github.com/asdf-format/asdf/issues/839>`_, `#844 <https://github.com/asdf-format/asdf/issues/844>`_, `#847 <https://github.com/asdf-format/asdf/issues/847>`_]

- Drop support for automatic serialization of subclass
  attributes. [`#825 <https://github.com/asdf-format/asdf/issues/825>`_]

- Support asdf:// as a URI scheme. [`#854 <https://github.com/asdf-format/asdf/issues/854>`_, `#855 <https://github.com/asdf-format/asdf/issues/855>`_]

- Include only extensions used during serialization in
  a file's metadata. [`#848 <https://github.com/asdf-format/asdf/issues/848>`_, `#864 <https://github.com/asdf-format/asdf/issues/864>`_]

- Drop support for Python 3.5. [`#856 <https://github.com/asdf-format/asdf/issues/856>`_]

- Add new extension API to support versioned extensions.
  [`#850 <https://github.com/asdf-format/asdf/issues/850>`_, `#851 <https://github.com/asdf-format/asdf/issues/851>`_, `#853 <https://github.com/asdf-format/asdf/issues/853>`_, `#857 <https://github.com/asdf-format/asdf/issues/857>`_, `#874 <https://github.com/asdf-format/asdf/issues/874>`_]

- Permit wildcard in tag validator URIs. [`#858 <https://github.com/asdf-format/asdf/issues/858>`_, `#865 <https://github.com/asdf-format/asdf/issues/865>`_]

- Implement support for ASDF Standard 1.6.0.  This version of
  the standard limits mapping keys to string, integer, or
  boolean. [`#866 <https://github.com/asdf-format/asdf/issues/866>`_]

- Stop removing schema defaults for all ASDF Standard versions,
  and automatically fill defaults only for versions <= 1.5.0. [`#860 <https://github.com/asdf-format/asdf/issues/860>`_]

- Stop removing keys with ``None`` values from the tree on write.  This
  fixes a long-standing issue where the tree structure is not preserved
  on write, but will break ``ExtensionType`` subclasses that depend on
  this behavior.  Extension developers will need to modify their
  ``to_tree`` methods to check for ``None`` before adding a key to
  the tree (or modify the schema to permit nulls, if that is the
  intention). [`#863 <https://github.com/asdf-format/asdf/issues/863>`_]

- Deprecated the ``auto_inline`` argument to ``AsdfFile.write_to`` and
  ``AsdfFile.update`` and added ``AsdfConfig.array_inline_threshold``. [`#882 <https://github.com/asdf-format/asdf/issues/882>`_, `#991 <https://github.com/asdf-format/asdf/issues/991>`_]

- Add ``edit`` subcommand to asdftool for efficient editing of
  the YAML portion of an ASDF file.  [`#873 <https://github.com/asdf-format/asdf/issues/873>`_, `#922 <https://github.com/asdf-format/asdf/issues/922>`_]

- Increase limit on integer literals to signed 64-bit. [`#894 <https://github.com/asdf-format/asdf/issues/894>`_]

- Remove the ``asdf.test`` method and ``asdf.__githash__`` attribute. [`#943 <https://github.com/asdf-format/asdf/issues/943>`_]

- Add support for custom compression via extensions. [`#931 <https://github.com/asdf-format/asdf/issues/931>`_]

- Remove unnecessary ``.tree`` from search result paths. [`#954 <https://github.com/asdf-format/asdf/issues/954>`_]

- Drop support for bugs in older operating systems and Python versions. [`#955 <https://github.com/asdf-format/asdf/issues/955>`_]

- Add argument to ``asdftool diff`` that ignores tree nodes that match
  a JMESPath expression. [`#956 <https://github.com/asdf-format/asdf/issues/956>`_]

- Fix behavior of ``exception`` argument to ``GenericFile.seek_until``. [`#980 <https://github.com/asdf-format/asdf/issues/980>`_]

- Fix issues in file type detection to allow non-seekable input and
  filenames without recognizable extensions.  Remove the ``asdf.asdf.is_asdf_file``
  function. [`#978 <https://github.com/asdf-format/asdf/issues/978>`_]

- Update ``asdftool extensions`` and ``asdftool tags`` to incorporate
  the new extension API. [`#988 <https://github.com/asdf-format/asdf/issues/988>`_]

- Add ``AsdfSearchResult.replace`` method for assigning new values to
  search results. [`#981 <https://github.com/asdf-format/asdf/issues/981>`_]

- Search for block index starting from end of file. Fixes rare bug when
  a data block contains a block index. [`#990 <https://github.com/asdf-format/asdf/issues/990>`_]

- Update asdf-standard to 1.6.0 tag. [`#993 <https://github.com/asdf-format/asdf/issues/993>`_]

2.7.5 (2021-06-09)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Fix bug in ``asdf.schema.check_schema`` causing relative references in
  metaschemas to be resolved incorrectly. [`#987 <https://github.com/asdf-format/asdf/issues/987>`_]

- Fix bug in block manager when a new block is added to an existing
  file without a block index. [`#1000 <https://github.com/asdf-format/asdf/issues/1000>`_]

2.7.4 (2021-04-30)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Fix pytest plugin failure under older versions of pytest. [`#934 <https://github.com/asdf-format/asdf/issues/934>`_]

- Copy array views when the base array is non-contiguous. [`#949 <https://github.com/asdf-format/asdf/issues/949>`_]

- Prohibit views over FITS arrays that change dtype. [`#952 <https://github.com/asdf-format/asdf/issues/952>`_]

- Add support for HTTPS URLs and following redirects. [`#971 <https://github.com/asdf-format/asdf/issues/971>`_]

- Prevent astropy warnings in tests when opening known bad files. [`#977 <https://github.com/asdf-format/asdf/issues/977>`_]

2.7.3 (2021-02-25)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Add pytest plugin options to skip and xfail individual tests
  and xfail the unsupported ndarray-1.0.0 example. [`#929 <https://github.com/asdf-format/asdf/issues/929>`_]

- Fix bug resulting in invalid strides values for views over
  FITS arrays. [`#930 <https://github.com/asdf-format/asdf/issues/930>`_]

2.7.2 (2021-01-15)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Fix bug causing test collection failures in some environments. [`#889 <https://github.com/asdf-format/asdf/issues/889>`_]

- Fix bug when decompressing arrays with numpy 1.20.  [`#901 <https://github.com/asdf-format/asdf/issues/901>`_, `#909 <https://github.com/asdf-format/asdf/issues/909>`_]

2.7.1 (2020-08-18)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Fix bug preventing access to copied array data after
  ``AsdfFile`` is closed. [`#869 <https://github.com/asdf-format/asdf/issues/869>`_]

2.7.0 (2020-07-23)
==================

.. note::
    The ASDF Standard is at v1.5.0

- Fix bug preventing diff of files containing ndarray-1.0.0
  objects in simplified form. [`#786 <https://github.com/asdf-format/asdf/issues/786>`_]

- Fix bug causing duplicate elements to appear when calling
  ``copy.deepcopy`` on a ``TaggedList``. [`#788 <https://github.com/asdf-format/asdf/issues/788>`_]

- Improve validator performance by skipping unnecessary step of
  copying schema objects. [`#784 <https://github.com/asdf-format/asdf/issues/784>`_]

- Fix bug with ``auto_inline`` option where inline blocks
  are not converted to internal when they exceed the threshold. [`#802 <https://github.com/asdf-format/asdf/issues/802>`_]

- Fix misinterpretation of byte order of blocks stored
  in FITS files. [`#810 <https://github.com/asdf-format/asdf/issues/810>`_]

- Improve read performance by skipping unnecessary rebuild
  of tagged tree. [`#787 <https://github.com/asdf-format/asdf/issues/787>`_]

- Add option to ``asdf.open`` and ``fits_embed.AsdfInFits.open``
  that disables validation on read. [`#792 <https://github.com/asdf-format/asdf/issues/792>`_]

- Fix bugs and code style found by adding F and W ``flake8`` checks. [`#797 <https://github.com/asdf-format/asdf/issues/797>`_]

- Eliminate warnings in pytest plugin by using ``from_parent``
  when available. [`#799 <https://github.com/asdf-format/asdf/issues/799>`_]

- Prevent validation of empty tree when ``AsdfFile`` is
  initialized. [`#794 <https://github.com/asdf-format/asdf/issues/794>`_]

- All warnings now subclass ``asdf.exceptions.AsdfWarning``. [`#804 <https://github.com/asdf-format/asdf/issues/804>`_]

- Improve warning message when falling back to an older schema,
  and note that fallback behavior will be removed in 3.0. [`#806 <https://github.com/asdf-format/asdf/issues/806>`_]

- Drop support for jsonschema 2.x. [`#807 <https://github.com/asdf-format/asdf/issues/807>`_]

- Stop traversing oneOf and anyOf combiners when filling
  or removing default values. [`#811 <https://github.com/asdf-format/asdf/issues/811>`_]

- Fix bug in version map caching that caused incompatible
  tags to be written under ASDF Standard 1.0.0. [`#821 <https://github.com/asdf-format/asdf/issues/821>`_]

- Fix bug that corrupted ndarrays when the underlying block
  array was converted to C order on write. [`#827 <https://github.com/asdf-format/asdf/issues/827>`_]

- Fix bug that produced unreadable ASDF files when an
  ndarray in the tree was both offset and broadcasted. [`#827 <https://github.com/asdf-format/asdf/issues/827>`_]

- Fix bug preventing validation of default values in
  ``schema.check_schema``. [`#785 <https://github.com/asdf-format/asdf/issues/785>`_]

- Add option to disable validation of schema default values
  in the pytest plugin. [`#831 <https://github.com/asdf-format/asdf/issues/831>`_]

- Prevent errors when extension metadata contains additional
  properties. [`#832 <https://github.com/asdf-format/asdf/issues/832>`_]

2.6.0 (2020-04-22)
==================

.. note::
    The ASDF Standard is at v1.5.0

- AsdfDeprecationWarning now subclasses DeprecationWarning. [`#710 <https://github.com/asdf-format/asdf/issues/710>`_]

- Resolve external references in custom schemas, and deprecate
  asdf.schema.load_custom_schema.  [`#738 <https://github.com/asdf-format/asdf/issues/738>`_]

- Add ``asdf.info`` for displaying a summary of a tree, and
  ``AsdfFile.search`` for searching a tree. [`#736 <https://github.com/asdf-format/asdf/issues/736>`_]

- Add pytest plugin option to skip warning when a tag is
  unrecognized. [`#771 <https://github.com/asdf-format/asdf/issues/771>`_]

- Fix generic_io ``read_blocks()`` reading past the requested size [`#773 <https://github.com/asdf-format/asdf/issues/773>`_]

- Add support for ASDF Standard 1.5.0, which includes several new
  transform schemas. [`#776 <https://github.com/asdf-format/asdf/issues/776>`_]

- Enable validation and serialization of previously unhandled numpy
  scalar types. [`#778 <https://github.com/asdf-format/asdf/issues/778>`_]

- Fix handling of trees containing implicit internal references and
  reference cycles.  Eliminate need to call ``yamlutil.custom_tree_to_tagged_tree``
  and ``yamlutil.tagged_tree_to_custom_tree`` from extension code,
  and allow ``ExtensionType`` subclasses to return generators. [`#777 <https://github.com/asdf-format/asdf/issues/777>`_]

- Fix bug preventing history entries when a file was previously
  saved without them. [`#779 <https://github.com/asdf-format/asdf/issues/779>`_]

- Update developer overview documentation to describe design of changes
  to handle internal references and reference cycles. [`#781 <https://github.com/asdf-format/asdf/issues/781>`_]

2.5.2 (2020-02-28)
==================

.. note::
    The ASDF Standard is at v1.4.0

- Add a developer overview document to help understand how ASDF works
  internally. Still a work in progress. [`#730 <https://github.com/asdf-format/asdf/issues/730>`_]

- Remove unnecessary dependency on six. [`#739 <https://github.com/asdf-format/asdf/issues/739>`_]

- Add developer documentation on schema versioning, additional
  schema and extension-related tests, and fix a variety of
  issues in ``AsdfType`` subclasses. [`#750 <https://github.com/asdf-format/asdf/issues/750>`_]

- Update asdf-standard to include schemas that were previously
  missing from 1.4.0 version maps.  [`#767 <https://github.com/asdf-format/asdf/issues/767>`_]

- Simplify example in README.rst [`#763 <https://github.com/asdf-format/asdf/issues/763>`_]

2.5.1 (2020-01-07)
==================

.. note::
    The ASDF Standard is at v1.4.0

- Fix bug in test causing failure when test suite is run against
  an installed asdf package. [`#732 <https://github.com/asdf-format/asdf/issues/732>`_]

2.5.0 (2019-12-23)
==================

.. note::
    The ASDF Standard is at v1.4.0

- Added asdf-standard 1.4.0 to the list of supported versions. [`#704 <https://github.com/asdf-format/asdf/issues/704>`_]
- Fix load_schema LRU cache memory usage issue [`#682 <https://github.com/asdf-format/asdf/issues/682>`_]
- Add convenience method for fetching the default resolver [`#682 <https://github.com/asdf-format/asdf/issues/682>`_]

- ``SpecItem`` and ``Spec`` were deprecated  in ``semantic_version``
  and were replaced with ``SimpleSpec``. [`#715 <https://github.com/asdf-format/asdf/issues/715>`_]

- Pinned the minimum required ``semantic_version`` to 2.8. [`#715 <https://github.com/asdf-format/asdf/issues/715>`_]

- Fix bug causing segfault after update of a memory-mapped file. [`#716 <https://github.com/asdf-format/asdf/issues/716>`_]

2.4.2 (2019-08-29)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Limit the version of ``semantic_version`` to <=2.6.0 to work
  around a Deprecation warning. [`#700 <https://github.com/asdf-format/asdf/issues/700>`_]

2.4.1 (2019-08-27)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Define the ``in`` operator for top-level ``AsdfFile`` objects. [`#623 <https://github.com/asdf-format/asdf/issues/623>`_]

- Overhaul packaging infrastructure. Remove use of ``astropy_helpers``. [`#670 <https://github.com/asdf-format/asdf/issues/670>`_]

- Automatically register schema tester plugin. Do not enable schema tests by
  default. Add configuration setting and command line option to enable schema
  tests. [`#676 <https://github.com/asdf-format/asdf/issues/676>`_]

- Enable handling of subclasses of known custom types by using decorators for
  convenience. [`#563 <https://github.com/asdf-format/asdf/issues/563>`_]

- Add support for jsonschema 3.x. [`#684 <https://github.com/asdf-format/asdf/issues/684>`_]

- Fix bug in ``NDArrayType.__len__``.  It must be a method, not a
  property. [`#673 <https://github.com/asdf-format/asdf/issues/673>`_]

2.3.3 (2019-04-02)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Pass ``ignore_unrecognized_tag`` setting through to ASDF-in-FITS. [`#650 <https://github.com/asdf-format/asdf/issues/650>`_]

- Use ``$schema`` keyword if available to determine meta-schema to use when
  testing whether schemas themselves are valid. [`#654 <https://github.com/asdf-format/asdf/issues/654>`_]

- Take into account resolvers from installed extensions when loading schemas
  for validation. [`#655 <https://github.com/asdf-format/asdf/issues/655>`_]

- Fix compatibility issue with new release of ``pyyaml`` (version 5.1). [`#662 <https://github.com/asdf-format/asdf/issues/662>`_]

- Allow use of ``pathlib.Path`` objects for ``custom_schema`` option. [`#663 <https://github.com/asdf-format/asdf/issues/663>`_]

2.3.2 (2019-02-19)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Fix bug that occurs when comparing installed extension version with that
  found in file. [`#641 <https://github.com/asdf-format/asdf/issues/641>`_]

2.3.1 (2018-12-20)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Provide source information for ``AsdfDeprecationWarning`` that come from
  extensions from external packages. [`#629 <https://github.com/asdf-format/asdf/issues/629>`_]

- Ensure that top-level accesses to the tree outside a closed context handler
  result in an ``OSError``. [`#628 <https://github.com/asdf-format/asdf/issues/628>`_]

- Fix the way ``generic_io`` handles URIs and paths on Windows. [`#632 <https://github.com/asdf-format/asdf/issues/632>`_]

- Fix bug in ``asdftool`` that prevented ``extract`` command from being
  visible. [`#633 <https://github.com/asdf-format/asdf/issues/633>`_]

2.3.0 (2018-11-28)
==================

.. note::
    The ASDF Standard is at v1.3.0

- Storage of arbitrary precision integers is now provided by
  ``asdf.IntegerType``.  Reading a file with integer literals that are too
  large now causes only a warning instead of a validation error. This is to
  provide backwards compatibility for files that were created with a buggy
  version of ASDF (see #553 below). [`#566 <https://github.com/asdf-format/asdf/issues/566>`_]

- Remove WCS tags. These are now provided by the `gwcs package
  <https://github.com/spacetelescope/gwcs>`_. [`#593 <https://github.com/asdf-format/asdf/issues/593>`_]

- Deprecate the ``asdf.asdftypes`` module in favor of ``asdf.types``. [`#611 <https://github.com/asdf-format/asdf/issues/611>`_]

- Support use of ``pathlib.Path`` with ``asdf.open`` and ``AsdfFile.write_to``.
  [`#617 <https://github.com/asdf-format/asdf/issues/617>`_]

- Update ASDF Standard submodule to version 1.3.0.

2.2.1 (2018-11-15)
==================

- Fix an issue with the README that caused sporadic installation failures and
  also prevented the long description from being rendered on pypi. [`#607 <https://github.com/asdf-format/asdf/issues/607>`_]

2.2.0 (2018-11-14)
==================

- Add new parameter ``lazy_load`` to ``AsdfFile.open``. It is ``True`` by
  default and preserves the default behavior. ``False`` detaches the
  loaded tree from the underlying file: all blocks are fully read and
  numpy arrays are materialized. Thus it becomes safe to close the file
  and continue using ``AsdfFile.tree``. However, ``copy_arrays`` parameter
  is still effective and the active memory maps may still require the file
  to stay open in case ``copy_arrays`` is ``False``. [`#573 <https://github.com/asdf-format/asdf/issues/573>`_]

- Add ``AsdfConversionWarning`` for failures to convert ASDF tree into custom
  types. This warning is converted to an error when using
  ``assert_roundtrip_tree`` for tests. [`#583 <https://github.com/asdf-format/asdf/issues/583>`_]

- Deprecate ``asdf.AsdfFile.open`` in favor of ``asdf.open``. [`#579 <https://github.com/asdf-format/asdf/issues/579>`_]

- Add readonly protection to memory mapped arrays when the underlying file
  handle is readonly. [`#579 <https://github.com/asdf-format/asdf/issues/579>`_]

2.1.2 (2018-11-13)
==================

- Make sure that all types corresponding to core tags are added to the type
  index before any others. This fixes a bug that was related to the way that
  subclass tags were overwritten by external extensions. [`#598 <https://github.com/asdf-format/asdf/issues/598>`_]

2.1.1 (2018-11-01)
==================

- Make sure extension metadata is written even when constructing the ASDF tree
  on-the-fly. [`#549 <https://github.com/asdf-format/asdf/issues/549>`_]

- Fix large integer validation when storing `numpy` integer literals in the
  tree. [`#553 <https://github.com/asdf-format/asdf/issues/553>`_]

- Fix bug that caused subclass of external type to be serialized by the wrong
  tag. [`#560 <https://github.com/asdf-format/asdf/issues/560>`_]

- Fix bug that occurred when attempting to open invalid file but Astropy import
  fails while checking for ASDF-in-FITS. [`#562 <https://github.com/asdf-format/asdf/issues/562>`_]

- Fix bug that caused tree creation to fail when unable to locate a schema file
  for an unknown tag. This now simply causes a warning, and the offending node
  is converted to basic Python data structures. [`#571 <https://github.com/asdf-format/asdf/issues/571>`_]

2.1.0 (2018-09-25)
==================

- Add API function for retrieving history entries. [`#501 <https://github.com/asdf-format/asdf/issues/501>`_]

- Store ASDF-in-FITS data inside a 1x1 BINTABLE HDU. [`#519 <https://github.com/asdf-format/asdf/issues/519>`_]

- Allow implicit conversion of ``namedtuple`` into serializable types. [`#534 <https://github.com/asdf-format/asdf/issues/534>`_]

- Fix bug that prevented use of ASDF-in-FITS with HDUs that have names with
  underscores. [`#543 <https://github.com/asdf-format/asdf/issues/543>`_]

- Add option to ``generic_io.get_file`` to close underlying file handle. [`#544 <https://github.com/asdf-format/asdf/issues/544>`_]

- Add top-level ``keys`` method to ``AsdfFile`` to access tree keys. [`#545 <https://github.com/asdf-format/asdf/issues/545>`_]

2.0.3 (2018-09-06)
==================

- Update asdf-standard to reflect more stringent (and, consequently, more
  correct) requirements on the formatting of complex numbers. [`#526 <https://github.com/asdf-format/asdf/issues/526>`_]

- Fix bug with dangling file handle when using ASDF-in-FITS. [`#533 <https://github.com/asdf-format/asdf/issues/533>`_]

- Fix bug that prevented fortran-order arrays from being serialized properly.
  [`#539 <https://github.com/asdf-format/asdf/issues/539>`_]

2.0.2 (2018-07-27)
==================

- Allow serialization of broadcasted ``numpy`` arrays. [`#507 <https://github.com/asdf-format/asdf/issues/507>`_]

- Fix bug that caused result of ``set_array_compression`` to be overwritten by
  ``all_array_compression`` argument to ``write_to``. [`#510 <https://github.com/asdf-format/asdf/issues/510>`_]

- Add workaround for Python OSX write limit bug
  (see https://bugs.python.org/issue24658). [`#521 <https://github.com/asdf-format/asdf/issues/521>`_]

- Fix bug with custom schema validation when using out-of-line definitions in
  schema file. [`#522 <https://github.com/asdf-format/asdf/issues/522>`_]

2.0.1 (2018-05-08)
==================

- Allow test suite to run even when package is not installed. [`#502 <https://github.com/asdf-format/asdf/issues/502>`_]

2.0.0 (2018-04-19)
==================

- Astropy-specific tags have moved to Astropy core package. [`#359 <https://github.com/asdf-format/asdf/issues/359>`_]

- ICRSCoord tag has moved to Astropy core package. [`#401 <https://github.com/asdf-format/asdf/issues/401>`_]

- Remove support for Python 2. [`#409 <https://github.com/asdf-format/asdf/issues/409>`_]

- Create ``pytest`` plugin to be used for testing schema files. [`#425 <https://github.com/asdf-format/asdf/issues/425>`_]

- Add metadata about extensions used to create a file to the history section of
  the file itself. [`#475 <https://github.com/asdf-format/asdf/issues/475>`_]

- Remove hard dependency on Astropy. It is still required for testing, and for
  processing ASDF-in-FITS files. [`#476 <https://github.com/asdf-format/asdf/issues/476>`_]

- Add command for extracting ASDF extension from ASDF-in-FITS file and
  converting it to a pure ASDF file. [`#477 <https://github.com/asdf-format/asdf/issues/477>`_]

- Add command for removing ASDF extension from ASDF-in-FITS file. [`#480 <https://github.com/asdf-format/asdf/issues/480>`_]

- Add an ``ExternalArrayReference`` type for referencing arrays in external
  files. [`#400 <https://github.com/asdf-format/asdf/issues/400>`_]

- Improve the way URIs are detected for ASDF-in-FITS files in order to fix bug
  with reading gzipped ASDF-in-FITS files. [`#416 <https://github.com/asdf-format/asdf/issues/416>`_]

- Explicitly disallow access to entire tree for ASDF file objects that have
  been closed. [`#407 <https://github.com/asdf-format/asdf/issues/407>`_]

- Install and load extensions using ``setuptools`` entry points. [`#384 <https://github.com/asdf-format/asdf/issues/384>`_]

- Automatically initialize ``asdf-standard`` submodule in ``setup.py``. [`#398 <https://github.com/asdf-format/asdf/issues/398>`_]

- Allow foreign tags to be resolved in schemas and files. Deprecate
  ``tag_to_schema_resolver`` property for ``AsdfFile`` and
  ``AsdfExtensionList``. [`#399 <https://github.com/asdf-format/asdf/issues/399>`_]

- Fix bug that caused serialized FITS tables to be duplicated in embedded ASDF
  HDU. [`#411 <https://github.com/asdf-format/asdf/issues/411>`_]

- Create and use a new non-standard FITS extension instead of ImageHDU for
  storing ASDF files embedded in FITS. Explicitly remove support for the
  ``.update`` method of ``AsdfInFits``, even though it didn't appear to be
  working previously. [`#412 <https://github.com/asdf-format/asdf/issues/412>`_]

- Allow package to be imported and used from source directory and builds in
  development mode. [`#420 <https://github.com/asdf-format/asdf/issues/420>`_]

- Add command to ``asdftool`` for querying installed extensions. [`#418 <https://github.com/asdf-format/asdf/issues/418>`_]

- Implement optional top-level validation pass using custom schema. This can be
  used to ensure that particular ASDF files follow custom conventions beyond
  those enforced by the standard. [`#442 <https://github.com/asdf-format/asdf/issues/442>`_]

- Remove restrictions affecting top-level attributes ``data``, ``wcs``, and
  ``fits``. Bump top-level ASDF schema version to v1.1.0. [`#444 <https://github.com/asdf-format/asdf/issues/444>`_]

1.3.3 (2018-03-01)
==================

- Update test infrastructure to rely on new Astropy v3.0 plugins. [`#461 <https://github.com/asdf-format/asdf/issues/461>`_]

- Disable use of 2to3. This was causing test failures on Debian builds. [`#463 <https://github.com/asdf-format/asdf/issues/463>`_]

1.3.2 (2018-02-22)
==================

- Updates to allow this version of ASDF to be compatible with Astropy v3.0.
  [`#450 <https://github.com/asdf-format/asdf/issues/450>`_]

- Remove tests that are no longer relevant due to latest updates to Astropy's
  testing infrastructure. [`#458 <https://github.com/asdf-format/asdf/issues/458>`_]

1.3.1 (2017-11-02)
==================

- Relax requirement on ``semantic_version`` version to 2.3.1. [`#361 <https://github.com/asdf-format/asdf/issues/361>`_]

- Fix bug when retrieving file format version from new ASDF file. [`#365 <https://github.com/asdf-format/asdf/issues/365>`_]

- Fix bug when duplicating inline arrays. [`#370 <https://github.com/asdf-format/asdf/issues/370>`_]

- Allow tag references using the tag URI scheme to be resolved in schema files.
  [`#371 <https://github.com/asdf-format/asdf/issues/371>`_]

1.3.0 (2017-10-24)
==================

- Fixed a bug in reading data from an "http:" url. [`#231 <https://github.com/asdf-format/asdf/issues/231>`_]

- Implements v 1.1.0 of the asdf schemas. [`#233 <https://github.com/asdf-format/asdf/issues/233>`_]

- Added a function ``is_asdf_file`` which inspects the input and
  returns ``True`` or ``False``. [`#239 <https://github.com/asdf-format/asdf/issues/239>`_]

- The ``open`` method of ``AsdfInFits`` now accepts URIs and open file handles
  in addition to HDULists. The ``open`` method of ``AsdfFile`` will now try to
  parse the given URI or file handle as ``AsdfInFits`` if it is not obviously a
  regular ASDF file. [`#241 <https://github.com/asdf-format/asdf/issues/241>`_]

- Updated WCS frame fields ``obsgeoloc`` and ``obsgeovel`` to reflect recent
  updates in ``astropy`` that changed representation from ``Quantity`` to
  ``CartesianRepresentation``. Updated to reflect ``astropy`` change that
  combines ``galcen_ra`` and ``galcen_dec`` into ``galcen_coord``. Added
  support for new field ``galcen_v_sun``. Added support for required module
  versions for tag classes. [`#244 <https://github.com/asdf-format/asdf/issues/244>`_]

- Added support for ``lz4`` compression algorithm [`#258 <https://github.com/asdf-format/asdf/issues/258>`_]. Also added support
  for using a different compression algorithm for writing out a file than the
  one that was used for reading the file (e.g. to convert blocks to use a
  different compression algorithm) [`#257 <https://github.com/asdf-format/asdf/issues/257>`_]

- Tag classes may now use an optional ``supported_versions`` attribute to
  declare exclusive support for particular versions of the corresponding
  schema. If this attribute is omitted (as it is for most existing tag
  classes), the tag is assumed to be compatible with all versions of the
  corresponding schema. If ``supported_versions`` is provided, the tag class
  implementation can include code that is conditioned on the schema version. If
  an incompatible schema is encountered, or if deserialization of the tagged
  object fails with an exception, a raw Python data structure will be returned.
  [`#272 <https://github.com/asdf-format/asdf/issues/272>`_]

- Added option to ``AsdfFile.open`` to allow suppression of warning messages
  when mismatched schema versions are encountered. [`#294 <https://github.com/asdf-format/asdf/issues/294>`_]

- Added a diff tool to ``asdftool`` to allow for visual comparison of pairs of
  ASDF files. [`#286 <https://github.com/asdf-format/asdf/issues/286>`_]

- Added command to ``asdftool`` to display available tags. [`#303 <https://github.com/asdf-format/asdf/issues/303>`_]

- When possible, display name of ASDF file that caused version mismatch
  warning. [`#306 <https://github.com/asdf-format/asdf/issues/306>`_]

- Issue a warning when an unrecognized tag is encountered. [`#295 <https://github.com/asdf-format/asdf/issues/295>`_] This warning
  is silenced by default, but can be enabled with a parameter to the
  ``AsdfFile`` constructor, or to ``AsdfFile.open``. Also added an option for
  ignoring warnings from unrecognized schema tags. [`#319 <https://github.com/asdf-format/asdf/issues/319>`_]

- Fix bug with loading JSON schemas in Python 3.5. [`#317 <https://github.com/asdf-format/asdf/issues/317>`_]

- Remove all remnants of support for Python 2.6. [`#333 <https://github.com/asdf-format/asdf/issues/333>`_]

- Fix issues with the type index used for writing out ASDF files. This ensures
  that items in the type index are not inadvertently overwritten by later
  versions of the same type. It also makes sure that schema example tests run
  against the correct version of the ASDF standard. [`#350 <https://github.com/asdf-format/asdf/issues/350>`_]

- Update time schema to reflect changes in astropy. This fixes an outstanding
  bug. [`#343 <https://github.com/asdf-format/asdf/issues/343>`_]

- Add ``copy_arrays`` option to ``asdf.open`` to control whether or not
  underlying array data should be memory mapped, if possible. [`#355 <https://github.com/asdf-format/asdf/issues/355>`_]

- Allow the tree to be accessed using top-level ``__getitem__`` and
  ``__setitem__``. [`#352 <https://github.com/asdf-format/asdf/issues/352>`_]

1.2.1 (2016-11-07)
==================

- Make asdf conditionally dependent on the version of astropy to allow
  running it with older versions of astropy. [`#228 <https://github.com/asdf-format/asdf/issues/228>`_]

1.2.0 (2016-10-04)
==================

- Added Tabular model. [`#214 <https://github.com/asdf-format/asdf/issues/214>`_]

- Forced new blocks to be contiguous [`#221 <https://github.com/asdf-format/asdf/issues/221>`_]

- Rewrote code which tags complex objects [`#223 <https://github.com/asdf-format/asdf/issues/223>`_]

- Fixed version error message [`#224 <https://github.com/asdf-format/asdf/issues/224>`_]

1.0.5 (2016-06-28)
==================

- Fixed a memory leak when reading wcs that grew memory to over 10 Gb. [`#200 <https://github.com/asdf-format/asdf/issues/200>`_]

1.0.4 (2016-05-25)
==================

- Added wrapper class for astropy.core.Time, TaggedTime. [`#198 <https://github.com/asdf-format/asdf/issues/198>`_]


1.0.2 (2016-02-29)
==================

- Renamed package to ASDF. [`#190 <https://github.com/asdf-format/asdf/issues/190>`_]

- Stopped support for Python 2.6 [`#191 <https://github.com/asdf-format/asdf/issues/191>`_]


1.0.1 (2016-01-08)
==================

- Fixed installation from the source tarball on Python 3. [`#187 <https://github.com/asdf-format/asdf/issues/187>`_]

- Fixed error handling when opening ASDF files not supported by the current
  version of asdf. [`#178 <https://github.com/asdf-format/asdf/issues/178>`_]

- Fixed parse error that could occur sometimes when YAML data was read from
  a stream. [`#183 <https://github.com/asdf-format/asdf/issues/183>`_]


1.0.0 (2015-09-18)
==================

- Initial release.
