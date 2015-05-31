This file keeps track of changes between tagged versions of the Astropy
package template, for the benefit of affiliated package maintainers. It can
be removed in affiliated packages.

The changes below indicate what file the change was made in so that these can
be copied over manually if desired.

1.0 (2015-05-31)
----------------

- The instructions for the documentation have now been clarified to indicate
  that packages do not *have* to include the documentation in a sub-folder of
  ``docs`` (see updated note in ``docs/index.rst``). [#123]

- Updated ``setup.cfg`` to enable ``doctest_plus`` by default.

- Updated ``.travis.yml`` to:

  - Update apt-get package list

  - Add ``jinja2`` as a dependency to be installed with conda [#114]

  - Drop Python 3.2 testing [#114]

  - Drop Numpy 1.5 testing, and use Numpy 1.9 as a baseline [#114]

- Updated ``MANIFEST.in`` to:

  - Recursively include *.pyx, *.c, and *.pxd files

  - Globally exclude *.pyc and *.o files
  
  - Include ``CHANGES.rst``
  
- Update ``docs/conf.py`` to import Sphinx extensions from
  ``astropy_helpers`` instead of ``astropy``. [#119]

- Added 'Powered by Astropy badge' to ``README.rst``. [#112]

- Show how to add and remove packages from pytest header in
  ``packagename/conftest.py``, and show how to show the package version
  instead of the astropy version in the top line.

- Minor documentation change in ``packagename/_astropy_init.py``. [#110]

- Use setuptools entry_points for command line scripts (change in
  ``setup.py``). [#116]

- Updated ``astropy-helpers`` and ``ah_bootstrap.py`` to v1.0.2.

- Remove requires and provides from setup.py. [#128]

0.4.1 (2014-10-22)
------------------

- Changed order of exclusion in MANIFEST.in, excluding *.pyc *after* including
  astropy-template

- Updated astropy-helpers to v0.4.3

0.4 (2014-08-14)
----------------

- Initial tagged version, contains astropy-helpers v0.4.1
