.. currentmodule:: asdf

.. _whats_new:

**********
What's New
**********

.. _whats_new_3.0.0:

3.0.0
=====

Asdf 3.0.0 is the first major asdf release since 2018.

Thank you to all the
`contributors <https://github.com/asdf-format/asdf/graphs/contributors>`_!

.. _whats_new_3.0.0_removed:

Removed features
----------------

The following deprecated features are removed in asdf 3.0.0:

* :ref:`AsdfInFits <asdf_in_fits_deprecation>`
* :ref:`Legacy Extensions <legacy_extension_api_deprecation>`

Please see the links above or the :ref:`deprecations` for more details.

.. _whats_new_3.0.0__ew_features:

New features
------------

As asdf now only supports new-style :ref:`extensions <extending_extensions>` several
new features were added to allow these extensions to retain all the
functionality of the now removed type system.

Converters can now :ref:`defer <extending_converters_deferral>` conversion allowing
a different converter to handle serailizing an object. This is useful if a
subclass instance can be safely converted to a superclass during serialization.
See :ref:`extending_converters_deferral` for an example and more information.

Converters can now access :ref:`ASDF block storage <extending_converter_block_storage>`.
during serialization and deserialization. See :ref:`extending_converter_block_storage`
for examples and more information.

Converters have always been "strict" about tag version mismatches
(returning 'raw' objects if a specific tag version is not supported). This
"strictness" now extends to all objects handled by asdf. As all known asdf
extensions have already migrated to converters this should pose no issue
for users. Please `open an issue <https://github.com/asdf-format/asdf/issues>`_
if you run into any difficulty.

.. whats_new_3.0.0_internal:

Internal changes
----------------

2.15.1 included internally a version of jsonschema. See the
:ref:`jsonschema <whats_new_2.15.1_jsonschema>` sub-section of the
:ref:`2.15.1 <whats_new_2.15.1>` section for more details. Asdf 3.0.0 drops
jsonschema as a dependency. If your software requires jsonschema be sure to add
it to your dependencies.

To accomplish the above improvements to asdf extensions, a major rewrite of
the ASDF block management code was required. During this rewrite
``AsdfBlockIndexWarning`` was added which users will see if they open an ASDF
file with an invalid block index. Re-saving the file (or removing the
optional block index) is often sufficient to fix the file so it no longer
issues the warning when opened.

.. whats_new_3.0.0_upcoming:

Upcoming changes
----------------

With the release of asdf 3.0.0 the developers are beginning work on 3.1.0 and
4.0.0. One major change being considered for asdf 4.0.0 is the disabling of
memory mapping as the default option when as ASDF file is opened. Memory
mapping can offer significant performance gains but also increases the chance
for gnarly errors like segfaults and corrupt data. Please let us know if
this change would impact your use of asdf in the newly opened
`asdf discussions <https://github.com/asdf-format/asdf/discussions>`_

In an attempt to construct a coherent api, asdf 3.1 (and additional minor
versions) will likely contain new deprecations in an effort to reorganize
and clean up the api. If you are using features that are not currently listed
in the :ref:`user_api` or :ref:`developer_api` documentation please open an issue. This will help
us to know what functions should be preserved, what requires a deprecation
prior to removal and which of our un-documented (non-public) features can
be removed without a deprecation.


.. _whats_new_2.15.1:

2.15.1
======

.. _whats_new_2.15.1_jsonschema:

jsonschema
----------

Asdf 2.15.1 includes internally a version of jsonschema 4.17.3. This inclusion
was done to deal with incompatible changes in jsonschema 4.18.

Many libraries that use asdf import jsonschema to allow catching of ``ValidationError``
instances that might be raised during schema validation. Prior to asdf 2.15 this
error type was not part of the public asdf API. For 2.15 and later users are
expected to import ``ValidationError`` from `asdf.exceptions` (instead of jsonschema
directly).

To further ease the transition, asdf will, when possible, use exceptions imported
from any installed version of jsonschema. This means that when the asdf internal
jsonschema raises a ``ValidationError`` on a system where jsonschema was separately
installed, the internal jsonschema will attempt to use ``ValidationError`` from the
installed version. This should allow code that catches exceptions imported from
jsonschema to continue to work with no changes. However, asdf cannot guarantee
compatibility with future installed jsonschema versions and users are encouraged
to update their code to import ``ValidationError`` from `asdf.exceptions`.

Finally, asdf is temporarily keeping jsonschema as a dependency as many libraries
expected this to be installed by asdf. We expect to drop this requirement soon (likely
in 3.0.0) and this change might occur in a minor or even patch version.
