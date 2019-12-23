.. currentmodule:: asdf

*******
Changes
*******

What's New in ASDF 2.5.0?
=========================

The ASDF Standard is at v1.4.0.

Changes include:

* Added convenience method for fetching the default resolver

* Fixed load_schema LRU cache memory usage issue

* Fixed bug causing segfault after update of a memory-mapped file.

What's New in ASDF 2.4.2?
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

What's New in ASDF 2.3.3?
=========================


The ASDF Standard is at v1.3.0. Changes include:

* Pass ``ignore_unrecognized_tag`` setting through to ASDF-in-FITS.

* Use ``$schema`` keyword if available to determine meta-schema to use when
  testing whether schemas themselves are valid.

* Take into account resolvers from installed extensions when loading schemas
  for validation.

* Fix compatibility issue with new release of ``pyyaml`` (version 5.1).

* Allow use of ``pathlib.Path`` objects for ``custom_schema`` option.

What's New in ASDF 2.3.1?
=========================

he ASDF Standard is at v1.3.0. Changes include:

* Provide source information for ``AsdfDeprecationWarning`` that come from
  extensions from external packages.

* Fix the way ``generic_io`` handles URIs and paths on Windows.

* Fix bug in ``asdftool`` that prevented ``extract`` command from being
  visible.

What's New in ASDF 2.3?
=======================

ASDF 2.3 reflects the update of ASDF Standard to v1.3.0, and contains a few
notable features and an API change:

* Storage of arbitrary precision integers is now provided by
  `asdf.IntegerType`. This new type is provided by version 1.3.0 of the ASDF
  Standard.

* Reading a file with integer literals that are too large now causes only a
  warning instead of a validation error. This is to provide backwards
  compatibility for files that were created with a buggy version of ASDF.

* The functions `asdf.open` and `AsdfFile.write_to` now support the use of
  `pathlib.Path`.

* The `asdf.asdftypes` module has been deprecated in favor of `asdf.types`. The
  old module will be removed entirely in the 3.0 release.

What's New in ASDF 2.2?
=======================

ASDF 2.2 contains several API changes, although backwards compatibilty is
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

What's New in ASDF 2.1?
=======================

ASDF 2.1 is a minor release, and most of the changes affect only a subset of
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

What's New in ASDF 2.0?
=======================

ASDF 2.0 is a major release that includes many improvements, new features, and
some API changes. It is the first release of the ASDF package that only
supports Python 3.

The full list of changes, including bug fixes, can be found in the
:ref:`change_log`. A brief overview of changes is provided below:

* Support for Python 2.7 has been removed entirely.

* There is no longer a hard dependency on `astropy`. It is still required for
  some features, and for running the tests. Astropy-related tag implementations
  have been moved to the Astropy package itself.
* External packages can now install and register custom ASDF extensions using
  `setuptools` entry points (see :ref:`other_packages` and
  :ref:`packaging_extensions`). ASDF detects extensions that are installed in
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
