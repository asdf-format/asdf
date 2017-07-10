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
