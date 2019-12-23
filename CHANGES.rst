2.5.0 (2019-12-23)
------------------

- Added asdf-standard 1.4.0 to the list of supported versions. [#704]
- Fix load_schema LRU cache memory usage issue [#682]
- Add convenience method for fetching the default resolver [#682]

- ``SpecItem`` and ``Spec`` were depreicated  in ``semantic_version``
  and were replaced with ``SimpleSpec``. [#715]

- Pinned the minimum required ``semantic_version`` to 2.8. [#715]

- Fix bug causing segfault after update of a memory-mapped file. [#716]

2.4.2 (2019-08-29)
------------------

- Limit the version of ``semantic_version`` to <=2.6.0 to work
  around a Deprecation warning. [#700]

2.4.1 (2019-08-27)
------------------

- Define the ``in`` operator for top-level ``AsdfFile`` objects. [#623]

- Overhaul packaging infrastructure. Remove use of ``astropy_helpers``. [#670]

- Automatically register schema tester plugin. Do not enable schema tests by
  default. Add configuration setting and command line option to enable schema
  tests. [#676]

- Enable handling of subclasses of known custom types by using decorators for
  convenience. [#563]

- Add support for jsonschema 3.x. [#684]

2.3.4 (unreleased)
------------------

- Fix bug in ``NDArrayType.__len__``.  It must be a method, not a
  property. [#673]

2.3.3 (2019-04-02)
------------------

- Pass ``ignore_unrecognized_tag`` setting through to ASDF-in-FITS. [#650]

- Use ``$schema`` keyword if available to determine meta-schema to use when
  testing whether schemas themselves are valid. [#654]

- Take into account resolvers from installed extensions when loading schemas
  for validation. [#655]

- Fix compatibility issue with new release of ``pyyaml`` (version 5.1). [#662]

- Allow use of ``pathlib.Path`` objects for ``custom_schema`` option. [#663]

2.3.2 (2019-02-19)
------------------

- Fix bug that occurs when comparing installed extension version with that
  found in file. [#641]

2.3.1 (2018-12-20)
------------------

- Provide source information for ``AsdfDeprecationWarning`` that come from
  extensions from external packages. [#629]

- Ensure that top-level accesses to the tree outside a closed context handler
  result in an ``OSError``. [#628]

- Fix the way ``generic_io`` handles URIs and paths on Windows. [#632]

- Fix bug in ``asdftool`` that prevented ``extract`` command from being
  visible. [#633]

2.3.0 (2018-11-28)
------------------

- Storage of arbitrary precision integers is now provided by
  ``asdf.IntegerType``.  Reading a file with integer literals that are too
  large now causes only a warning instead of a validation error. This is to
  provide backwards compatibility for files that were created with a buggy
  version of ASDF (see #553 below). [#566]

- Remove WCS tags. These are now provided by the `gwcs package
  <https://github.com/spacetelescope/gwcs>`_. [#593]

- Deprecate the ``asdf.asdftypes`` module in favor of ``asdf.types``. [#611]

- Support use of ``pathlib.Path`` with ``asdf.open`` and ``AsdfFile.write_to``.
  [#617]

- Update ASDF Standard submodule to version 1.3.0.

2.2.1 (2018-11-15)
------------------

- Fix an issue with the README that caused sporadic installation failures and
  also prevented the long description from being rendered on pypi. [#607]

2.2.0 (2018-11-14)
------------------

- Add new parameter ``lazy_load`` to ``AsdfFile.open``. It is ``True`` by
  default and preserves the default behavior. ``False`` detaches the
  loaded tree from the underlying file: all blocks are fully read and
  numpy arrays are materialized. Thus it becomes safe to close the file
  and continue using ``AsdfFile.tree``. However, ``copy_arrays`` parameter
  is still effective and the active memory maps may still require the file
  to stay open in case ``copy_arrays`` is ``False``. [#573]

- Add ``AsdfConversionWarning`` for failures to convert ASDF tree into custom
  types. This warning is converted to an error when using
  ``assert_roundtrip_tree`` for tests. [#583]

- Deprecate ``asdf.AsdfFile.open`` in favor of ``asdf.open``. [#579]

- Add readonly protection to memory mapped arrays when the underlying file
  handle is readonly. [#579]

2.1.2 (2018-11-13)
------------------

- Make sure that all types corresponding to core tags are added to the type
  index before any others. This fixes a bug that was related to the way that
  subclass tags were overwritten by external extensions. [#598]

2.1.1 (2018-11-01)
------------------

- Make sure extension metadata is written even when constructing the ASDF tree
  on-the-fly. [#549]

- Fix large integer validation when storing `numpy` integer literals in the
  tree. [#553]

- Fix bug that caused subclass of external type to be serialized by the wrong
  tag. [#560]

- Fix bug that occurred when attempting to open invalid file but Astropy import
  fails while checking for ASDF-in-FITS. [#562]

- Fix bug that caused tree creation to fail when unable to locate a schema file
  for an unknown tag. This now simply causes a warning, and the offending node
  is converted to basic Python data structures. [#571]

2.1.0 (2018-09-25)
------------------

- Add API function for retrieving history entries. [#501]

- Store ASDF-in-FITS data inside a 1x1 BINTABLE HDU. [#519]

- Allow implicit conversion of ``namedtuple`` into serializable types. [#534]

- Fix bug that prevented use of ASDF-in-FITS with HDUs that have names with
  underscores. [#543]

- Add option to ``generic_io.get_file`` to close underlying file handle. [#544]

- Add top-level ``keys`` method to ``AsdfFile`` to access tree keys. [#545]

2.0.3 (2018-09-06)
------------------

- Update asdf-standard to reflect more stringent (and, consequently, more
  correct) requirements on the formatting of complex numbers. [#526]

- Fix bug with dangling file handle when using ASDF-in-FITS. [#533]

- Fix bug that prevented fortran-order arrays from being serialized properly.
  [#539]

2.0.2 (2018-07-27)
------------------

- Allow serialization of broadcasted ``numpy`` arrays. [#507]

- Fix bug that caused result of ``set_array_compression`` to be overwritten by
  ``all_array_compression`` argument to ``write_to``. [#510]

- Add workaround for Python OSX write limit bug
  (see https://bugs.python.org/issue24658). [#521]

- Fix bug with custom schema validation when using out-of-line definitions in
  schema file. [#522]

2.0.1 (2018-05-08)
------------------

- Allow test suite to run even when package is not installed. [#502]

2.0.0 (2018-04-19)
------------------

- Astropy-specific tags have moved to Astropy core package. [#359]

- ICRSCoord tag has moved to Astropy core package. [#401]

- Remove support for Python 2. [#409]

- Create ``pytest`` plugin to be used for testing schema files. [#425]

- Add metadata about extensions used to create a file to the history section of
  the file itself. [#475]

- Remove hard dependency on Astropy. It is still required for testing, and for
  processing ASDF-in-FITS files. [#476]

- Add command for extracting ASDF extension from ASDF-in-FITS file and
  converting it to a pure ASDF file. [#477]

- Add command for removing ASDF extension from ASDF-in-FITS file. [#480]

- Add an ``ExternalArrayReference`` type for referencing arrays in external
  files. [#400]

- Improve the way URIs are detected for ASDF-in-FITS files in order to fix bug
  with reading gzipped ASDF-in-FITS files. [#416]

- Explicitly disallow access to entire tree for ASDF file objects that have
  been closed. [#407]

- Install and load extensions using ``setuptools`` entry points. [#384]

- Automatically initialize ``asdf-standard`` submodule in ``setup.py``. [#398]

- Allow foreign tags to be resolved in schemas and files. Deprecate
  ``tag_to_schema_resolver`` property for ``AsdfFile`` and
  ``AsdfExtensionList``. [#399]

- Fix bug that caused serialized FITS tables to be duplicated in embedded ASDF
  HDU. [#411]

- Create and use a new non-standard FITS extension instead of ImageHDU for
  storing ASDF files embedded in FITS. Explicitly remove support for the
  ``.update`` method of ``AsdfInFits``, even though it didn't appear to be
  working previously. [#412]

- Allow package to be imported and used from source directory and builds in
  development mode. [#420]

- Add command to ``asdftool`` for querying installed extensions. [#418]

- Implement optional top-level validation pass using custom schema. This can be
  used to ensure that particular ASDF files follow custom conventions beyond
  those enforced by the standard. [#442]

- Remove restrictions affecting top-level attributes ``data``, ``wcs``, and
  ``fits``. Bump top-level ASDF schema version to v1.1.0. [#444]

1.3.3 (2018-03-01)
------------------

- Update test infrastructure to rely on new Astropy v3.0 plugins. [#461]

- Disable use of 2to3. This was causing test failures on Debian builds. [#463]

1.3.2 (2018-02-22)
------------------

- Updates to allow this version of ASDF to be compatible with Astropy v3.0.
  [#450]

- Remove tests that are no longer relevant due to latest updates to Astropy's
  testing infrastructure. [#458]

1.3.1 (2017-11-02)
------------------

- Relax requirement on ``semantic_version`` version to 2.3.1. [#361]

- Fix bug when retrieving file format version from new ASDF file. [#365]

- Fix bug when duplicating inline arrays. [#370]

- Allow tag references using the tag URI scheme to be resolved in schema files.
  [#371]

1.3.0 (2017-10-24)
------------------

- Fixed a bug in reading data from an "http:" url. [#231]

- Implements v 1.1.0 of the asdf schemas. [#233]

- Added a function ``is_asdf_file`` which inspects the input and
  returns ``True`` or ``False``. [#239]

- The ``open`` method of ``AsdfInFits`` now accepts URIs and open file handles
  in addition to HDULists. The ``open`` method of ``AsdfFile`` will now try to
  parse the given URI or file handle as ``AsdfInFits`` if it is not obviously a
  regular ASDF file. [#241]

- Updated WCS frame fields ``obsgeoloc`` and ``obsgeovel`` to reflect recent
  updates in ``astropy`` that changed representation from ``Quantity`` to
  ``CartesianRepresentation``. Updated to reflect ``astropy`` change that
  combines ``galcen_ra`` and ``galcen_dec`` into ``galcen_coord``. Added
  support for new field ``galcen_v_sun``. Added support for required module
  versions for tag classes. [#244]

- Added support for ``lz4`` compression algorithm [#258]. Also added support
  for using a different compression algorithm for writing out a file than the
  one that was used for reading the file (e.g. to convert blocks to use a
  different compression algorithm) [#257]

- Tag classes may now use an optional ``supported_versions`` attribute to
  declare exclusive support for particular versions of the corresponding
  schema. If this attribute is omitted (as it is for most existing tag
  classes), the tag is assumed to be compatible with all versions of the
  corresponding schema. If ``supported_versions`` is provided, the tag class
  implementation can include code that is conditioned on the schema version. If
  an incompatible schema is encountered, or if deserialization of the tagged
  object fails with an exception, a raw Python data structure will be returned.
  [#272]

- Added option to ``AsdfFile.open`` to allow suppression of warning messages
  when mismatched schema versions are encountered. [#294]

- Added a diff tool to ``asdftool`` to allow for visual comparison of pairs of
  ASDF files. [#286]

- Added command to ``asdftool`` to display available tags. [#303]

- When possible, display name of ASDF file that caused version mismatch
  warning. [#306]

- Issue a warning when an unrecognized tag is encountered. [#295] This warning
  is silenced by default, but can be enabled with a parameter to the
  ``AsdfFile`` constructor, or to ``AsdfFile.open``. Also added an option for
  ignoring warnings from unrecognized schema tags. [#319]

- Fix bug with loading JSON schemas in Python 3.5. [#317]

- Remove all remnants of support for Python 2.6. [#333]

- Fix issues with the type index used for writing out ASDF files. This ensures
  that items in the type index are not inadvertently overwritten by later
  versions of the same type. It also makes sure that schema example tests run
  against the correct version of the ASDF standard. [#350]

- Update time schema to reflect changes in astropy. This fixes an outstanding
  bug. [#343]

- Add ``copy_arrays`` option to ``asdf.open`` to control whether or not
  underlying array data should be memory mapped, if possible. [#355]

- Allow the tree to be accessed using top-level ``__getitem__`` and
  ``__setitem__``. [#352]

1.2.1(2016-11-07)
-----------------

- Make asdf conditionally dependent on the version of astropy to allow
  running it with older versions of astropy. [#228]

1.2.0(2016-10-04)
-----------------

- Added Tabular model. [#214]

- Forced new blocks to be contiguous [#221]

- Rewrote code which tags complex objects [#223]

- Fixed version error message [#224]

1.0.5 (2016-06-28)
------------------

- Fixed a memory leak when reading wcs that grew memory to over 10 Gb. [#200]

1.0.4 (2016-05-25)
------------------

- Added wrapper class for astropy.core.Time, TaggedTime. [#198]


1.0.2 (2016-02-29)
------------------

- Renamed package to ASDF. [#190]

- Stopped support for Python 2.6 [#191]


1.0.1 (2016-01-08)
------------------

- Fixed installation from the source tarball on Python 3. [#187]

- Fixed error handling when opening ASDF files not supported by the current
  version of asdf. [#178]

- Fixed parse error that could occur sometimes when YAML data was read from
  a stream. [#183]


1.0.0 (2015-09-18)
------------------

- Initial release.
