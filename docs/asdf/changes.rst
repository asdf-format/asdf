*******
Changes
*******

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
