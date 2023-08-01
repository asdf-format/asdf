.. currentmodule:: asdf

.. _whats_new:

**********
What's new
**********

jsonschema
----------

Asdf 3.0.0 includes internally a version of jsonschema 4.17.3. This inclusion
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
expected this to be installed by asdf. We expect to drop this requirement soon and
this change might occur in a minor or even patch version.
