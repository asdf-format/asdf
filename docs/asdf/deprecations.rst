.. currentmodule:: asdf

.. _deprecations:

************
Deprecations
************

ASDF 2.15 introduced many new `asdf.exceptions.AsdfDeprecationWarning` messages. These
warnings are subclasses of the built-in python `DeprecationWarning` and will by
default be ignored except in `__main__` and with testing tools such as
:ref:`pytest <pytest:deprecation-warnings>`.

These are intended to highlight use of features that we will likely remove in the next
major version of ASDF (see our :ref:`release_and_support` for more details about our
versioning, compatibility and support policy).

.. _legacy_extension_api_deprecation:

Legacy Extension API Deprecation
================================

A large number of `asdf.exceptions.AsdfDeprecationWarning` messages appear related to
use of the ``legacy extension api``. Some examples include:

* ``asdf.types``
* ``asdf.types.CustomType``
* ``asdf.type_index``
* ``asdf.resolver``
* the ``asdf_extensions`` entry point
* portions of asdf.extension including:

  * ``asdf.extension.AsdfExtension``
  * ``asdf.extension.AsdfExtensionList``
  * ``asdf.extension.BuiltinExtension``
  * ``asdf.extension.default_extensions``
  * ``asdf.extension.get_cached_asdf_extensions``
  * ``asdf.extension.get_default_resolver``

* attributes to asdf.AsdfFile including:

  * ``asdf.AsdfFile.run_hook``
  * ``asdf.AsdfFile.run_modifying_hook``
  * ``asdf.AsdfFile.url_mapping``
  * ``asdf.AsdfFile.tag_mapping``
  * ``asdf.AsdfFile.type_index``
  * ``asdf.AsdfFile.resolver``
  * ``asdf.AsdfFile.extension_list``

This deprecated api is replaced by new-style :ref:`converters <extending_converters>`,
:ref:`extensions <extending_extensions>` and :ref:`validators <extending_validators>`.
`asdf-astropy <https://asdf-astropy.readthedocs.io/en/latest/>`_ is a useful example
package that uses these new-style extension api.

.. _asdf_in_fits_deprecation:

ASDF-in-FITS Deprecation
========================

Support for ``AsdfInFits`` (including the ``asdf.fits_embed`` module) is
deprecated. Code using this format can migrate to using `stdatamodels` which
contains functions to read and write AsdfInFits files
(see :external+stdatamodels:doc:`asdf_in_fits` for migration information).

Without support for ``fits_embed.AsdfInFits`` the ``extract`` and
``remove-hdu`` commands for :ref:`asdftool <asdf_tool>` are no longer usable and are
deprecated.

.. _tests_helpers_deprecation:

asdf.tests.helpers Deprecation
==============================

Use of ``asdf.tests.helpers`` is deprecated. Please see `asdf.testing.helpers`
for alternative functions to aid in testing.
