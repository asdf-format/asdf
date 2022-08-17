2.12.1 (2022-08-17)
-------------------

The ASDF Standard is at v1.6.0

- Overhaul of the ASDF documentation to make it more consistent and readable. [#1142, #1152]
- Update deprecated instances of `abstractproperty` to `abstractmethod` [#1148]
- Move build configuration into `pyproject.toml` [#1149, #1155]
- Pin ``jsonschema`` to below `4.10.0`. [#1171]

2.12.0 (2022-06-06)
-------------------

The ASDF Standard is at v1.6.0

- Added ability to display title as a comment in using the
  ``info()`` functionality. [#1138]
- Add ability to set asdf-standard version for schema example items. [#1143]

2.11.1 (2022-04-15)
-------------------

The ASDF Standard is at v1.6.0

- Update minimum astropy version to 5.0.4. [#1133]

2.11.0 (2022-03-15)
-------------------

The ASDF Standard is at v1.6.0

- Update minimum jsonschema version to 4.0.1. [#1105]

2.10.1 (2022-03-02)
-------------------

The ASDF Standard is at v1.6.0

- Bugfix for circular build dependency for asdf. [#1094]

- Fix small bug with handling multiple schema uris per tag. [#1095]

2.10.0 (2022-02-17)
-------------------

The ASDF Standard is at v1.6.0

- Replace asdf-standard submodule with pypi package. [#1079]

2.9.2 (2022-02-07)
------------------

The ASDF Standard is at v1.6.0

- Fix deprecation warnings stemming from the release of pytest 7.0.0. [#1075]

- Fix bug in pytest plugin when schemas are not in a directory named "schemas". [#1076]

2.9.1 (2022-02-03)
------------------

The ASDF Standard is at v1.6.0

- Fix typo in testing module ``__init__.py`` name. [#1071]

2.9.0 (2022-02-02)
------------------

The ASDF Standard is at v1.6.0

- Added the capability for tag classes to provide an interface
  to asdf info functionality to obtain information about the
  class attributes rather than appear as an opaque class object.
  [#1052 #1055]

- Fix tag listing when extension is not fully implemented. [#1034]

- Drop support for Python 3.6. [#1054]

- Adjustments to compression plugin tests and documentation. [#1053]

- Update setup.py to raise error if "git submodule update --init" has
  not been run. [#1057]

- Add ability for tags to correspond to multiple schema_uri, with an
  implied allOf among the schema_uris. [#1058, #1069]

- Add the URL of the file being parsed to ``SerializationContext``. [#1065]

- Add ``asdf.testing.helpers`` module with simplified versions of test
  helpers previously available in ``asdf.tests.helpers``. [#1067]

2.8.3 (2021-12-13)
------------------

The ASDF Standard is at v1.6.0

- Fix more use of 'python' where 'python3' is intended. [#1033]

2.8.2 (2021-12-06)
------------------

The ASDF Standard is at v1.6.0

- Update documentation to reflect new 2.8 features. [#998]

- Fix array compression for non-native byte order [#1010]

- Fix use of 'python' where 'python3' is intended. [#1026]

- Fix schema URI resolving when the URI prefix is also
  claimed by a legacy extension. [#1029]

- Remove 'name' and 'version' attributes from NDArrayType
  instances. [#1031]

2.8.1 (2021-06-09)
------------------

- Fix bug in block manager when a new block is added to an existing
  file without a block index. [#1000]

2.8.0 (2021-05-12)
------------------

The ASDF Standard is at v1.6.0

- Add ``yaml_tag_handles`` property to allow definition of custom yaml
  ``%TAG`` handles in the asdf file header. [#963]

- Add new resource mapping API for extending asdf with additional
  schemas. [#819, #828, #843, #846]

- Add global configuration mechanism. [#819, #839, #844, #847]

- Drop support for automatic serialization of subclass
  attributes. [#825]

- Support asdf:// as a URI scheme. [#854, #855]

- Include only extensions used during serialization in
  a file's metadata. [#848, #864]

- Drop support for Python 3.5. [#856]

- Add new extension API to support versioned extensions.
  [#850, #851, #853, #857, #874]

- Permit wildcard in tag validator URIs. [#858, #865]

- Implement support for ASDF Standard 1.6.0.  This version of
  the standard limits mapping keys to string, integer, or
  boolean. [#866]

- Stop removing schema defaults for all ASDF Standard versions,
  and automatically fill defaults only for versions <= 1.5.0. [#860]

- Stop removing keys with ``None`` values from the tree on write.  This
  fixes a long-standing issue where the tree structure is not preserved
  on write, but will break ``ExtensionType`` subclasses that depend on
  this behavior.  Extension developers will need to modify their
  ``to_tree`` methods to check for ``None`` before adding a key to
  the tree (or modify the schema to permit nulls, if that is the
  intention). [#863]

- Deprecated the ``auto_inline`` argument to ``AsdfFile.write_to`` and
  ``AsdfFile.update`` and added ``AsdfConfig.array_inline_threshold``. [#882, #991]

- Add ``edit`` subcommand to asdftool for efficient editing of
  the YAML portion of an ASDF file.  [#873, #922]

- Increase limit on integer literals to signed 64-bit. [#894]

- Remove the ``asdf.test`` method and ``asdf.__githash__`` attribute. [#943]

- Add support for custom compression via extensions. [#931]

- Remove unnecessary ``.tree`` from search result paths. [#954]

- Drop support for bugs in older operating systems and Python versions. [#955]

- Add argument to ``asdftool diff`` that ignores tree nodes that match
  a JMESPath expression. [#956]

- Fix behavior of ``exception`` argument to ``GenericFile.seek_until``. [#980]

- Fix issues in file type detection to allow non-seekable input and
  filenames without recognizable extensions.  Remove the ``asdf.asdf.is_asdf_file``
  function. [#978]

- Update ``asdftool extensions`` and ``asdftool tags`` to incorporate
  the new extension API. [#988]

- Add ``AsdfSearchResult.replace`` method for assigning new values to
  search results. [#981]

- Search for block index starting from end of file. Fixes rare bug when
  a data block contains a block index. [#990]

- Update asdf-standard to 1.6.0 tag. [#993]

2.7.5 (2021-06-09)
------------------

The ASDF Standard is at v1.5.0

- Fix bug in ``asdf.schema.check_schema`` causing relative references in
  metaschemas to be resolved incorrectly. [#987]

- Fix bug in block manager when a new block is added to an existing
  file without a block index. [#1000]

2.7.4 (2021-04-30)
------------------

The ASDF Standard is at v1.5.0

- Fix pytest plugin failure under older versions of pytest. [#934]

- Copy array views when the base array is non-contiguous. [#949]

- Prohibit views over FITS arrays that change dtype. [#952]

- Add support for HTTPS URLs and following redirects. [#971]

- Prevent astropy warnings in tests when opening known bad files. [#977]

2.7.3 (2021-02-25)
------------------

The ASDF Standard is at v1.5.0

- Add pytest plugin options to skip and xfail individual tests
  and xfail the unsupported ndarray-1.0.0 example. [#929]

- Fix bug resulting in invalid strides values for views over
  FITS arrays. [#930]

2.7.2 (2021-01-15)
------------------

The ASDF Standard is at v1.5.0

- Fix bug causing test collection failures in some environments. [#889]

- Fix bug when decompressing arrays with numpy 1.20.  [#901, #909]

2.7.1 (2020-08-18)
------------------

The ASDF Standard is at v1.5.0

- Fix bug preventing access to copied array data after
  ``AsdfFile`` is closed. [#869]

2.7.0 (2020-07-23)
------------------

The ASDF Standard is at v1.5.0

- Fix bug preventing diff of files containing ndarray-1.0.0
  objects in simplified form. [#786]

- Fix bug causing duplicate elements to appear when calling
  ``copy.deepcopy`` on a ``TaggedList``. [#788]

- Improve validator performance by skipping unnecessary step of
  copying schema objects. [#784]

- Fix bug with ``auto_inline`` option where inline blocks
  are not converted to internal when they exceed the threshold. [#802]

- Fix misinterpretation of byte order of blocks stored
  in FITS files. [#810]

- Improve read performance by skipping unnecessary rebuild
  of tagged tree. [#787]

- Add option to ``asdf.open`` and ``fits_embed.AsdfInFits.open``
  that disables validation on read. [#792]

- Fix bugs and code style found by adding F and W ``flake8`` checks. [#797]

- Eliminate warnings in pytest plugin by using ``from_parent``
  when available. [#799]

- Prevent validation of empty tree when ``AsdfFile`` is
  initialized. [#794]

- All warnings now subclass ``asdf.exceptions.AsdfWarning``. [#804]

- Improve warning message when falling back to an older schema,
  and note that fallback behavior will be removed in 3.0. [#806]

- Drop support for jsonschema 2.x. [#807]

- Stop traversing oneOf and anyOf combiners when filling
  or removing default values. [#811]

- Fix bug in version map caching that caused incompatible
  tags to be written under ASDF Standard 1.0.0. [#821]

- Fix bug that corrupted ndarrays when the underlying block
  array was converted to C order on write. [#827]

- Fix bug that produced unreadable ASDF files when an
  ndarray in the tree was both offset and broadcasted. [#827]

- Fix bug preventing validation of default values in
  ``schema.check_schema``. [#785]

- Add option to disable validation of schema default values
  in the pytest plugin. [#831]

- Prevent errors when extension metadata contains additional
  properties. [#832]

2.6.0 (2020-04-22)
------------------

The ASDF Standard is at v1.5.0

- AsdfDeprecationWarning now subclasses DeprecationWarning. [#710]

- Resolve external references in custom schemas, and deprecate
  asdf.schema.load_custom_schema.  [#738]

- Add ``asdf.info`` for displaying a summary of a tree, and
  ``AsdfFile.search`` for searching a tree. [#736]

- Add pytest plugin option to skip warning when a tag is
  unrecognized. [#771]

- Fix generic_io ``read_blocks()`` reading past the requested size [#773]

- Add support for ASDF Standard 1.5.0, which includes several new
  transform schemas. [#776]

- Enable validation and serialization of previously unhandled numpy
  scalar types. [#778]

- Fix handling of trees containing implicit internal references and
  reference cycles.  Eliminate need to call ``yamlutil.custom_tree_to_tagged_tree``
  and ``yamlutil.tagged_tree_to_custom_tree`` from extension code,
  and allow ``ExtensionType`` subclasses to return generators. [#777]

- Fix bug preventing history entries when a file was previously
  saved without them. [#779]

- Update developer overview documentation to describe design of changes
  to handle internal references and reference cycles. [#781]

2.5.2 (2020-02-28)
------------------

The ASDF Standard is at v1.4.0

- Add a developer overview document to help understand how ASDF works
  internally. Still a work in progress. [#730]

- Remove unnecessary dependency on six. [#739]

- Add developer documentation on schema versioning, additional
  schema and extension-related tests, and fix a variety of
  issues in ``AsdfType`` subclasses. [#750]

- Update asdf-standard to include schemas that were previously
  missing from 1.4.0 version maps.  [#767]

- Simplify example in README.rst [#763]

2.5.1 (2020-01-07)
------------------

The ASDF Standard is at v1.4.0

- Fix bug in test causing failure when test suite is run against
  an installed asdf package. [#732]

2.5.0 (2019-12-23)
------------------

The ASDF Standard is at v1.4.0

- Added asdf-standard 1.4.0 to the list of supported versions. [#704]
- Fix load_schema LRU cache memory usage issue [#682]
- Add convenience method for fetching the default resolver [#682]

- ``SpecItem`` and ``Spec`` were deprecated  in ``semantic_version``
  and were replaced with ``SimpleSpec``. [#715]

- Pinned the minimum required ``semantic_version`` to 2.8. [#715]

- Fix bug causing segfault after update of a memory-mapped file. [#716]

2.4.2 (2019-08-29)
------------------

The ASDF Standard is at v1.3.0

- Limit the version of ``semantic_version`` to <=2.6.0 to work
  around a Deprecation warning. [#700]

2.4.1 (2019-08-27)
------------------

The ASDF Standard is at v1.3.0

- Define the ``in`` operator for top-level ``AsdfFile`` objects. [#623]

- Overhaul packaging infrastructure. Remove use of ``astropy_helpers``. [#670]

- Automatically register schema tester plugin. Do not enable schema tests by
  default. Add configuration setting and command line option to enable schema
  tests. [#676]

- Enable handling of subclasses of known custom types by using decorators for
  convenience. [#563]

- Add support for jsonschema 3.x. [#684]

- Fix bug in ``NDArrayType.__len__``.  It must be a method, not a
  property. [#673]

2.3.3 (2019-04-02)
------------------

The ASDF Standard is at v1.3.0

- Pass ``ignore_unrecognized_tag`` setting through to ASDF-in-FITS. [#650]

- Use ``$schema`` keyword if available to determine meta-schema to use when
  testing whether schemas themselves are valid. [#654]

- Take into account resolvers from installed extensions when loading schemas
  for validation. [#655]

- Fix compatibility issue with new release of ``pyyaml`` (version 5.1). [#662]

- Allow use of ``pathlib.Path`` objects for ``custom_schema`` option. [#663]

2.3.2 (2019-02-19)
------------------

The ASDF Standard is at v1.3.0

- Fix bug that occurs when comparing installed extension version with that
  found in file. [#641]

2.3.1 (2018-12-20)
------------------

The ASDF Standard is at v1.3.0

- Provide source information for ``AsdfDeprecationWarning`` that come from
  extensions from external packages. [#629]

- Ensure that top-level accesses to the tree outside a closed context handler
  result in an ``OSError``. [#628]

- Fix the way ``generic_io`` handles URIs and paths on Windows. [#632]

- Fix bug in ``asdftool`` that prevented ``extract`` command from being
  visible. [#633]

2.3.0 (2018-11-28)
------------------

The ASDF Standard is at v1.3.0

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
