1.2.2 (Unreleased)
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

- Issue a warning when an unrecognized tag is encountered. [#295]

- Fix bug with loading JSON schemas in Python 3.5. [#317]

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
