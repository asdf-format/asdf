.. currentmodule:: asdf

*******
Changes
*******

What's new in asdf 2.11.1?
==========================

The ASDF Standard is at v1.6.0.

Changes include:

- Update minimum astropy version to 5.0.4.

What's new in asdf 2.11.0?
==========================

The ASDF Standard is at v1.6.0.

Changes include:

- Update minimum jsonschema version to 4.0.1.

What's new in asdf 2.10.1?
==========================

The ASDF Standard is at v1.6.0.

Changes include:

- Bugfix for circular build dependency for asdf.
- Fix small bug with handling multiple schema uris per tag.

What's new in asdf 2.10.0?
==========================

The ASDF Standard is at v1.6.0.

Changes include:

- Replace asdf-standard submodule with pypi package.

What's new in asdf 2.9.2?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Fix deprecation warnings stemming from the release of pytest 7.0.0.

- Fix bug in pytest plugin when schemas are not in a directory named "schemas".

What's new in asdf 2.9.1?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Fix typo in testing module ``__init__.py`` name.

What's new in asdf 2.9.0?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Added the capability for classes to expose their contents
  to AsdfFile.info and AsdfFile.search via the ``__asdf_traverse__`` method.

- Drop support for Python 3.6.

- Update setup.py to raise error if "git submodule update --init" has
  not been run.

- Add ability for tags to correspond to multiple schema_uri, with an
  implied allOf among the schema_uris.

- Add the URL of the file being parsed to ``SerializationContext``.

- Add ``asdf.testing.helpers`` module with simplified versions of test
  helpers previously available in ``asdf.tests.helpers``.

What's new in asdf 2.8.3?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Fix use of "python" instead of "python3" in compatibility tests.

What's new in asdf 2.8.2?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Fix array compression for non-native byte order.

- Fix bug in schema loading when URI is claimed by both legacy
  and new-style extensions.

- Hide 'name' and 'version' attributes on instances of
  NDArrayType.

What's new in asdf 2.8.1?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- Fix bug that corrupts ndarray views when a new block is added
  to an existing file in absence of a block index.

What's new in asdf 2.8.0?
=========================

The ASDF Standard is at v1.6.0.

Changes include:

- New plugin APIs for block compressors, extensions, and schemas.

- New global configuration mechanism (``asdf.get_config()``).

- Support for the asdf:// URI scheme.

- Drop support for Python 3.5.

- Support for ASDF Standard 1.6.0, which is available via the
  ``version`` argument to ``AsdfFile.__init__`` but not yet the
  default.

- Values that match defaults defined in schemas are no longer
  automatically removed from the ASDF tree.

- ``None`` values are no longer removed from the tree on write.

- Remove the ``asdf.test`` method and ``asdf.__githash__`` attribute.

- And more, see full changelog below for details.

What's new in asdf 2.7.5?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

- Fix bug in ``asdf.schema.check_schema`` causing relative references in
  metaschemas to be resolved incorrectly.

- Fix bug that corrupts ndarray views when a new block is added
  to an existing file in absence of a block index.

What's New in asdf 2.7.4?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

- Fix pytest plugin failure under older versions of pytest.

- Fix bugs when serializing views over non-contiguous and FITS
  base arrays.

- Add support for opening files from HTTPS URLs and following
  HTTP/HTTPS redirects.

What's New in asdf 2.7.3?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

- Fix bug resulting in invalid strides values for views over
  FITS arrays.

- Add pytest plugin options to skip and xfail individual tests
  and xfail the unsupported ndarray-1.0.0 schema example.

What's New in asdf 2.7.2?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

* Fix bug causing test collection failures under Python 3.9.

* Fix bug when decompressing arrays with numpy 1.20.

* Replace ``assert`` statements with ``raise`` at the behest
  of the bandit security linter.

What's New in asdf 2.7.1?
=========================

The ASDF Standard is at v1.5.0.

The sole change in this release:

* Fix bug preventing access to copied array data after
  an ``AsdfFile`` is closed.

What's New in asdf 2.7.0?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

* Performance improvements when reading and validating
  ASDF files.

* Numerous bug fixes.  See complete changelog below for details.

* Add option to ``asdf.open`` that disables schema validation on read.

* Improved warning messages.  All `asdf` library warnings now
  subclass ``asdf.exceptions.AsdfWarning``.

* Drop support for filling default values from subschemas
  within oneOf or anyOf combiners.

* Resolve deprecation warnings from the `asdf` pytest plugin
  when used with newer versions of pytest.

* Drop support for 2.x versions of the jsonschema package.

What's New in asdf 2.6.0?
=========================

The ASDF Standard is at v1.5.0.

Changes include:

* ASDF Standard 1.5.0 is now the default for new files.  Changes to
  the standard include several new and updated transform schemas,
  and removal of wcs schemas that were previously deprecated and
  moved to the ``gwcs`` package.

* Add ``asdf.info`` and ``AsdfFile.search`` methods for visualizing
  and interactively searching an ASDF tree.

* Fix bug causing too many bytes to be consumed when reading
  compressed blocks.

* Support validation and serialization of additional numpy
  scalar types.

* Fix serialization of trees containing implicit internal references
  and reference cycles, and simplify handling of children in
  ``ExtensionType`` subclasses.

* Fix bug preventing addition of history entires to a file that
  was initially saved without them.

* Expand developer documentation to cover the details of pyyaml
  integration and conversion between tagged trees and custom trees.

What's New in asdf 2.5.2?
=========================

The ASDF Standard is at v1.4.0.

Changes include:

* Add schemas that were previously missing from ASDF Standard 1.4.0,
  and fix a variety of minor issues in ``AsdfType`` subclasses.

* Add general and versioning-specific developer documentation.

What's New in asdf 2.5.1?
=========================

The ASDF Standard is at v1.4.0.

Changes include:

* Fix bug in test causing failure when test suite is run against
  an installed `asdf` package.

What's New in asdf 2.5.0?
=========================

The ASDF Standard is at v1.4.0.

Changes include:

* Added convenience method for fetching the default resolver

* Fixed load_schema LRU cache memory usage issue

* Fixed bug causing segfault after update of a memory-mapped file.

What's New in asdf 2.4.2?
=========================

The ASDF Standard is at v1.3.0. Changes include:

* Define the ``in`` operator for top-level ``AsdfFile`` objects.

* Automatically register schema tester plugin. Do not enable schema tests by
  default. Add configuration setting and command line option to enable schema
  tests.

* Enable handling of subclasses of known custom types by using decorators for
  convenience.

* Add support for jsonschema 3.x.

* Fix bug in ``NDArrayType.__len__``.  It must be a method, not a
  property.

What's New in asdf 2.3.3?
=========================

The ASDF Standard is at v1.3.0. Changes include:

* Pass ``ignore_unrecognized_tag`` setting through to ASDF-in-FITS.

* Use ``$schema`` keyword if available to determine meta-schema to use when
  testing whether schemas themselves are valid.

* Take into account resolvers from installed extensions when loading schemas
  for validation.

* Fix compatibility issue with new release of ``pyyaml`` (version 5.1).

* Allow use of ``pathlib.Path`` objects for ``custom_schema`` option.

What's New in asdf 2.3.1?
=========================

he ASDF Standard is at v1.3.0. Changes include:

* Provide source information for ``AsdfDeprecationWarning`` that come from
  extensions from external packages.

* Fix the way ``generic_io`` handles URIs and paths on Windows.

* Fix bug in ``asdftool`` that prevented ``extract`` command from being
  visible.

What's New in asdf 2.3?
=======================

`asdf` 2.3 reflects the update of ASDF Standard to v1.3.0, and contains a few
notable features and an API change:

* Storage of arbitrary precision integers is now provided by
  `asdf.IntegerType`. This new type is provided by version 1.3.0 of the ASDF
  Standard.

* Reading a file with integer literals that are too large now causes only a
  warning instead of a validation error. This is to provide backwards
  compatibility for files that were created with a buggy version of `asdf`.

* The functions `asdf.open` and `AsdfFile.write_to` now support the use of
  `pathlib.Path`.

* The `asdf.asdftypes` module has been deprecated in favor of `asdf.types`. The
  old module will be removed entirely in the 3.0 release.

What's New in asdf 2.2?
=======================

`asdf` 2.2 contains several API changes, although backwards compatibilty is
preserved for now. The most significant changes are:

* The function `AsdfFile.open` has been deprecated in favor of `asdf.open`.
  It will be removed entirely in the 3.0 release. More intelligent file mode
  handling has been added to `asdf.open`. Files that are opened in read-only
  mode with `asdf.open` now explicitly block writes to memory-mapped arrays.
  This may cause problems for some existing code, but any such code was
  accessing these arrays in an unsafe manner, so backwards compatibility for
  this case is not provided. The old mode handling behavior is retained for now
  in `AsdfFile.open`.

* It is now possible to disable lazy loading of internal arrays. This is useful
  when the `AsdfFile` was opened using another open file. With lazy loading, it
  is possible to close the original file but still retain access to the array
  data.

* There is a new warning `AsdfConversionWarning` that occurs when failing to
  convert nodes in the ASDF tree into custom tagged types. This makes it easier
  for users to filter specifically for this failure case.

What's New in asdf 2.1?
=======================

`asdf` 2.1 is a minor release, and most of the changes affect only a subset of
users. The most notable changes are the following:

* `namedtuple` objects can now be serialized. They are automatically converted
  into `list` objects, and therefore are not strictly able to round-trip. By
  default a warning occurs when performing this conversion, but the warning can
  be disabled by passing `ignore_implicit_conversion=True` to the `AsdfFile`
  constructor.

* Added a method `AsdfFile.get_history_entries` for getting a list of history
  entries from the tree.

* Added an option to `generic_io.get_file` to close the underlying file handle.

Please see the :ref:`change_log` for additional details.

What's New in asdf 2.0?
=======================

`asdf` 2.0 is a major release that includes many improvements, new features, and
some API changes. It is the first release of the `asdf` package that only
supports Python 3.

The full list of changes, including bug fixes, can be found in the
:ref:`change_log`. A brief overview of changes is provided below:

* Support for Python 2.7 has been removed entirely.

* There is no longer a hard dependency on `astropy`. It is still required for
  some features, and for running the tests. Astropy-related tag implementations
  have been moved to the Astropy package itself.
* External packages can now install and register custom ASDF extensions using
  `setuptools` entry points (see :ref:`other_packages` and
  :ref:`packaging_extensions`). `asdf` detects extensions that are installed in
  this way and automatically uses them when reading and writing files with
  custom types.
* A bug was fixed that now allows fully-specified tags from external packages
  to be properly resolved.
* The file format now includes metadata about the extensions that were used to
  create an ASDF file. The software automatically adds this information when
  writing an ASDF file, and will check for installed extensions when reading
  a file containing such metadata (see :ref:`extension_checking`).
* The restrictions on the top-level attributes `data`, `wcs`, and `fits` have
  been removed.
* Clients that wish to impose additional validation requirements on files can
  now provide custom top-level schemas (see :ref:`custom-schemas`).
* There is a new way to reference array data that is defined in external files
  (see :ref:`array-references`).
* Several new commands have been added to the `asdftool` command line
  interface:

  * ``extensions`` for showing information about installed extensions (see
        :ref:`other_packages`).
  * ``remove-hdu`` for removing ASDF extension from ASDF-in-FITS file
      (requires `astropy`, see :ref:`asdf-in-fits`).

* The package now cleanly supports builds in `develop` mode and can be imported
  from the source tree.

.. _change_log:

Change Log
==========

.. include:: ../../CHANGES.rst
