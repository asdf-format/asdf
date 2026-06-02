.. currentmodule:: asdf

.. _deprecations:

************
Deprecations
************

Version 3.3
===========

``asdf.util.filepath_to_url`` is deprecated. Please use ``pathlib.Path.to_uri``.

The ``ignore_implicit_conversion`` argument for ``AsdfFile`` and
``treeutil.walk_and_modify`` is deprecated. "implicit conversion" is also
deprecated. This referred to the behavior where certain types (namedtuple)
were silently (or with a warning depending on the ``ignore_implicit_conversion``
setting) converted to a list when added to an asdf tree. As these types
(namedtuple) can be supported by a ``Converter`` this "implicit conversion"
will be removed.

Version 3.1
===========

``asdf.asdf`` is deprecated. Please use the top-level ``asdf`` module for
``AsdfFile`` and ``open`` (same as ``asdf.asdf.open_asdf``).

``AsdfFile.resolve_and_inline`` is deprecated. Please use
``AsdfFile.resolve_references`` and provide ``all_array_storage='inline'`` to
``AdsfFile.write_to`` (or ``AsdfFile.update``).

Automatic calling of ``AsdfFile.find_references`` during calls to
``AsdfFile.__init__`` and ``asdf.open``. Call ``AsdfFile.find_references`` to
find references.

Several deprecations were added to ``AsdfFile`` methods that validate the
tree. In a future version of asdf these methods will not perform any tree
validation (please call ``AsdfFile.validate`` to validate the tree).
As this behavior is difficult to deprecate (without triggering warnings
for every call of the method) an ``AsdfDeprecationWarning`` will only
be issued on a failed validation during the following methods:

* ``AsdfFile.tree`` assignment
* ``AsdfFile.resolve_references``
* ``AsdfFile.__init__`` (when the ``tree`` argument is provided)

Providing ``kwargs`` to ``AsdfFile.resolve_references`` does nothing and is deprecated.

Version 3.0
===========

The following functions in ``asdf.util`` are deprecated:

* ``human_list`` this is no longer part of the public API
* ``resolve_name`` see ``astropy.utils.resolve_name``
* ``minversion`` see ``astropy.utils.minversion``
* ``iter_subclasses`` this is no longer part of the public API

Version 3.0
===========

SerializationContext was previously importable from ``asdf.asdf.SerializationContext``.
Although not part of the public API, this import path has been deprecated and users
should instead import ``SerializationContext`` from `asdf.extension`.

Version 2.15
============

ASDF 2.15 introduced many new `asdf.exceptions.AsdfDeprecationWarning` messages. These
warnings are subclasses of the built-in python `DeprecationWarning` and will by
default be ignored except in `__main__` and with testing tools such as
:ref:`pytest <pytest:deprecation-warnings>`.

These are intended to highlight use of features that we will likely remove in the next
major version of ASDF (see our :ref:`release_and_support` for more details about our
versioning, compatibility and support policy).

.. _legacy_extension_api_deprecation:

Legacy Extension API Deprecation
--------------------------------

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
------------------------

Support for ``AsdfInFits`` (including the ``asdf.fits_embed`` module) is
deprecated. Code using this format can migrate to using `stdatamodels` which
contains functions to read and write AsdfInFits files
(see :external+stdatamodels:doc:`asdf_in_fits` for migration information).

Without support for ``fits_embed.AsdfInFits`` the ``extract`` and
``remove-hdu`` commands for :ref:`asdftool <asdf_tool>` are no longer usable and are
deprecated.

.. _tests_helpers_deprecation:

asdf.tests.helpers Deprecation
------------------------------

Use of ``asdf.tests.helpers`` is deprecated. Please see `asdf.testing.helpers`
for alternative functions to aid in testing.
